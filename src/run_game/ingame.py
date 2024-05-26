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
import math

import pygame
from data import game_states
from general_use import game_structures, utility
from run_game import abilities, gameboard, items, entities, tutorials
from screens import run_start_end


class Inputs:
    up_input = pygame.K_w
    down_input = pygame.K_s
    dash = pygame.K_d
    prefer_pickup = pygame.K_SPACE
    pause = pygame.K_ESCAPE
    next_text = pygame.K_RETURN


loop_counter = 2 ** 10

tick_counter = 0

paused = False


@utility.make_async
def outline_text_button(button: game_structures.Button):
    width = 6
    img = button.img
    outlined = utility.outline_img(img, width, utility.OutlineTypes.Circle)
    if img is button.img:
        button.img = outlined
        button.rect.y -= width
        button.rect.x -= width
        button.rect.width += 2 * width
        button.rect.height += 2 * width


def pause():
    global paused
    paused = True
    run_start_end.switch_to_main_pause()
    width = (game_states.WIDTH - 768) // 2 - 40
    for i, item in enumerate(game_structures.HANDS):
        item: items.Item
        holder: game_structures.ScrollableButtonHolder = run_start_end.PAUSE_BUTTONS[i + 3]
        holder.clear()
        if item is not None:
            description_text = items.description(item)
            holder.add_button(game_structures.Button.make_img_button(
                None,
                item.icon,
                (width // 2, 64),
                "icon",
            ))
            button = game_structures.Button.make_text_button(
                description_text,
                64,
                max_line_pixels=width,
                enforce_width=width,
                background_color=(0, 0, 0, 0),
                outline_color=(255, 255, 255),
                center=(20 + (width - 40) * i, 128),
                x_align=i,
                y_align=0,
                text_align=i
            )
            outline_text_button(button)
            holder.add_button(button)
            holder.fit_y(100)


def tick(do_tick: bool = None):
    if paused:
        gameboard.tick(False)
        return
    if do_tick is None or do_tick:
        if game_states.INVULNERABILITY_LEFT > 0:
            game_states.INVULNERABILITY_LEFT -= 1
        if game_states.HEALTH <= 0 and game_states.PLACE is screen:
            game_structures.switch_to_place(game_structures.PLACES.dead)
        if game_states.HEALTH < 5:
            game_states.TIME_SINCE_LAST_INTERACTION = min(game_states.TIME_SINCE_LAST_INTERACTION + 1, 600)
        if game_states.TIME_SINCE_LAST_INTERACTION == 600 and game_states.HEALTH < 5:
            if game_states.LAST_HEAL >= 20:
                game_states.LAST_HEAL = 0
                game_states.HEALTH += 1
            else:
                game_states.LAST_HEAL += 1
        else:
            if game_states.LAST_HEAL < 20:
                game_states.LAST_HEAL += 1
        global tick_counter
        tick_counter = tick_counter + 1
        if tick_counter >= loop_counter:
            tick_counter = 0
            abilities.last_dash_time -= loop_counter
        # if game_states.GLIDE_SPEED > 0:
        #     if game_states.GLIDE_DURATION == 0:
        #         game_states.GLIDE_SPEED -= game_states.TAPER_AMOUNT
        #         if game_states.GLIDE_SPEED <= 0:
        #             game_states.GLIDE_SPEED = 0
        #     else:
        #         game_states.GLIDE_DURATION -= 1
        #     # spawn dash ripples
        #     if (game_states.GLIDE_DURATION + game_states.GLIDE_SPEED // game_states.TAPER_AMOUNT) % 2 == 1:
        #         gameboard.PARTICLE_BOARD.add(entities.DASH_RIPPLE_PARTICLES(
        #             (0, game_states.DISTANCE)
        #         ))
        #     game_states.DISTANCE += game_states.GLIDE_SPEED * game_states.GLIDE_DIRECTION
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


def item_input_catch(num: int) -> None:
    if game_structures.HANDS[num] is None or pygame.key.get_pressed()[Inputs.prefer_pickup]:
        pickup_to_hand(num)
        return
    if items.prevent_other_use(game_structures.HANDS[1 - num]):
        return
    game_structures.HANDS[num].action(game_structures.HANDS[num])


def release_hand(hand: int) -> None:
    item = game_structures.HANDS[hand]
    if item is None:
        return
    item.release(item)


mouse_events = {
    pygame.MOUSEBUTTONDOWN: item_input_catch,
    pygame.MOUSEBUTTONUP: release_hand
}
mouse_button_mapping = (None, 0, None, 1)


def event_catcher(event: pygame.event.Event) -> bool:
    global paused
    if paused:
        if event.type == pygame.KEYDOWN and event.key == Inputs.pause:
            paused = False
        return True
    if game_states.HEALTH <= 0:
        return False
    if event.type == pygame.WINDOWFOCUSLOST:
        pause()
    if event.type == pygame.KEYDOWN:
        if event.key == Inputs.dash:
            abilities.dash_input_catch(tick_counter)
            return True
        elif event.key == Inputs.pause:
            pause()
            return True
        elif event.key == pygame.K_RETURN:
            tutorials.next_pressed()
            return True
    elif event.type in mouse_events:
        if event.button <= 3:
            hand = mouse_button_mapping[event.button]
            if hand is not None:
                mouse_events[event.type](hand)
                return True
    return False


pickup_points = 8
pickup_rad = 40


def spawn_pickup_particles():
    for i in range(pickup_points):
        rot = 2 * math.pi * i / pickup_points
        gameboard.PARTICLE_BOARD.add(entities.PICKUP_SPARKLES(
            (pickup_rad * math.cos(rot), game_states.DISTANCE + pickup_rad * math.sin(rot))
        ))


def pickup_to_hand(num: int):
    for entity in gameboard.ENTITY_BOARD:
        if entity.is_holder:
            entity = entity.holding
        if not entity.is_item_entity:
            continue
        if not isinstance(entity.pos[0], int):
            continue
        if not (abs(entity.x) < 60 and abs(entity.y - game_states.DISTANCE) < entity.height // 2 + 10):
            continue
        if game_structures.HANDS[num] is None:
            game_structures.PLAYER_ENTITY.pickup_to(entity, num)
        elif game_structures.HANDS[1 - num] is None:
            game_structures.PLAYER_ENTITY.pickup_to(entity, 1 - num)
        elif items.swappable(game_structures.HANDS[num]):
            game_structures.PLAYER_ENTITY.pickup_to(entity, num)
            spawn_pickup_particles()
        return True
    return False


def crash(e: Exception):
    from screens import main_screen
    from general_use import utility
    run_start_end.log_run(run_start_end.RunEndReasons.error)
    utility.log_error(e)
    game_structures.ALERTS.add_alert(
        "An error occurred during the run that was not caught!  Check the log for details."
    )
    main_screen.main_screen_place.start()
    return True


screen = game_structures.Place(
    tick=tick,
    enter=run_start_end.start,
    end=run_start_end.end,
    catcher=event_catcher,
    exit_on=lambda: run_start_end.log_run(run_start_end.RunEndReasons.close),
    crash_on=crash
)
