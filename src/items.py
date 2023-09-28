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
    SimpleShield = 0


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


def action_available(item) -> bool:
    match item.type:
        case ItemTypes.SimpleStab:
            return not item.data_pack[0] and item.data_pack[1] >= item.data_pack[2]


def in_use(item) -> bool:
    match item.type:
        case ItemTypes.SimpleStab:
            return item.data_pack[0]


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
            # pygame.draw.rect(
            #     game_structures.SCREEN,
            #     (128, 128, 128),
            #     rect
            # )
            # pygame.draw.rect(
            #     game_structures.SCREEN,
            #     (128, 128, 128),
            #     pygame.Rect(-32 + 600, game_states.DISTANCE - 32 + 600, 64, 64)
            # )
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
                game_states.HEALTH -= damage
                game_structures.begin_shake(10 * (1 + damage // 2), (20, 20), (2 * (1 + damage), -5 * (1 + damage)))
                entities.glide_player(item.data_pack[4] * 3, 20, 3, (
                        (item.pos[1] if isinstance(item.pos[0], int) else item.pos[0].y) < game_states.DISTANCE) * 2 - 1)
    return True


def simple_stab(cooldown: int, duration: int, img: pygame.Surface, pos: tuple[int, int], damage: int = 3) -> Item:
    """
    generate an item that uses a simple stab item
    :return: 
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