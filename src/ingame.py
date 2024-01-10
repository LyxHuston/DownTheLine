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

in-game calculations
"""

import gameboard
import pygame
import game_states
import game_structures
import items
import entities
import abilities
import run_start_end


class Inputs:
    up_input = pygame.K_w
    down_input = pygame.K_s
    ignore_pickup = pygame.K_SPACE
    ability_1_input = pygame.K_a
    ability_2_input = pygame.K_d


loop_counter = 2 ** 10

tick_counter = 0


def tick(do_tick: bool = None):
    if do_tick is None or do_tick:
        if game_states.INVULNERABILITY_LEFT > 0:
            game_states.INVULNERABILITY_LEFT -= 1
        if game_states.HEALTH <= 0 and game_states.PLACE is screen:
            game_structures.switch_to_place(game_structures.PLACES.lost)
        global tick_counter
        tick_counter = tick_counter + 1
        if tick_counter >= loop_counter:
            tick_counter = 0
            abilities.last_dash_time -= loop_counter
            abilities.last_press_for_dash -= loop_counter
        if game_states.GLIDE_SPEED > 0:
            if game_states.GLIDE_DURATION == 0:
                game_states.GLIDE_SPEED -= game_states.TAPER_AMOUNT
                if game_states.GLIDE_SPEED <= 0:
                    game_states.GLIDE_SPEED = 0
            else:
                game_states.GLIDE_DURATION -= 1
            game_states.DISTANCE += game_states.GLIDE_SPEED * game_states.GLIDE_DIRECTION
        elif do_tick is None:
            pressed = pygame.key.get_pressed()
            direction = pressed[Inputs.up_input] - pressed[Inputs.down_input]
            if abs(direction) == 1:
                game_states.LAST_DIRECTION = direction
            move = 10 * direction
            game_states.DISTANCE += move
        if game_states.DISTANCE < game_states.BOTTOM:
            game_states.DISTANCE = game_states.BOTTOM
        if game_states.DISTANCE > game_states.RECORD_DISTANCE:
            game_states.RECORD_DISTANCE = game_states.DISTANCE
    gameboard.tick(do_tick if isinstance(do_tick, bool) else True)


def event_catcher(event: pygame.event.Event) -> bool:
    if game_states.HEALTH <= 0:
        return False
    match event.type:
        case pygame.KEYDOWN:
            match event.key:
                case Inputs.up_input:
                    abilities.dash_input_catch(1, tick_counter)
                    return True
                case Inputs.down_input:
                    abilities.dash_input_catch(-1, tick_counter)
                    return True
        case pygame.MOUSEBUTTONDOWN:
            match event.button:
                case 1:
                    item_input_catch(0)
                    return True
                case 3:
                    item_input_catch(1)
                    return True
    return False


def item_input_catch(num: int) -> None:
    if not pygame.key.get_pressed()[Inputs.ignore_pickup]:
        for area in game_structures.initialized_areas():
            for entity in area.entity_list:
                # entity = area.entity_list[i]
                if entity.is_holder:
                    # print("extracted from holder")
                    entity = entity.holding
                if not entity.is_item_entity:
                    continue
                if not isinstance(entity.pos[0], int):
                    continue
                if not entity.rect.colliderect(
                        pygame.Rect(-32, game_states.DISTANCE - 10, 64, 20)):
                    continue
                if game_structures.HANDS[num] is None:
                    game_structures.HANDS[num] = entity.pick_up(num)
                elif game_structures.HANDS[1 - num] is None:
                    game_structures.HANDS[1 - num] = entity.pick_up(1 - num)
                elif not entity.picked_up:
                    game_structures.HANDS[num].pos = entity.pos
                    area.entity_list.append(entities.ItemEntity(game_structures.HANDS[num]))
                    game_structures.HANDS[num] = entity.pick_up(num)
                return
    if game_structures.HANDS[num] is None:
        return
    game_structures.HANDS[num].action(game_structures.HANDS[num])


screen = game_structures.Place(
    tick=tick,
    enter=run_start_end.start,
    catcher=event_catcher
)