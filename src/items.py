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
import game_structures
import game_states
import pygame
import entities
import images
import math
import enum


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
    pos: Union[int, tuple[entities.Entity, int], tuple[int, int]]
    draw: Callable
    data_pack: Any
    type: ItemTypes


def find_range(item) -> int:
    """
    finds the effective range of a given item
    :param item:
    :return:
    """

    match item.type:
        case ItemTypes.SimpleStab:
            return item.img.get_height()
        case ItemTypes.SimpleShield:
            return item.img.get_width()
        case ItemTypes.SimpleThrowable:
            return item.data_pack[0].find_range(*item.data_pack[1])


def action_available(item) -> bool:
    match item.type:
        case ItemTypes.SimpleStab:
            return not item.data_pack[0] and item.data_pack[1] >= item.data_pack[2]
        case ItemTypes.SimpleShield:
            return not item.data_pack[0] and item.data_pack[1] >= item.data_pack[2]
        case ItemTypes.SimpleThrowable:
            return True


def in_use(item) -> bool:
    match item.type:
        case ItemTypes.SimpleStab:
            return item.data_pack[0]
        case ItemTypes.SimpleShield:
            return item.data_pack[0]
        case ItemTypes.SimpleThrowable:
            return False


def from_player(item) -> bool:
    match item.type:
        case ItemTypes.SimpleStab:
            return isinstance(item.pos, int)
        case ItemTypes.SimpleShield:
            return isinstance(item.pos, int)
        case ItemTypes.SimpleThrowable:
            return isinstance(item.pos, int)


def deepcopy_datapack_factory(item) -> tuple[Callable, Callable, pygame.Surface, Any, Callable, Callable, ItemTypes]:
    """
    makes a factory function that returns duplicates of the item datapack for separate use
    :param item: any item
    :return:
    """
    match item.type:
        case ItemTypes.SimpleStab:
            contents = (*item.data_pack[:-1], [])
        case ItemTypes.SimpleShield:
            contents = (*item.data_pack[:-1], [])
        case ItemTypes.SimpleThrowable:
            contents = (*item.data_pack[:-1], images.SIMPLE_THROWABLE_ICON.img)

    def factory():
        return list(contents)

    return item.action, item.tick, item.img, item.pos, item.draw, factory, item.type

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


def _wrap(new, old):
    """Simple substitute for functools.update_wrapper."""
    for replace in ['__module__', '__name__', '__qualname__', '__doc__']:
        if hasattr(old, replace):
            setattr(new, replace, getattr(old, replace))
    new.__dict__.update(old.__dict__)


def use_wrap_update(func: Callable):
    """
    makes a wrapper use the _wrap function on its output.  Needs to be a wrapper.
    :param func: MUST BE A WRAPPER
    :return:
    """

    def internal(func_2: Callable):
        new = func(func_2)
        _wrap(new, func_2)
        return new

    return internal


@use_wrap_update
def make_add_wrapper(func: Callable):
    """
    converts the function into something that calls itself then the function it's
    wrapped on, returning the value from the second
    :param func:
    :return:
    """

    @use_wrap_update
    def internal(func_2: Callable):
        def internal_2(*args):
            func(*args)
            return func_2(*args)

        return internal_2

    return internal


@use_wrap_update
def draw_on_ground_if_not_held(func: Callable):
    """
    wrapper to make a function draw on the ground if it wasn't held
    :param func:
    :return:
    """

    def internal(item: Item):
        if isinstance(item.pos, int):
            func(item)
        elif isinstance(item.pos[0], int):
            draw_on_ground(item)
        else:
            func(item)

    return internal


@use_wrap_update
def draw_by_side_if_not_used(func: Callable):
    """
    assumes already checked if being held
    :param func:
    :return:
    """

    def internal(item: Item):
        if item.data_pack[0]:
            func(item)
        else:
            original_simple_draw(item)

    return internal


def draw_icon_for_simple_duration_item(item: Item):
    if not isinstance(item.pos, int):
        return
    game_structures.SCREEN.blit(
        item.data_pack[5],
        (66 * item.pos, 202)
    )
    if item.data_pack[0]:
        pygame.draw.rect(
            game_structures.SCREEN,
            (0, 0, 0),
            pygame.Rect(66 * item.pos, 202, 64, 64),
        )
    else:
        pygame.draw.rect(
            game_structures.SCREEN,
            (0, 0, 0),
            pygame.Rect(66 * item.pos, 202, 64 - round(64 * item.data_pack[1] / item.data_pack[2]), 64),
        )


add_simple_duration_icon = make_add_wrapper(draw_icon_for_simple_duration_item)


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


simple_draw = draw_on_ground_if_not_held(original_simple_draw)


def draw_on_ground(item):
    """
    assumes that item is already determined to be on ground
    :param item:
    :return:
    """
    game_structures.SCREEN.blit(
        item.img,
        (
            game_structures.to_screen_x(item.pos[0]) - item.img.get_width() // 2,
            game_structures.to_screen_y(item.pos[1]) - item.img.get_height() // 2
        )
    )


def passing(*args):
    """
    simple to put for anything, does nothing.  Use for objects without a tick effect
    :return: True, for use in the tick function
    """
    return True


@draw_on_ground_if_not_held
@add_simple_duration_icon
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
@add_simple_duration_icon
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


@simple_duration_tick
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
            for entity in game_structures.all_entities():
                if entity in item.data_pack[-1]:
                    continue
                if rect.colliderect(entity.rect):
                    entity.hit(item.data_pack[4], item)
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


@simple_duration_tick
def simple_shield_tick(item: Item):
    """
    tick for shielding.
    'simple'
    :param item:
    :return:
    """
    if item.data_pack[0]:
        if isinstance(item.pos, int):
            rect = pygame.Rect(
                8 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION - item.img.get_height() // 2,
                game_states.DISTANCE + (20 + item.img.get_width() // 2) * game_states.LAST_DIRECTION - item.img.get_width() // 2,
                item.img.get_height(),
                item.img.get_width()
            )
        else:
            if isinstance(item.pos[0], int):
                return True
            new_center = offset_point_rotated(
                item.pos[0].pos,
                (
                    item.pos[0].width // 4 * (item.pos[1] * 2 - 1),
                    20 + item.img.get_width() // 2
                ),
                item.pos[0].rotation
            )
            # rect = item.img.get_rect(center=new_center)
            rect = pygame.Rect(
                new_center[0] - item.img.get_height() // 2,
                new_center[1] - item.img.get_width() // 2,
                item.img.get_height(),
                item.img.get_width()
            )
        if isinstance(item.pos, int):
            for entity in game_structures.all_entities():
                if rect.colliderect(entity.rect):
                    entity.y = rect.centery + (rect.height // 2 + entity.height // 2) * game_states.LAST_DIRECTION
                    if isinstance(entity, entities.Projectile):
                        entity.hit(entity.health, item)
                    else:
                        if entity not in item.data_pack[-1]:
                            entity.hit(item.data_pack[4], item)
                            item.data_pack[-1].append(entity)
                    game_states.DISTANCE -= game_states.LAST_DIRECTION * 2
        else:
            damage = item.data_pack[4]
            correct_distance = item.pos[0].y + item.pos[0].height // 2 * math.cos(math.radians(item.pos[0].rotation))
            for entity in game_structures.all_entities():
                if not entity.allied_with_player:
                    continue
                if rect.colliderect(entity.rect):
                    entity.y = correct_distance + entity.height // 2 * math.cos(math.radians(item.pos[0].rotation))
                    if isinstance(entity, entities.Projectile):
                        entity.hit(entity.health, item)
                    else:
                        if entity not in item.data_pack[-1]:
                            entity.hit(item.data_pack[4], item)
                            item.data_pack[-1].append(entity)
                    item.pos[0].y -= 2 * math.cos(math.radians(item.pos[0].rotation))
            if rect.colliderect(pygame.Rect(-32, game_states.DISTANCE - 32, 64, 64)):
                if "p" not in item.data_pack[-1]:
                    item.data_pack.append("p")
                    game_structures.deal_damage(damage, item)
                    entities.glide_player(item.data_pack[4] * 3, 20, 3, (
                            (item.pos[1] if isinstance(item.pos[0], int) else item.pos[0].y) < game_states.DISTANCE) * 2 - 1)
                    game_structures.begin_shake(10 * (1 + damage // 2), (20, 20), (2 * (1 + damage), -5 * (1 + damage)))
                game_states.DISTANCE = item.pos[0].y + (item.pos[0].height // 2 + item.img.get_width()) * math.cos(math.radians(item.pos[0].rotation))
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
        print(rot)
        game_structures.HANDS[item.pos] = None  # remove from hands of entity throwing
    else:
        pos = item.pos[0].pos
        rot = item.pos[0].rotation
        item.pos[0].hands[item.pos[1]] = None  # remove from hands of entity throwing
    area = game_structures.AREA_QUEUE[0]
    ent = item.data_pack[0](pos, rot, *item.data_pack[1])  # create entity
    ent.allied_with_player = p
    area.entity_list.append(ent)  # add entity to entity list


def simple_stab(cooldown: int, duration: int, img: pygame.Surface, pos: tuple[int, int], damage: int = 3) -> Item:
    """
    generate an item that uses a simple stab item
    """
    return Item(
        simple_cooldown_action,
        simple_stab_tick,
        img,
        pos,
        simple_stab_draw,
        [False, cooldown, cooldown, duration, damage, images.SIMPLE_STAB_ICON.img, []
         ],  # state, tracker, cooldown ticks, duration ticks, hit tracker
        ItemTypes.SimpleStab
    )


simple_stab_imgs = [images.SIMPLE_SWORD, images.SIMPLE_SPEAR]


def random_simple_stab(strength: int, random, pos=None):
    img = random.choice(simple_stab_imgs).img

    damage = max(3 - img.get_height() // 100, 0)

    match random.randint(1, 3):
        case 1:
            cooldown = max(180 - strength, 70)
            duration = 70
        case 2:
            cooldown = max(120 - 3 * strength, 50)
            duration = 50
        case _:
            cooldown = max(60 - 9 * strength, 30)
            duration = 10

    if cooldown < 30:
        cooldown = 30

    return Item(
        simple_cooldown_action,
        simple_stab_tick,
        img,
        pos,
        simple_stab_draw,
        [False, cooldown, cooldown, duration, damage, images.SIMPLE_STAB_ICON.img, []
         ],  # state, tracker, cooldown ticks, duration ticks, hit tracker
        ItemTypes.SimpleStab
    )


def simple_shield(cooldown: int, duration: int, img: pygame.Surface, pos: tuple[int, int], damage: int = 0) -> Item:
    """
    generate a simple stab item
    """
    return Item(
        simple_cooldown_action,
        simple_shield_tick,
        img,
        pos,
        simple_shield_draw,
        [False, cooldown, cooldown, duration, damage, images.SIMPLE_SHIELD_ICON.img, []],
        ItemTypes.SimpleShield
    )


simple_shield_imgs = [images.SIMPLE_SHIELD, images.SPIKY_SHIELD]


def random_simple_shield(strength: int, random, pos=None):
    damage = random.randint(0, 1)

    match random.randint(1, 3):
        case 1:  # long out, long cd
            allotment = 180 + strength * 5
            cooldown = 80
        case 2:  # medium out, medium cd
            allotment = 100 + strength * 2
            cooldown = 40
        case _:  # out for not long, extremely low cd
            allotment = 40 + strength
            cooldown = 10

    cooldown += 10 * random.randint(1, 3)
    duration = allotment - cooldown

    return Item(
        simple_cooldown_action,
        simple_shield_tick,
        simple_shield_imgs[damage].img,
        pos,
        simple_shield_draw,
        [False, cooldown, cooldown, duration, damage, images.SIMPLE_SHIELD_ICON.img, []],
        ItemTypes.SimpleShield
    )


def make_random_reusable(random, pos):
    """
    makes a random reusable item (melee weapon, shield, throwable, or )
    :param random:
    :return:
    """
    match random.randint(0, 1):
        case 0:
            return random_simple_stab(game_states.LAST_AREA, random, pos)
        case 1:
            return random_simple_shield(game_states.LAST_AREA, random, pos)


def simple_throwable(img, pos, creates, args):
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
        pos,
        simple_draw,
        [creates, args, images.SIMPLE_THROWABLE_ICON],
        ItemTypes.SimpleThrowable
    )


def simple_bomb(pos, speed, taper, glide_duration, delay, size, damage):
    return simple_throwable(
        images.SIMPLE_BOMB.img,
        pos,
        entities.Bomb,
        (images.SIMPLE_BOMB.img, speed, taper, glide_duration, delay, size, damage)
    )


def make_random_single_use(random, pos):
    """
    makes a random single use item at a position
    :param random:
    :param pos:
    :return:
    """
    pass