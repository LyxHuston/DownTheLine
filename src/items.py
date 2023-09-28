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
        else:  # would be held by an enemy entity, a case which does not exist yet
            pass

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
    game_structures.SCREEN.blit(
        pygame.transform.flip(item.img, ((item.pos == 0) != (game_states.LAST_DIRECTION == -1)),
                              game_states.LAST_DIRECTION == -1),
        (
            game_structures.to_screen_x(
                32 * (item.pos * 2 - 1) * game_states.LAST_DIRECTION) - item.img.get_width() // 2,
            game_structures.to_screen_y(game_states.DISTANCE) - item.img.get_height() // 2
        )
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