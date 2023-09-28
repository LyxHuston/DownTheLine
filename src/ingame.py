"""
in-game calculations
"""

import gameboard
import pygame
import game_states
import game_structures
import items


dash_img = pygame.image.load("resources/abilities/ability_icons/dash_icon.png")


class Inputs:
    up_input = pygame.K_w
    down_input = pygame.K_s
    ability_1_input = pygame.K_a
    ability_2_input = pygame.K_d


loop_counter = 2 ** 10

tick_counter = 0

def tick():
    global tick_counter
    tick_counter = tick_counter + 1
    if tick_counter >= loop_counter:
        global last_dash_time, last_press_for_dash
        tick_counter = 0
        last_dash_time -= loop_counter
        last_press_for_dash -= loop_counter
    if game_states.GLIDE_SPEED > 0:
        if game_states.GLIDE_DURATION == 0:
            game_states.GLIDE_SPEED -= game_states.TAPER_AMOUNT
            if game_states.GLIDE_SPEED <= 0:
                game_states.GLIDE_SPEED = 0
        else:
            game_states.GLIDE_DURATION -= 1
        game_states.DISTANCE += game_states.GLIDE_SPEED * game_states.GLIDE_DIRECTION
    else:
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
    game_structures.SCREEN.blit(
        dash_img,
        (0, 136)
    )
    pygame.draw.rect(
        game_structures.SCREEN,
        (0, 0, 0),
        pygame.Rect(0, 136, 64 - round(-64 * (last_dash_time - tick_counter) / dash_cooldown), 64),
    )
    gameboard.tick()


dash_sensitivity = 20

last_press_for_dash = -1 - dash_sensitivity

dash_cooldown = 100

last_dash_time = -1 - dash_cooldown

last_dash_input = 0


def event_catcher(event: pygame.event.Event) -> bool:
    match event.type:
        case pygame.KEYDOWN:
            match event.key:
                case Inputs.up_input:
                    dash_input_catch(1)
                    return True
                case Inputs.down_input:
                    dash_input_catch(-1)
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


def dash_input_catch(direction: int) -> None:
    global dash_cooldown, dash_sensitivity, last_dash_time, last_press_for_dash, last_dash_input
    if last_dash_time + dash_cooldown > tick_counter:
        return
    if last_dash_input == direction and last_press_for_dash + dash_sensitivity >= tick_counter:
        last_dash_input = 0
        last_dash_time = tick_counter
        game_states.GLIDE_SPEED = 25
        game_states.TAPER_AMOUNT = 100
        game_states.GLIDE_DURATION = 20
        game_states.GLIDE_DIRECTION = direction
        game_structures.begin_shake(
            20,
            (3, 0),
            (1, 0)
        )
        return
    last_dash_input = direction
    last_press_for_dash = tick_counter


def item_input_catch(num: int) -> None:
    for area in game_structures.AREA_QUEUE:
        if not area.initialized:
            break
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


game_structures.CUSTOM_EVENT_CATCHERS.append(event_catcher)