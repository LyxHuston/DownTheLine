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
from typing import Callable, Union, Any, Self
import pygame
import functools
from run_game import entities, tutorials, abilities, ingame, gameboard
import math
import enum
import random
from data import draw_constants, game_states, images, switches
from general_use import utility, game_structures


def raise_abstract_item_type():
    raise TypeError("Abstract item type attempted to be instantiated")


def damage_description(d: int) -> str:
    if d <= 5:
        return ("no", "low", "moderate", "great", "high", "massive")[d]
    d -= 4
    d //= 5
    if d <= 4:
        return ("massive", "extreme", "titanic", "catastrophic", "cataclysmic")[d]
    return "unimaginable"


@dataclass
class ItemType:

    first: int = -1  # first possible appearance, -1 for never (aka abstract or not fully implemented)
    constructor: Callable = staticmethod(lambda *args: raise_abstract_item_type())  # constructor for item types
    generate_parts: Callable = staticmethod(lambda difficulty, random: raise_abstract_item_type())  # generate parts for constructor
    description: Callable = (lambda item: f"{item.type.name}: {item.data_pack}", "Empty")  # get string description
    get_range: Callable = (utility.passing(0), 0)  # range, used for calculations when held by monsters
    action_available: Callable = (utility.make_simple_always(False), False)  # check if an action is available
    in_use: Callable = (utility.make_simple_always(False), False)  # check if item is in use
    held: Callable = (lambda item: isinstance(item.pos[0], entities.Entity), False)  # check if the item is held by an entity
    holder: Callable = (lambda item: item.pos[0], None)  # get the holder
    hand: Callable = (lambda item: item.pos[1], None)
    from_player: Callable = (lambda item: item.pos[0] is game_structures.PLAYER_ENTITY, False)  # check if item is from player
    friendly_player: Callable = (lambda item: item.pos[0].allied_with_player, True)  # check if item is friendly to the player
    prevent_other_use: Callable = (utility.make_simple_always(False), False)  # check if it prevents other items from being in use
    swappable: Callable = (utility.passing, True)  # check if it is swappable with other items

    def __init__(self, first=-1, parent: Self = None, fields: tuple = None, **kwargs):
        self.__dict__.update(
            {
                k: v[0]
                for k, v in self.__class__.__dict__.items()
                if not k.startswith("_") and isinstance(v, tuple)
            }
        )
        self.constructor = self.__class__.constructor
        self.generate_parts = self.__class__.generate_parts
        if fields is not None:
            self.fields = custom_runs.FieldOptions.ItemMaker.value(self, fields)
        for k in kwargs:
            if k.startswith("_") or k not in self.__dict__:
                raise TypeError(f"'{k}' is an invalid keyword argument for ItemType()")
        if parent is not None:
            self.__dict__.update(parent.__dict__)
        self.__dict__.update(kwargs)
        self.first = first

    def construct(self, strength: int, random: random.Random, pos: tuple[int, int]):
        return self.constructor(*self.generate_parts(strength, random, pos))


from screens import custom_runs


simple_stab_imgs = [images.SIMPLE_SPEAR, images.SIMPLE_SWORD, images.SIMPLE_DAGGER]


def random_simple_stab(strength: int, random, pos: tuple[int, int] | None = None):
    damage = random.randint(2, 4)
    image = simple_stab_imgs[damage - 2]
    img = image.img

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


def random_simple_shield(strength, random, pos=None):
    return simple_shield(pos)


def boomerang(strength, random, pos):
    throw_strength = random.choice((5, 10, 15))
    return Item(
        simple_boomerang_action,
        passing,
        simple_boomerang_tick,
        images.BOOMERANG.img,
        images.BOOMERANG.outlined_img,
        pos,
        simple_boomerang_draw,
        images.BOOMERANG_ICON.img,
        [False, 0, 120, 1, throw_strength],
        ItemTypes.Boomerang
    )


def random_simple_throwable(strength, random, pos):
    # current only reusable throwable is hatchet
    throw_strength = random.choice((25, 35))
    item = simple_throwable(
        images.HATCHET.img,
        images.HATCHET.outlined_img,
        pos,
        entities.Hatchet,
        (),
        "Hatchet\n\n"
        f"Throw to deal {damage_description(4)} damage to enemies it touches.\n"
        "If you are dashing while you throw it, it goes faster and deals more damage.\n\n"
        f"Throw Speed: {throw_strength}"
    )
    item.data_pack[1] = tuple([throw_strength, item])
    return item


bow_charge_per_damage = 40


def bow(strength, random, pos):

    max_bonus_damage = random.randint(1, strength // 5)
    pierce = random.choice(list(range(min(strength // 10, 2), 1 + strength // 5)) + ([-1] if strength >= 30 else []))

    cooldown = 30 * max_bonus_damage
    max_charge = (max_bonus_damage + 1) * bow_charge_per_damage

    if pierce == -1:
        growth_rate = 0
    else:
        growth_rate = max_bonus_damage / (max_charge * (0.5 + pierce / 2))

    return Item(
        bow_action,
        bow_release,
        bow_tick,
        images.BOW.img,
        images.BOW.outlined_img,
        pos,
        bow_draw,
        images.BOW_ICON.img,
        [False, cooldown, cooldown, max_charge, pierce, growth_rate, 0, [img.img for img in images.BOW_DRAWS]],
        ItemTypes.Bow
    )


def hammer(strength, random, pos):
    cooldown = 240
    duration = 120
    knockback_duration = 120
    return Item(
        simple_cooldown_action,
        passing,
        hammer_tick,
        images.HAMMER.img,
        images.HAMMER.outlined_img,
        pos,
        hammer_draw,
        images.HAMMER_ICON.img,
        [False, cooldown, cooldown, duration, knockback_duration, images.SWIPE.img],
        ItemTypes.Hammer
    )


in_use_basic = lambda item: item.data_pack[0]


class ItemTypes(enum.Enum):
    """
    enum of item types
    """
    SimpleCooldownAction = ItemType(
        action_available=lambda item: not item.data_pack[0] and item.data_pack[1] >= item.data_pack[2],
        in_use=in_use_basic
    )
    SimpleStab: ItemType = ItemType(
        0,
        SimpleCooldownAction,
        constructor=random_simple_stab,
        description=lambda item:  # state, tracker, cooldown ticks, duration ticks, damage, hit tracker
        f"{('Spear', 'Sword', 'Dagger')[item.data_pack[-2] - 2]}\n\n"
        f"Deals {damage_description(item.data_pack[-2])} damage to enemies it hits.\n"
        f"The simplest weapon type.\n\n"
        f"Cooldown:{round(item.data_pack[2] / 60, 1)} second(s)\n"
        f"Stab Duration: {round(item.data_pack[3] / 60, 1)} second(s)",
        get_range=lambda item: item.img.get_height()
    )
    SimpleShield: ItemType = ItemType(
        0,
        constructor=random_simple_shield,
        description=lambda _:
        "Shield\n\n"
        "Protects you from damage in a direction, in exchange for preventing use of other items.\n"
        f"If you dash into enemies with a shield up, they will take {damage_description(1)} damage.",
        get_range=lambda item: item.img.get_width(),
        action_available=utility.passing(True),
        in_use=in_use_basic,
        prevent_other_use=in_use_basic
    )
    SimpleThrowable: ItemType = ItemType(
        10,
        constructor=random_simple_throwable,
        description=lambda item: item.data_pack[-1],
        get_range=lambda item: item.data_pack[0].find_range(*item.data_pack[1]),
        action_available=lambda item: True
    )
    Bow: ItemType = ItemType(
        12,
        SimpleCooldownAction,
        constructor=bow,
        description=lambda item:
        "Bow\n\n"
        f"Hold it to charge up and shoot an arrow in a given direction, dealing {damage_description(1)} damage.  "
        "The longer you charge, the longer the arrow travels, and the more damage it deals.\n"
        "Release while dashing to halt a dash and deal more damage.\n\n"
        f"Cooldown:{round(item.data_pack[2] / 60, 1)} second(s)\n"
        f"Max Charge Length: {round(item.data_pack[3] / 60, 1)} second(s)"
        f"Pierce: {'Infinite' if item.data_pack[4] == -1 else item.data_pack[4]}"
    )
    Boomerang: ItemType = ItemType(
        15,
        SimpleCooldownAction,
        constructor=boomerang,
        description=lambda item:
        "Boomerang\n\n"
        f"A throwable weapon that returns to the user.  It deals {damage_description(1)} "
        f"damage to enemies it travels through.\n"
        "When the boomerang returns to the user, "
        "the user will automatically pick it back up, unless the player is dashing.\n\n"
        f"Throw Strength: {item.data_pack[4]}",
        swappable=lambda item: not in_use(item)
    )
    Hammer: ItemType = ItemType(
        10,
        SimpleCooldownAction,
        constructor=hammer,
        description=lambda item:
        "Hammer\n\n"
        f"After a long charge-up deal {damage_description(5)} damage to the closest enemy in range.  "
        "Knock it far back and deal moderate damage to enemies it touches."
    )


del in_use_basic


@dataclass
class Item:
    """
    an item entity
    """
    action: Callable
    release: Callable
    tick: Callable
    img: pygame.Surface
    ground_img: pygame.Surface
    pos: Union[int, tuple[entities.Entity, int], tuple[int, int], None]
    draw: Callable
    icon: pygame.Surface
    data_pack: Any
    type: ItemTypes


def deepcopy_datapack_factory(item) -> tuple[Callable, Callable, Callable, pygame.Surface, pygame.Surface, Any, Callable, pygame.Surface, Callable, ItemTypes]:
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

    return item.action, item.release, item.tick, item.img, item.ground_img, item.pos, item.draw, item.icon, factory, item.type


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


_wrap = functools.update_wrapper


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
        return functools.partial(func, *args, **kwargs)
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


@utility.memoize(guarantee_natural=True, guarantee_single=True)
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
@utility.memoize(guarantee_single=True)
def none_check(result: Any) -> Callable[[Any], tuple[Any, Any]]:
    def inner(item):
        return item is not None, result
    return inner


# dynamically generate these.  forward calls to item type defined
description: Callable[[Item], str]
get_range: Callable[[Item], bool]
action_available: Callable[[Item], bool]
in_use: Callable[[Item], bool]
held: Callable[[Item], bool]
holder: Callable[[Item], entities.Entity]
hand: Callable[[Item], int]
from_player: Callable[[Item], bool]
friendly_player: Callable[[Item], bool]
prevent_other_use: Callable[[Item], bool]
swappable: Callable[[Item], bool]

maker = lambda name: (
    getattr(ItemType, name)[0]
    if all(getattr(typ.value, name) is getattr(ItemType, name) for typ in ItemTypes)
    else lambda item: getattr(item.type.value, name)(item)
)

globals().update({
    name: none_check(val[1])(maker(name))
    for name, val in
    ItemType.__dict__.items()
    if not name.startswith("_") and isinstance(val, tuple)
})

del maker

@forward_wrapper_func
def draw_on_ground_if_not_held(func: Callable, item: Item):
    """
    wrapper to make a function draw on the ground if it wasn't held
    :param func:
    :return:
    """
    if not held(item):
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
get_icon_x = lambda _hand: game_states.WIDTH // 2 - spread() // 2 + spread() * _hand - 64
get_icon_y = lambda: (game_states.HEIGHT - 2 * draw_constants.row_separation - tutorials.display_height *
                      switches.TUTORIAL_TEXT_POSITION + 16 * min(max(3 - game_states.HEALTH, 0), 2) ** 2)


@make_conditional_wrapper
def if_held_by_player(item: Item):
    return from_player(item), False


@make_conditional_wrapper
def if_not_in_use(item: Item):
    return not in_use(item), False


@make_conditional_wrapper
def if_action_available(item: Item):
    return action_available(item), False


@make_add_wrapper
@if_held_by_player
def draw_icon(item: Item):
    _hand = hand(item)
    abilities.draw_icon(
        item.icon, 0, (get_icon_x(_hand), get_icon_y()),
        prevent_other_use(game_structures.HANDS[1 - _hand]) or not swappable(item)
    )


@make_add_wrapper
@if_held_by_player
def draw_icon_for_simple_duration_item(item: Item):
    _hand = hand(item)
    abilities.draw_icon(
        item.icon,
        item.data_pack[1] / item.data_pack[3] if in_use(item) else 1 - item.data_pack[1] / item.data_pack[2],
        (get_icon_x(_hand), get_icon_y()),
        prevent_other_use(game_structures.HANDS[1 - _hand]) or not swappable(item)
    )


def original_simple_draw(item: Item):
    """
    very simple drawing function.  If on the ground, draws on the ground
    if held by a player, draws it to the player's side
    if held by an entity, draws it to the entity's side
    :param item:
    :return:
    """
    ent = holder(item)
    _hand = hand(item) * 2 - 1
    rotated = pygame.transform.rotate(
        pygame.transform.flip(item.img, _hand == -1, False),
        ent.rotation + 180
    )
    point = game_structures.to_screen_pos(offset_point_rotated(
            (
                ent.x - rotated.get_width() // 2,
                ent.y + rotated.get_height() // 2
            ),
            (_hand * ent.width // 2, 0),
            ent.rotation
        ))
    game_structures.SCREEN.blit(
        rotated,
        point
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
    ent = holder(item)
    # print(ent.pos, ent.get_pos())
    _hand = hand(item) * 2 - 1
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
            (_hand * ent.width // 3, ent.height // 2 + item.img.get_height() // 2),
            ent.rotation
        ))
    )


@draw_on_ground_if_not_held
@draw_icon
@draw_by_side_if_not_used
def simple_shield_draw(item: Item):
    """
    simple draw function for a shield item.  In front of player if shielding,
    beside player if not
    :param item:
    :return:
    """
    ent = item.pos[0]
    _hand = item.pos[1] * 2 - 1
    rotated = pygame.transform.rotate(
        item.img,
        ent.rotation + 270
    )
    game_structures.SCREEN.blit(
        rotated,
        game_structures.to_screen_pos(offset_point_rotated(
            (
                ent.x - rotated.get_width() // 2,
                ent.y + rotated.get_height() // 2
            ),
            (_hand * ent.width // 8, ent.height // 2 + rotated.get_height() // 2),
            ent.rotation
        ))
    )


simple_boomerang_draw: Callable = draw_on_ground_if_not_held(
    draw_icon_for_simple_duration_item(
        draw_by_side_if_not_used(
            utility.passing
        )
    )
)


def spike_repeat(i: int, mod: int):
    return abs(2 * ((i / mod) % 2) - 1)


@draw_on_ground_if_not_held
@draw_icon_for_simple_duration_item
@draw_by_side_if_not_used
def bow_draw(item: Item):
    ent = holder(item)
    _hand = hand(item)
    # shake strength is how much bonus damage it deals, capped at 5
    shake_strength = min(int(item.data_pack[1] * item.data_pack[5]), 5)
    rotated = pygame.transform.rotate(
        pygame.transform.flip(item.data_pack[-1][shake_strength // 2], _hand == -1, False),
        ent.rotation + 270
    )
    y_shake = round(spike_repeat(item.data_pack[-2], 5) * 3 * shake_strength)
    x_shake = round(spike_repeat(item.data_pack[-2], 7) * 3 * shake_strength)
    game_structures.SCREEN.blit(
        rotated,
        game_structures.to_screen_pos(offset_point_rotated(
            (
                ent.x - rotated.get_width() // 2 + x_shake,
                ent.y + rotated.get_height() // 2 + y_shake
            ),
            (_hand * ent.width // 8, ent.height // 2 + rotated.get_height() // 4),
            ent.rotation
        ))
    )


@if_action_available
def simple_cooldown_action(item: Item):
    """
    a simple action with a cooldown
    :param item:
    :return:
    """
    item.data_pack[0] = True
    item.data_pack[1] = 0
    return True


def simple_toggle_action(item: Item):
    """
    simple action that toggles if the item is in use
    :param item:
    :return:
    """
    item.data_pack[0] = not item.data_pack[0]
    return True


def simple_shield_action(item: Item):
    """
    simple action that toggles a shield
    :param item:
    :return:
    """
    if item.data_pack[0]:
        item.data_pack[1].clear()
    item.data_pack[0] = not item.data_pack[0]
    return True


@if_action_available
def simple_boomerang_action(item: Item):
    item.data_pack[0] = True
    item.data_pack[1] = 0
    gameboard.NEW_ENTITIES.append(entities.Boomerang(item, item.data_pack[4]))


def simple_boomerang_tick(item: Item):
    if not item.data_pack[0] and item.data_pack[1] < item.data_pack[2]:
        item.data_pack[1] += 1
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
    if in_use(item) and held(item):
        user: entities.Entity = holder(item)
        rect = item.img.get_rect(center=offset_point_rotated(
            user.pos,
            (
                user.width // 3 * (item.pos[1] * 2 - 1),
                20 + item.img.get_height() // 2
            ),
            user.rotation
        ))
        rad = user.radius() + get_range(item) + entities.Entity.biggest_radius + 5
        damage = item.data_pack[4]
        hit = user.all_in_range(
                rad, lambda e: e is not user and e not in item.data_pack[-1] and rect.colliderect(e.rect)
        )
        if hit and from_player(item):
            game_states.TIME_SINCE_LAST_INTERACTION = 0
        for entity in hit:
            entity.hit(damage, item)
        item.data_pack[-1].extend(hit)
        if game_structures.PLAYER_ENTITY in hit:
            game_structures.begin_shake(10 * (1 + damage // 2), (20, 20), (2 * (1 + damage), -5 * (1 + damage)))
            entities.glide_player(item.data_pack[4] * 3, 20, 3, (user.y < game_states.DISTANCE) * 2 - 1)
    return True


def simple_shield_tick(item: Item):
    """
    tick for shielding.
    'simple'
    :param item:
    :return:
    """
    if not item.data_pack[0]:
        if item.data_pack[1]:
            for entity in item.data_pack[1]:
                entity.hit(1, item)
            item.data_pack[1].clear()
        return True
    elif not held(item):
        if item.data_pack[1]:
            item.data_pack[1].clear()
        return True
    user: entities.Entity | entities.Glides = holder(item)
    new_center = offset_point_rotated(
        user.pos,
        (
            user.width // 4 * (item.pos[1] * 2 - 1),
            user.height // 2 + item.img.get_width() // 2
        ),
        user.rotation
    )
    # rect = item.img.get_rect(center=new_center)
    rect = pygame.Rect(
        new_center[0] - item.img.get_height() // 2,
        new_center[1] - item.img.get_width() // 2,
        item.img.get_height(),
        item.img.get_width()
    )

    player_friendly = user.allied_with_player
    dashing = isinstance(user, entities.Glides) and user.is_gliding()
    rot = (user.rotation // 180 * 2) - 1
    radius = user.height // 2 + rect.height

    collide_list = user.all_in_range(
        entities.Entity.biggest_radius + radius,
        lambda ent: (ent.y - user.y) * rot > 0 and ent.colliderect(rect)
    )

    if collide_list and from_player(item):
        game_states.TIME_SINCE_LAST_INTERACTION = 0

    collide_list = list(filter(
        lambda en: False and (
            en.hit(en.health, item) if en.allied_with_player is not player_friendly else False
        ) if isinstance(en, entities.Projectile) else True,
        collide_list
    ))

    if dashing:
        item.data_pack[1].extend(
            entity for entity in collide_list
            if
            entity.allied_with_player is not player_friendly
            and entity not in item.data_pack[1]
        )
    elif item.data_pack[1]:
        for entity in item.data_pack[1]:
            entity.hit(1, item)
        item.data_pack[1].clear()

    if collide_list:  # code nearly copied from Crawler
        push_factor: float = math.inf
        new_push_factor: float
        en: entities.Entity
        push_factor_height: int = 0
        for en in collide_list:
            if user.y != en.y:
                new_push_factor = user.y - en.y
                # new_push_factor -= math.copysign(min(en.height // 2, new_push_factor - 1), new_push_factor)
                if abs(new_push_factor) < abs(push_factor):
                    push_factor = new_push_factor
                    push_factor_height = en.height
        if abs(push_factor) > radius:
            change = radius // round(abs(push_factor) - radius)
        else:
            change = radius
        change = min(change, push_factor_height // 2 + radius - abs(push_factor))
        change = round(math.copysign(change, push_factor))
        user.y += change

        # change rect so that it doesn't pull stuff along
        rect.y += change

        e: entities.Entity
        for e in filter(lambda en: en.colliderect(rect), collide_list):
            e.y = user.y + (radius + e.rect.height // 2 + 1) * ((e.y - user.y > 0) * 2 - 1)
        if dashing:
            for e in collide_list:
                e.flashing = 1

    return True


def simple_throwable_action(item: Item):
    """
    creates an entity with given arguments
    :param item:
    :return:
    """
    user: entities.Entity = holder(item)
    _hand = hand(item)
    user.hands[_hand] = None  # remove from hands of entity throwing
    if user is game_structures.PLAYER_ENTITY:
        ingame.pickup_to_hand(_hand)  # refill player hands
    ent = item.data_pack[0](user.pos, user.rotation, *item.data_pack[1])  # create entity
    ent.allied_with_player = user.allied_with_player
    gameboard.NEW_ENTITIES.append(ent)  # add entity to entity list


def simple_throwable(img, ground_img, pos, creates, args, description):
    """
    makes a throwable object that creates an entity when thrown with given arguments
    :param img:
    :param pos:
    :param creates:
    :param args:
    :param description:
    :return:
    """
    return Item(
        simple_throwable_action,
        passing,
        passing,
        img,
        ground_img,
        pos,
        simple_draw,
        images.SIMPLE_THROWABLE_ICON.img,
        [creates, args, description],
        ItemTypes.SimpleThrowable
    )


def simple_bomb(pos, speed, taper, glide_duration, delay, size, damage):
    return simple_throwable(
        images.SIMPLE_BOMB.img,
        images.SIMPLE_BOMB.outlined_img,
        pos,
        entities.Bomb,
        (images.SIMPLE_BOMB.img, speed, taper, glide_duration, delay, size, damage),
        "Bomb\n\n"
        f"{('drop', 'throw')[speed == 0]} to create an explosion after {round(delay / 60, 1)} second(s), dealing "
        f"{damage_description(damage)} damage in a {('small', 'medium', 'large')[size // 256]} area.\n\n"
        f"Movement type: {('drop', 'throw')[speed == 0]}\n"
        f"Delay: {round(delay / 60, 1)} second(s)\n"
        f"Damage: {damage_description(damage)}\n"
        f"Area: {('small', 'medium', 'large')[size // 256]}"
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


def bow_tick(item: Item):
    if held(item):
        item.data_pack[1] = min(item.data_pack[1] + 1, item.data_pack[2 + item.data_pack[0]])
        item.data_pack[-2] = (item.data_pack[-2] + 1) % 35
    else:
        item.data_pack[0] = False
        item.data_pack[1] = item.data_pack[2]
    return True


@if_action_available
def bow_action(item: Item):
    item.data_pack[0] = True


def bow_release(item: Item):
    if item.data_pack[0]:
        pierce = item.data_pack[4]
        growth_rate = item.data_pack[5]
        duration = item.data_pack[1]
        speed = 1 + item.data_pack[1] // 20
        user = holder(item)
        damage = 1 + int(item.data_pack[1] * growth_rate)
        if isinstance(user, entities.Glides) and user.is_gliding():
            speed += user.glide_speed // 2
            damage += user.glide_speed // 10
            user.stop_gliding()
        rot = user.rotation
        rads = math.radians(rot)
        user_pos = user.pos
        radius = user.radius()
        pos = (user_pos[0] + round(radius * math.sin(rads)), user_pos[1] + round(radius * math.cos(rads)))
        gameboard.NEW_ENTITIES.append(
            entities.Projectile(
                images.ARROW.outlined_img,
                rot,
                pos,
                speed=speed,
                num_hit=pierce,
                damage=damage,
                expiry=duration,
                alliance=user.allied_with_player
            )
        )
        item.data_pack[0] = False
        item.data_pack[1] = 0


hammer_swipe_time = 20


def hammer_tick(item: Item):
    item.data_pack[1] += 1
    if item.data_pack[0]:
        if item.data_pack[1] > item.data_pack[3]:
            item.data_pack[0] = False
            item.data_pack[1] = 0
        if item.data_pack[3] - item.data_pack[1] < hammer_swipe_time:
            user: entities.Entity = holder(item)
            img: pygame.Surface = item.data_pack[-1]
            radius = (user.radius() + img.get_height()) // 2
            new_center = offset_point_rotated(
                user.pos,
                (
                    0,
                    radius
                ),
                user.rotation
            )
            rect = img.get_rect(center=new_center)
            collided = user.all_in_range(
                radius + entities.Entity.biggest_radius,
                lambda en: user.allied_with_player is not en.allied_with_player and not en.is_item_entity and en.colliderect(rect)
            )
            if collided:
                if from_player(item):
                    game_states.TIME_SINCE_LAST_INTERACTION = 0
                target = min(collided, key=lambda en: abs(user.y - en.y))
                gameboard.PARTICLE_BOARD.add(entities.EXPLOSION_PARTICLES(target.pos))
                target.hit(5, item)
                damage = 2
                speed = 10
                if isinstance(user, entities.Glides) and user.is_gliding():
                    speed += user.glide_speed
                    damage += 1
                    user.stop_gliding()
                if not target.freeze_x() and not target.freeze_y():
                    duration = item.data_pack[4]
                    target.flashing = duration
                    knocked = entities.KnockbackHolder(target, (target.y > user.y) * 2 - 1, speed, duration, damage)
                    gameboard.ENTITY_BOARD[target.index] = knocked
                item.data_pack[0] = False
                item.data_pack[1] = 0
    else:
        if item.data_pack[1] > item.data_pack[2]:
            item.data_pack[1] = item.data_pack[2]
    return True


@draw_on_ground_if_not_held
@draw_icon_for_simple_duration_item
@draw_by_side_if_not_used
def hammer_draw(item: Item):
    user = holder(item)
    _hand = hand(item) * 2 - 1
    if item.data_pack[3] - item.data_pack[1] < hammer_swipe_time:
        # swipe
        angle = user.rotation
        img = item.data_pack[-1]
        radius = (img.get_height() + user.radius()) // 2
        flip_y = True
    else:
        img = item.img
        angle_offset = ((item.data_pack[1] / item.data_pack[3]) ** 4 - 0.25) * 150
        angle = user.rotation + angle_offset * _hand + 270
        radius = (img.get_height() + user.radius()) // 2 * _hand
        flip_y = _hand == 1
    rotated = pygame.transform.rotate(
        pygame.transform.flip(img, False, flip_y),
        angle
    )
    rads = math.radians(angle)
    point = (
        user.x + radius * math.sin(rads) - rotated.get_width() // 2,
        user.y - radius * math.cos(rads) + rotated.get_height() // 2
    )
    game_structures.SCREEN.blit(
        rotated,
        game_structures.to_screen_pos(point)
    )


def make_random_single_use(random, pos):
    """
    makes a random single use item at a position
    currently only bombs
    :param random:
    :param pos:
    :return:
    """
    return random_simple_bomb(random, pos)


def make_random_reusable(random, pos):
    """
    makes a random reusable item (melee weapon, shield, throwable, or )
    :param random:
    :return:
    """
    choice: ItemTypes = random.choice(tuple(
        typ for typ in ItemTypes if 0 <= typ.value.first <= game_states.LAST_AREA
    ))
    try:
        return choice.value.construct(game_states.LAST_AREA, random, pos)
    except Exception as e:
        e.add_note(f"Error occurred during construction of {choice.name} item type.")
        raise e
    # if choose is ItemTypes.SimpleStab:
    #     return random_simple_stab(game_states.LAST_AREA, random, pos)  # done
    # elif choose is ItemTypes.SimpleShield:
    #     return random_simple_shield(random, pos)  # done
    # elif choose is ItemTypes.SimpleThrowable:
    #     return random_simple_throwable(random, pos)  # done
    # elif choose is ItemTypes.SimpleShooter:
    #     return random_simple_shooter(random, pos)
    # elif choose is ItemTypes.Boomerang:
    #     return boomerang(random, pos)


def simple_stab(cooldown: int, duration: int, img: pygame.Surface, ground_img: pygame.Surface,
                pos: tuple[int, int] | None, damage: int = 3):
    """
    generate an item that uses a simple stab item
    """
    return Item(
        simple_cooldown_action,
        passing,
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


def simple_shield(pos: tuple[int, int]):
    """
    generate a simple shield item
    """
    return Item(
        simple_toggle_action,
        passing,
        simple_shield_tick,
        images.SIMPLE_SHIELD.img,
        images.SIMPLE_SHIELD.outlined_img,
        pos,
        simple_shield_draw,
        images.SIMPLE_SHIELD_ICON.img,
        [False, []],
        ItemTypes.SimpleShield
    )


item_construction_map = custom_runs.FieldOptions.Mapping.value(
    {utility.from_camel(item_type.name): item_type.fields for item_type in ItemTypes if hasattr(item_type, "fields")}
)
