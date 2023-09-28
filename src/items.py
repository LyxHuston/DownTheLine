"""
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


def simple_draw(item: Item):
    """
    very simple drawing function.  If on the ground, draws on the ground
    if held by a player, draws it to the player's side
    if held by an entity, draws it to the entity's side
    :param item:
    :return:
    """
    if isinstance(item.pos, int):
        game_structures.SCREEN.blit(
            pygame.transform.flip(item.img, ((item.pos == 0) != (game_states.LAST_DIRECTION == -1)), game_states.LAST_DIRECTION == -1),
            (
                game_states.WIDTH // 2 + 32 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION - item.img.get_width() // 2,
                game_states.HEIGHT + game_states.CAMERA_BOTTOM - game_states.DISTANCE - item.img.get_height() // 2
            )
        )
    elif isinstance(item.pos[0], int):
        draw_on_ground(item)
    else:
        pass


def draw_on_ground(item):
    """
    assumes that item is already determined to be on ground
    :param item:
    :return:
    """
    game_structures.SCREEN.blit(
        item.img,
        (
            game_states.WIDTH // 2 + item.pos[0] - item.img.get_width() // 2,
            game_states.HEIGHT + game_states.CAMERA_BOTTOM - item.pos[1] - item.img.get_height() // 2
        )
    )


def passing(*args):
    """
    simple to put for anything, does nothing.  Use for objects without a tick effect
    :return: True, for use in the tick function
    """
    return True


def simple_stab_draw(item: Item):
    """
    simple draw function for a stabbing item.  In front of player if stabbing,
    beside player if not
    :param item:
    :return:
    """
    if not item.data_pack[0]:
        simple_draw(item)
        return
    if isinstance(item.pos, int):
        game_structures.SCREEN.blit(
            pygame.transform.flip(item.img, ((item.pos == 0) != (game_states.LAST_DIRECTION == -1)), game_states.LAST_DIRECTION == -1),
            (
                game_states.WIDTH // 2 + 16 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION - item.img.get_width() // 2,
                game_states.HEIGHT + game_states.CAMERA_BOTTOM - game_states.DISTANCE - item.img.get_height() // 2 - (20 + item.img.get_height() // 2) * game_states.LAST_DIRECTION
            )
        )
    elif isinstance(item.pos[0], int):
        draw_on_ground(item)
    else:
        pass


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


def simple_stab_tick(item: Item):
    """
    tick for stabbing.
    :param item:
    :return:
    """
    simple_duration_tick(item)
    if item.data_pack[0]:
        rect = item.img.get_rect(center=(
            16 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION,
            game_states.DISTANCE + (20 + item.img.get_height() // 2) * game_states.LAST_DIRECTION
        ))
        for area in game_structures.AREA_QUEUE:
            if not area.initialized:
                break
            for entity in area.entity_list:
                if not isinstance(entity, entities.Entity):
                    continue
                if entity in item.data_pack[-1]:
                    continue
                if rect.colliderect(entity.rect):
                    entity.hit(item.data_pack[4], item)
                    item.data_pack[-1].append(entity)
    if isinstance(item.pos, int):
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
         ]  # state, tracker, cooldown ticks, duration ticks, hit tracker
    )