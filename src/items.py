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