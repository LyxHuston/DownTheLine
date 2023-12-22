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

handles the ending screens for the game, both won and lost
"""

import pygame
import game_structures
import game_states
import ingame
import game_start


fade_counter = 0
tick_counter = 0
next_tick_max = 0

overlay = pygame.Surface(game_structures.SCREEN.get_size(), pygame.SRCALPHA)


def lose():
    global fade_counter, tick_counter, next_tick_max

    game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
        "Press Space or click to skip",
        40,
        skip_wait,
        (game_states.WIDTH, 0),
        x_align=1,
        y_align=0,
        background_color=(0, 0, 0),
        outline_color=(255, 255, 255),
        border_width=5,
        special_press=ingame.Inputs.ignore_pickup
    ))

    fade_counter = 0
    tick_counter = 0
    next_tick_max = 0
    del game_structures.CUSTOM_EVENT_CATCHERS[1]


def skip_wait():
    global fade_counter
    fade_counter = 255


def lost():
    global fade_counter, tick_counter, next_tick_max

    if fade_counter < 255:
        overlay.fill((0, 0, 0, fade_counter))
        game_structures.PLACES.in_game(tick_counter == 0)
        game_structures.SCREEN.blit(
            overlay,
            (0, 0)
        )
        fade_counter += 1
        tick_counter += 1
        if tick_counter >= next_tick_max:
            tick_counter = 0
            next_tick_max += 0.5
    elif fade_counter == 255:
        import main
        game_structures.BUTTONS.clear()
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "You Died",
            400,
            None,
            (game_states.WIDTH // 2, 400),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255)
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            f"You traveled {game_states.RECORD_DISTANCE} units",
            80,
            None,
            (game_states.WIDTH // 2 - 600, 700),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            text_align=0,
            x_align=0
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            f"You passed {game_states.AREAS_PASSED} areas",
            80,
            None,
            (game_states.WIDTH // 2 - 600, 800),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            text_align=0,
            x_align=0
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "Play Again",
            100,
            game_start.start,
            (game_states.WIDTH // 2 - 400, game_states.HEIGHT - 200),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            enforce_width=600,
            border_width=5,
            text_align=0.5
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "Quit",
            100,
            exit,
            (game_states.WIDTH // 2 + 400, game_states.HEIGHT - 200),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            enforce_width=600,
            border_width=5,
            text_align=0.5
        ))
        if game_states.AUTOSAVE:
            game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
                "Refresh from Save",
                25,
                refresh_from_save,
                (game_states.WIDTH // 2, game_states.HEIGHT - 40),
                background_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                enforce_width=600,
                border_width=5,
                text_align=0.5
            ))
        fade_counter = 256
    else:
        pass


def won():
    pass


def exit():
    game_states.RUNNING = False


def refresh_from_save():
    """
    dev tool
    :return:
    """
    for name, val in game_states.SAVE_DATA.items():
        setattr(game_states, name, val)
    game_structures.HANDS = game_states.HANDS_SAVE
    game_structures.AREA_QUEUE = game_states.QUEUE_SAVE
    # game_states.DISTANCE = game_structures.AREA_QUEUE[0].start_coordinate - 100
    game_states.HEALTH = 5
    game_states.PLACE = game_structures.PLACES.in_game
    game_structures.BUTTONS.clear()
    game_structures.CUSTOM_EVENT_CATCHERS.append(ingame.event_catcher)
