"""
A 1.5d hack-and-slash game.
Copyright (C) 2023  Lyx Huston

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or any
later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

handles making items.

This is going to be full of factory functions, huh.  Factories of factories of factories.  Factoryception.
"""

from dataclasses import dataclass
from typing import Callable, Union, Any
import pygame
from run_game import entities, tutorials, abilities, ingame, gameboard
import math
import enum
from data import draw_constants, game_states, images, switches
from general_use import utility, game_structures


class ItemTypes(enum.IntEnum):
    """
    enum of item types
    """
    SimpleStab = 0
    SimpleShield = 1
    SimpleThrowable = 2


@dataclass
class Item:
    """
    an item entity
    """
    action: Callable
    tick: Callable
    img: pygame.Surface
    ground_img: pygame.Surface
    pos: Union[int, tuple[entities.Entity, int], tuple[int, int], None]
    draw: Callable
    icon: pygame.Surface
    data_pack: Any
    type: ItemTypes


def deepcopy_datapack_factory(item) -> tuple[Callable, Callable, pygame.Surface, pygame.Surface, Any, Callable, pygame.Surface, Callable, ItemTypes]:
    """
    makes a factory function that returns duplicates of the item datapack for separate use
    :param item: any item
    :return:
    """
    if item.type == ItemTypes.SimpleStab:
        contents = (*item.data_pack[:-1], [])
    elif item.type == ItemTypes.SimpleShield:
        contents = (*item.data_pack[:-1], [])
    elif item.type == ItemTypes.SimpleThrowable:
        contents = item.data_pack[:]

    def factory():
        return list(contents)

    return item.action, item.tick, item.img, item.ground_img, item.pos, item.draw, item.icon, factory, item.type


def offset_point_rotated(origin: tuple[int, int], offset: tuple[int, int], rotation: int) -> tuple[int, int]:
    """
    rotates the offset point, then adds to origin.
    Uses monster's base orientation (0 is down, +y is down, +x is left)
    :param origin: center point
    :param offset: a point to be rotated and added to the origin
    :param rotation: amount to rotate
    :return: computed point
    """
    rad = math.radians(rotation)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return (
        round(origin[0] - cos * offset[0] + sin * offset[1]),
        round(origin[1] - cos * offset[1] - sin * offset[0])
    )


def _wrap(new: Any, old: Any):
    """Simple substitute for functools.update_wrapper."""
    for replace in ['__module__', '__name__', '__qualname__', '__doc__']:
        if hasattr(old, replace):
            setattr(new, replace, getattr(old, replace))
    new.__dict__.update(old.__dict__)
    return new


EMPTY = object()


def use_wrap_update(func: Callable):
    """
    makes a wrapper use the _wrap function on its output.  Needs to be a wrapper.
    :param func: MUST BE A WRAPPER
    :return:
    """

    @handle_arguments_meta_wrapper
    def internal(func_2: Callable):
        return _wrap(func(func_2), func_2)

    return _wrap(internal, func)


def handle_arguments_meta_wrapper(wrapper_func: Callable):
    """
    handles arguments for wrappers.  If arguments are given, passes them to the wrapped function,
    and passes the resultant function into the wrapper function.  Otherwise, passes the function
    object in
    if a function for running is given, instead runs with the specified function
    :return:
    """
    def inner(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], Callable):
            return _wrap(wrapper_func(args[0]), args[0])

        def inner2(func):
            return _wrap(wrapper_func(func(*args, **kwargs)), func)
        return inner2
    return _wrap(inner, wrapper_func)


def preset_args(*args, **kwargs) -> Callable[[Callable], Callable]:
    """
    given arguments as a wrapper, it makes invocations use those arguments first,
    and applies additional ones as supplied
    """
    @use_wrap_update
    def inner(func: Callable) -> Callable:
        return lambda *args2, **kwargs2: func(*args, *args2, **kwargs, **kwargs2)
    return inner


@use_wrap_update
def make_meta_wrapper(wrapper_func: Callable):
    """
    converts the function into a wrapper that produces another wrapper.  When that wrapper is
    used, it passes the two functions into the wrapper func, and returns the result.

    Example of use is the make_add_wrapper or make_conditional_wrapper

    if arguments are used on the wrapper, it passes the arguments to the function
    then uses the resultant function in all wraps.
    if arguments are used in the resultant wrapper, it passes the arguments to the function
    then uses the resultant function in only that wrap.
    """

    # when you have enough helper functions that pretty much anything can be a lambda expression
    # but you don't, because readability is important.  Disregard the rest of the file.
    @handle_arguments_meta_wrapper
    def inner(func1: Callable):
        def inner2(*args, **kwargs):
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], Callable):
                return _wrap(wrapper_func(func1, args[0]), func1)

            def inner3(func2: Callable):
                return _wrap(wrapper_func(func1(*args, **kwargs), func2), func1)
            return inner3
        return inner2
    return inner


@utility.memoize
def forward_args(num: int):

    def to_func(func):
        def inner(current_list: tuple[[Callable], ...], *args):
            if len(current_list) + len(args) == num:
                return preset_args(*current_list, *args)(func)
            if len(current_list) + len(args) > num:
                raise ValueError("Too many arguments given in forwarding.")

            return preset_args((*current_list, *args))(inner)

        return preset_args(())(inner)

    return to_func


@use_wrap_update
def forward_meta_wrapper_funcs(func: Callable):

    @make_meta_wrapper
    def inner(func1: Callable, func2: Callable):
        return _wrap(preset_args(func1, func2)(func), func)

    return inner


forward_wrapper_func = forward_args(1)


@forward_meta_wrapper_funcs
def make_add_wrapper(func1: Callable, func2: Callable, *args, **kwargs):
    func1(*args, **kwargs)
    return func2(*args, **kwargs)


@forward_meta_wrapper_funcs
def make_conditional_wrapper(func1: Callable, func2: Callable, *args, **kwargs):
    """
    makes a function a conditional wrapper.
    :param func1: must have return of (boolean, Any)
    :param func2: run if func1 returns (True, <Any>)
    :return:
    """
    valid, result = func1(*args, **kwargs)
    if valid:
        return func2(*args, **kwargs)
    return result


@make_conditional_wrapper
@utility.memoize
def none_check(result: Any) -> Callable[[Any], tuple[Any, Any]]:
    def inner(item):
        return item is not None, result
    return inner


@none_check(0)
def find_range(item) -> int:
    """
    finds the effective range of a given item
    :param item:
    :return:
    """

    if item.type == ItemTypes.SimpleStab:
        return item.img.get_height()
    elif item.type == ItemTypes.SimpleShield:
        return item.img.get_width()
    elif item.type == ItemTypes.SimpleThrowable:
        return item.data_pack[0].find_range(*item.data_pack[1])


@none_check(False)
def action_available(item) -> bool:
    if item.type == ItemTypes.SimpleStab:
        return not item.data_pack[0] and item.data_pack[1] >= item.data_pack[2]
    elif item.type == ItemTypes.SimpleShield:
        return True
    elif item.type == ItemTypes.SimpleThrowable:
        return True


@none_check(False)
def in_use(item) -> bool:
    if item.type == ItemTypes.SimpleStab:
        return item.data_pack[0]
    elif item.type == ItemTypes.SimpleShield:
        return item.data_pack[0]
    elif item.type == ItemTypes.SimpleThrowable:
        return False


@none_check(False)
def from_player(item) -> bool:
    if item.type == ItemTypes.SimpleStab:
        return isinstance(item.pos, int)
    elif item.type == ItemTypes.SimpleShield:
        return isinstance(item.pos, int)
    elif item.type == ItemTypes.SimpleThrowable:
        return isinstance(item.pos, int)


@none_check(False)
def prevent_other_use(item) -> bool:
    if item.type == ItemTypes.SimpleShield:
        return item.data_pack[0]
    else:
        return False


@forward_wrapper_func
def draw_on_ground_if_not_held(func: Callable, item: Item):
    """
    wrapper to make a function draw on the ground if it wasn't held
    :param func:
    :return:
    """
    if isinstance(item.pos, int):
        func(item)
    elif isinstance(item.pos[0], int):
        draw_on_ground(item)
    else:
        func(item)


@forward_wrapper_func
def draw_by_side_if_not_used(func: Callable, item: Item):
    """
    assumes already checked if being held
    """
    if in_use(item):
        func(item)
    else:
        original_simple_draw(item)


spread = lambda: 384 - 32 * min(max(0, 4 - game_states.HEALTH), 3)
get_icon_x = lambda hand: game_states.WIDTH // 2 - spread() // 2 + spread() * hand - 64
get_icon_y = lambda: (game_states.HEIGHT - 2 * draw_constants.row_separation - tutorials.display_height *
                      switches.TUTORIAL_TEXT_POSITION + 16 * min(max(3 - game_states.HEALTH, 0), 2) ** 2)


@make_conditional_wrapper
def if_held_by_player(item: Item):
    if isinstance(item.pos, int):
        return True, False
    return False, False


@make_add_wrapper
@if_held_by_player
def draw_icon(item: Item):
    abilities.draw_icon(
        item.icon, 0, (get_icon_x(item.pos), get_icon_y()),
        prevent_other_use(game_structures.HANDS[1 - item.pos])
    )


@make_add_wrapper
@if_held_by_player
def draw_icon_for_simple_duration_item(item: Item):
    abilities.draw_icon(
        item.icon,
        item.data_pack[1] / item.data_pack[3] if item.data_pack[0] else 1 - item.data_pack[1] / item.data_pack[2],
        (get_icon_x(item.pos), get_icon_y()),
        prevent_other_use(game_structures.HANDS[1 - item.pos])
    )


def original_simple_draw(item: Item):
    """
    very simple drawing function.  If on the ground, draws on the ground
    if held by a player, draws it to the player's side
    if held by an entity, draws it to the entity's side
    :param item:
    :return:
    """
    if isinstance(item.pos, int):
        game_structures.SCREEN.blit(
            pygame.transform.flip(item.img, ((item.pos == 0) != (game_states.LAST_DIRECTION == -1)),
                                  game_states.LAST_DIRECTION == -1),
            (
                game_structures.to_screen_x(
                    32 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION) - item.img.get_width() // 2,
                game_structures.to_screen_y(game_states.DISTANCE) - item.img.get_height() // 2
            )
        )
    else:
        ent = item.pos[0]
        hand = item.pos[1] * 2 - 1
        rotated = pygame.transform.rotate(
            pygame.transform.flip(item.img, item.pos[1] == 0, False),
            ent.rotation + 180
        )
        # print(ent.pos, (ent.x, ent.y), ent.get_pos(), )
        game_structures.SCREEN.blit(
            rotated,
            game_structures.to_screen_pos(offset_point_rotated(
                (
                    ent.x - rotated.get_width() // 2,
                    ent.y + rotated.get_height() // 2
                ),
                (hand * ent.width // 2, 0),
                ent.rotation
            ))
        )


simple_draw = draw_on_ground_if_not_held(draw_icon(original_simple_draw))


def draw_on_ground(item):
    """
    assumes that item is already determined to be on ground
    :param item:
    :return:
    """
    game_structures.SCREEN.blit(
        item.ground_img,
        (
            game_structures.to_screen_x(item.pos[0]) - item.img.get_width() // 2,
            game_structures.to_screen_y(item.pos[1]) - item.img.get_height() // 2
        )
    )


passing = utility.passing


@draw_on_ground_if_not_held
@draw_icon_for_simple_duration_item
@draw_by_side_if_not_used
def simple_stab_draw(item: Item):
    """
    simple draw function for a stabbing item.  In front of player if stabbing,
    beside player if not
    :param item:
    :return:
    """
    if isinstance(item.pos, int):
        game_structures.SCREEN.blit(
            pygame.transform.flip(item.img, ((item.pos == 0) != (game_states.LAST_DIRECTION == -1)),
                                  game_states.LAST_DIRECTION == -1),
            (
                game_structures.to_screen_x(
                    16 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION) - item.img.get_width() // 2,
                game_structures.to_screen_y(game_states.DISTANCE + (
                        20 + item.img.get_height() // 2) * game_states.LAST_DIRECTION) - item.img.get_height() // 2
            )
        )
    else:
        ent = item.pos[0]
        # print(ent.pos, ent.get_pos())
        hand = item.pos[1] * 2 - 1
        rotated = pygame.transform.rotate(
            pygame.transform.flip(item.img, item.pos[1] == 0, False),
            ent.rotation + 180
        )
        game_structures.SCREEN.blit(
            rotated,
            game_structures.to_screen_pos(offset_point_rotated(
                (
                    ent.x - rotated.get_width() // 2,
                    ent.y + rotated.get_height() // 2
                ),
                (hand * ent.width // 4, ent.height // 2 + item.img.get_height() // 2),
                ent.rotation
            ))
        )


@draw_on_ground_if_not_held
@draw_icon
@draw_by_side_if_not_used
def simple_shield_draw(item: Item):
    """
    simple draw function for a stabbing item.  In front of player if stabbing,
    beside player if not
    :param item:
    :return:
    """
    if isinstance(item.pos, int):
        game_structures.SCREEN.blit(
            pygame.transform.rotate(item.img, game_states.LAST_DIRECTION * 90),
            (
                game_structures.to_screen_x(
                    16 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION) - item.img.get_height() // 2,
                game_structures.to_screen_y(game_states.DISTANCE + (
                        20 + item.img.get_width() // 2) * game_states.LAST_DIRECTION) - item.img.get_width() // 2
            )
        )
    else:
        ent = item.pos[0]
        hand = item.pos[1] * 2 - 1
        rotated = pygame.transform.rotate(
            pygame.transform.flip(item.img, item.pos[1] == 0, False),
            ent.rotation + 270
        )
        game_structures.SCREEN.blit(
            rotated,
            game_structures.to_screen_pos(offset_point_rotated(
                (
                    ent.x - rotated.get_width() // 2,
                    ent.y + rotated.get_height() // 2
                ),
                (hand * ent.width // 8, ent.height // 2 + rotated.get_height() // 2),
                ent.rotation
            ))
        )


def simple_cooldown_action(item: Item):
    """
    a simple action with a cooldown
    :param item:
    :return:
    """
    if item.data_pack[0]:
        return False
    if item.data_pack[1] >= item.data_pack[2]:
        item.data_pack[0] = True
        item.data_pack[1] = 0
        return True
    return False


def simple_toggle_action(item: Item):
    """
    simple action that toggles if the item is in use
    :param item:
    :return:
    """
    item.data_pack[0] = not item.data_pack[0]
    return True


@make_add_wrapper
def simple_duration_tick(item: Item):
    """
    simple test for a simple duration and cooldown
    :param item:
    :return:
    """
    item.data_pack[1] += 1
    if item.data_pack[0]:
        if item.data_pack[1] > item.data_pack[3]:
            item.data_pack[0] = False
            item.data_pack[1] = 0
            item.data_pack[-1].clear()
    else:
        if item.data_pack[1] > item.data_pack[2]:
            item.data_pack[1] = item.data_pack[2]
    return True


@make_add_wrapper
def simple_damage_tick(cd: int, cache_slot: int):
    """
    an add wrapper that clears the damage cache on a weapon every <cd> ticks
    :param cd: cooldown on clearing damage cache
    :param cache_slot: slot to clear
    :param count_slot: slot that is counting time since clear
    :return:
    """

    @simple_duration_tick
    def inner(item: Item):
        if not hasattr(item, "damage_tick"):
            setattr(item, "damage_tick", 0)

        if not in_use(item):
            item.damage_tick = 0
            return

        item.damage_tick += 1
        if item.damage_tick == cd:
            item.damage_tick = 0
            item.data_pack[cache_slot].clear()

    return inner


@simple_damage_tick(25, -1)
def simple_stab_tick(item: Item):
    """
    tick for stabbing.
    :param item:
    :return:
    """
    if item.data_pack[0]:
        if isinstance(item.pos, int):
            rect = item.img.get_rect(center=(
                16 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION,
                game_states.DISTANCE + (20 + item.img.get_height() // 2) * game_states.LAST_DIRECTION
            ))
        else:
            if isinstance(item.pos[0], int):
                return True
            rect = item.img.get_rect(center=offset_point_rotated(
                item.pos[0].pos,
                (
                    item.pos[0].width // 2 * (item.pos[1] * 2 - 1),
                    20 + item.img.get_height() // 2
                ),
                item.pos[0].rotation
            ))
        if isinstance(item.pos, int):
            for entity in gameboard.ENTITY_BOARD:
                if entity in item.data_pack[-1]:
                    continue
                if rect.colliderect(entity.rect):
                    entity.hit(item.data_pack[4], item)
                    game_states.TIME_SINCE_LAST_INTERACTION = 0
                    item.data_pack[-1].append(entity)
        elif "p" not in item.data_pack[-1]:
            if rect.colliderect(pygame.Rect(-32, game_states.DISTANCE - 32, 64, 64)):
                item.data_pack[-1].append("p")
                damage = item.data_pack[4]
                game_structures.deal_damage(damage, item)
                game_structures.begin_shake(10 * (1 + damage // 2), (20, 20), (2 * (1 + damage), -5 * (1 + damage)))
                entities.glide_player(item.data_pack[4] * 3, 20, 3, (
                        (item.pos[1] if isinstance(item.pos[0], int) else item.pos[0].y) < game_states.DISTANCE) * 2 - 1)
    return True


def simple_shield_tick(item: Item):
    """
    tick for shielding.
    'simple'
    :param item:
    :return:
    """
    if not item.data_pack[0]:
        return True
    if isinstance(item.pos, int):
        rect = pygame.Rect(
            8 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION - item.img.get_height() // 2,
            game_states.DISTANCE + (20 + item.img.get_width() // 2) * game_states.LAST_DIRECTION - item.img.get_width() // 2,
            item.img.get_height(),
            item.img.get_width()
        )

        player_friendly = True
        dashing = abilities.is_dashing()
        center = game_states.DISTANCE
        radius = rect.height + 20

        collide_list = [
            entity
            for entity in gameboard.ENTITY_BOARD
            if
            not entity.freeze_y()
            and ((entity.y - game_states.DISTANCE) * game_states.LAST_DIRECTION > 0)
            and entity.colliderect(rect)
        ]

        if collide_list:
            game_states.TIME_SINCE_LAST_INTERACTION = 0
            game_states.DISTANCE -= game_states.LAST_DIRECTION * 2
    else:
        if isinstance(item.pos[0], int):
            return True
        e: entities.Entity | entities.Glides = item.pos[0]
        new_center = offset_point_rotated(
            e.pos,
            (
                item.pos[0].width // 4 * (item.pos[1] * 2 - 1),
                20 + item.img.get_width() // 2
            ),
            e.rotation
        )
        # rect = item.img.get_rect(center=new_center)
        rect = pygame.Rect(
            new_center[0] - item.img.get_height() // 2,
            new_center[1] - item.img.get_width() // 2,
            item.img.get_height(),
            item.img.get_width()
        )

        player_friendly = False
        dashing = isinstance(e, entities.Glides) and e.glide_speed > 0
        center = e.y
        radius = e.height // 2 + rect.height

        collide_list = e.all_in_range(
            entities.Entity.biggest_radius + radius,
            lambda en: not en.freeze_y() and en.colliderect(rect)
        )

    collide_list = list(filter(
        lambda en: False and (
            en.hit(en.health, item) if en.allied_with_player is not player_friendly else False
        ) if isinstance(en, entities.Projectile) else True,
        collide_list
    ))

    if collide_list:  # code nearly copied from Crawler
        push_factor: float = math.inf
        new_push_factor: float
        en: entities.Entity
        for en in collide_list:
            if center != en.y:
                new_push_factor = center - en.y
                if abs(new_push_factor) < abs(push_factor):
                    push_factor = new_push_factor
        if math.isfinite(push_factor):
            if abs(push_factor) > radius:
                push_factor -= math.copysign(radius, push_factor)
                change = radius // round(push_factor)
            else:
                change = round(math.copysign(radius, push_factor))

            if isinstance(item.pos, int):
                game_states.DISTANCE += change
            else:
                e.y += change
            center += change

        e: entities.Entity
        for e in filter(lambda ent: ent.colliderect(rect), collide_list):
            e.y = center + (radius + e.rect.height // 2) * ((e.y - center > 0) * 2 - 1)

    if not player_friendly:
        if rect.colliderect(pygame.Rect(-32, game_states.DISTANCE - 32, 64, 64)):
            game_states.DISTANCE = item.pos[0].y + (item.pos[0].height // 2 + item.img.get_width()) * math.cos(
                math.radians(item.pos[0].rotation))
            item.pos[0].y -= 2 * math.cos(math.radians(item.pos[0].rotation))

    return True


def simple_throwable_action(item: Item):
    """
    creates an entity with given arguments
    :param item:
    :return:
    """
    p = isinstance(item.pos, int)  # if it's from the player
    if p:
        pos = (0, game_states.DISTANCE)
        rot = game_states.LAST_DIRECTION * 90 + 90
        # print(rot)
        game_structures.HANDS[item.pos] = None  # remove from hands of entity throwing
        ingame.pickup_to_hand(item.pos)  # refill player hands
    else:
        pos = item.pos[0].pos
        rot = item.pos[0].rotation
        item.pos[0].hands[item.pos[1]] = None  # remove from hands of entity throwing
    # print(item)
    ent = item.data_pack[0](pos, rot, *item.data_pack[1])  # create entity
    ent.allied_with_player = p
    gameboard.NEW_ENTITIES.append(ent)  # add entity to entity list


def simple_stab(cooldown: int, duration: int, img: pygame.Surface, ground_img: pygame.Surface,
                pos: tuple[int, int] | None, damage: int = 3) -> Item:
    """
    generate an item that uses a simple stab item
    """
    return Item(
        simple_cooldown_action,
        simple_stab_tick,
        img,
        ground_img,
        pos,
        simple_stab_draw,
        images.SIMPLE_STAB_ICON.img,
        [False, cooldown, cooldown, duration, damage, []
         ],  # state, tracker, cooldown ticks, duration ticks, damage, hit tracker
        ItemTypes.SimpleStab
    )


simple_stab_imgs = [images.SIMPLE_SWORD, images.SIMPLE_SPEAR]


def random_simple_stab(strength: int, random, pos: tuple[int, int] | None = None):
    image = random.choice(simple_stab_imgs)
    img = image.img

    damage = max(3 - img.get_height() // 100, 0)

    choose = random.randint(1, 3)
    if choose == 1:
        cooldown = max(120 - strength, 60)
        duration = 70
    elif choose == 2:
        cooldown = max(120 - 3 * strength, 40)
        duration = 50
    else:
        cooldown = max(60 - 9 * strength, 20)
        duration = 10

    if cooldown < 30:
        cooldown = 30

    return simple_stab(cooldown, duration, img, image.outlined_img, pos, damage)


def simple_shield(pos: tuple[int, int]) -> Item:
    """
    generate a simple shield item
    """
    return Item(
        simple_toggle_action,
        simple_shield_tick,
        images.SIMPLE_SHIELD.img,
        images.SIMPLE_SHIELD.outlined_img,
        pos,
        simple_shield_draw,
        images.SIMPLE_SHIELD_ICON.img,
        [False],
        ItemTypes.SimpleShield
    )


def random_simple_shield(random, pos=None):

    return simple_shield(pos)


def make_random_reusable(random, pos):
    """
    makes a random reusable item (melee weapon, shield, throwable, or )
    :param random:
    :return:
    """
    choose = random.randint(0, 1)
    if choose == 0:
        return random_simple_stab(game_states.LAST_AREA, random, pos)
    elif choose == 1:
        return random_simple_shield(random, pos)


def simple_throwable(img, ground_img, pos, creates, args):
    """
    makes a throwable object that creates an entity when thrown with given arguments
    :param img:
    :param pos:
    :param creates:
    :param args:
    :return:
    """
    return Item(
        simple_throwable_action,
        passing,
        img,
        ground_img,
        pos,
        simple_draw,
        images.SIMPLE_THROWABLE_ICON.img,
        [creates, args],
        ItemTypes.SimpleThrowable
    )


def simple_bomb(pos, speed, taper, glide_duration, delay, size, damage):
    return simple_throwable(
        images.SIMPLE_BOMB.img,
        images.SIMPLE_BOMB.outlined_img,
        pos,
        entities.Bomb,
        (images.SIMPLE_BOMB.img, speed, taper, glide_duration, delay, size, damage)
    )


def random_simple_bomb(random, pos):
    choose = random.randint(0, 2)
    if choose == 0:  # archetype.1 1: landmine
        speed = 0
        taper = 0
        glide_duration = 0
        delay = 15 * random.randint(4, 7)
    elif choose == 1:  # archetype.1 2: glider
        speed = 5 * random.randint(1, 3)
        taper = 0
        glide_duration = 0
        delay = 15 * random.randint(3, 4)
    else:  # archetype.1 3: sitter
        speed = 5 * random.randint(2, 4)
        taper = 1
        glide_duration = 5 * random.randint(1, 2)
        delay = glide_duration + 60
    choose = random.randint(0, 2)
    if choose == 0:  # archetype.2 1: pinpoint nuke
        size = 64
        damage = 64
    elif choose == 1:  # archetype.2 2: semi-precise destruction
        size = 256
        damage = 10
    else:  # archetype.2 3: screen wide relatively low damage
        size = 640
        damage = 4
    return simple_bomb(pos, speed, taper, glide_duration, delay, size, damage)


def make_random_single_use(random, pos):
    """
    makes a random single use item at a position
    :param random:
    :param pos:
    :return:
    """
    return random_simple_bomb(random, pos)
