"""
in-game calculations
"""

import gameboard
import pygame
import game_states
import game_structures
import items
import abilities


class Inputs:
    up_input = pygame.K_w
    down_input = pygame.K_s
    ability_1_input = pygame.K_a
    ability_2_input = pygame.K_d


loop_counter = 2 ** 10

tick_counter = 0


def tick(do_tick: bool = None):
    if do_tick is None or do_tick:
        if game_states.HEALTH <= 0 and game_states.PLACE is tick:
            import other_screens
            other_screens.lose()
            game_states.PLACE = game_structures.PLACES.lost
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
        if game_states.DISTANCE < game_states.CAMERA_BOTTOM + game_states.CAMERA_THRESHOLDS[0]:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0]
        if game_states.DISTANCE > game_states.CAMERA_BOTTOM + game_states.HEIGHT - game_states.CAMERA_THRESHOLDS[1]:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE + game_states.CAMERA_THRESHOLDS[1] - game_states.HEIGHT
        if game_states.DISTANCE > game_states.RECORD_DISTANCE:
            game_states.RECORD_DISTANCE = game_states.DISTANCE
    abilities.draw_dash_icon(tick_counter)
    gameboard.tick(do_tick if isinstance(do_tick, bool) else True)


def event_catcher(event: pygame.event.Event) -> bool:
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
    for area in game_structures.initialized_areas():
        for i in range(len(area.entity_list)):
            entity = area.entity_list[i]
            if not isinstance(entity, items.Item):
                continue
            if not isinstance(entity.pos[0], int):
                continue
            if not entity.img.get_rect(center=entity.pos).colliderect(
                    pygame.Rect(-32, game_states.DISTANCE - 10, 64, 20)):
                continue
            if game_structures.HANDS[num] is None:
                del area.entity_list[i]
            else:
                game_structures.HANDS[num].pos = entity.pos
                area.entity_list[i] = game_structures.HANDS[num]
            game_structures.HANDS[num] = entity
            entity.pos = num
            return
    if game_structures.HANDS[num] is None:
        return
    game_structures.HANDS[num].action(game_structures.HANDS[num])