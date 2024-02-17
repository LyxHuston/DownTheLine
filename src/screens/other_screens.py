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
from general_use import game_structures, utility
from data import game_states
from run_game import ingame
from screens import run_start_end

fade_counter = 0
tick_counter = 0
next_tick_max = 0

overlay = pygame.Surface(game_structures.SCREEN.get_size(), pygame.SRCALPHA)


def die():
    global fade_counter, tick_counter, next_tick_max

    run_start_end.log_run(run_start_end.RunEndReasons.die)

    game_structures.BUTTONS.add_button(
        game_structures.Button.make_text_button("Press Space or click to skip", 40, (game_states.WIDTH, 0), skip_wait,
                                                background_color=(0, 0, 0), outline_color=(255, 255, 255),
                                                border_width=5, x_align=1, y_align=0,
                                                special_press=ingame.Inputs.ignore_pickup))

    fade_counter = 0
    tick_counter = 0
    next_tick_max = 0


def skip_wait():
    global fade_counter
    fade_counter = 255


def dead():
    global fade_counter, tick_counter, next_tick_max

    if fade_counter < 255:
        overlay.fill((0, 0, 0, fade_counter))
        game_structures.PLACES.in_game.value.tick(tick_counter == 0)
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
        game_structures.BUTTONS.clear()
        game_structures.BUTTONS.add_button(
            game_structures.Button.make_text_button("You Died", 400, (game_states.WIDTH // 2, 400), None,
                                                    background_color=(0, 0, 0), outline_color=(255, 255, 255)))
        game_structures.BUTTONS.add_button(
            game_structures.Button.make_text_button(f"You traveled {game_states.RECORD_DISTANCE} units", 80,
                                                    (game_states.WIDTH // 2 - 600, 700), None,
                                                    background_color=(0, 0, 0), outline_color=(255, 255, 255),
                                                    text_align=0, x_align=0))
        game_structures.BUTTONS.add_button(
            game_structures.Button.make_text_button(f"You passed {game_states.AREAS_PASSED} areas", 80,
                                                    (game_states.WIDTH // 2 - 600, 800), None,
                                                    background_color=(0, 0, 0), outline_color=(255, 255, 255),
                                                    text_align=0, x_align=0))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button("Play Again", 100, (
            game_states.WIDTH // 2 - 800, game_states.HEIGHT - 200), game_structures.PLACES.in_game.value.start,
                                                                                   background_color=(0, 0, 0),
                                                                                   outline_color=(255, 255, 255),
                                                                                   border_width=5, text_align=0.5,
                                                                                   enforce_width=600))
        game_structures.BUTTONS.add_button(
            game_structures.Button.make_text_button("Home", 100, (game_states.WIDTH // 2, game_states.HEIGHT - 200),
                                                    game_structures.PLACES.main.value.start, background_color=(0, 0, 0),
                                                    outline_color=(255, 255, 255), border_width=5, text_align=0.5,
                                                    enforce_width=600))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button("Quit", 100, (
            game_states.WIDTH // 2 + 800, game_states.HEIGHT - 200), exit_game, background_color=(0, 0, 0),
                                                                                   outline_color=(255, 255, 255),
                                                                                   border_width=5, text_align=0.5,
                                                                                   enforce_width=600))
        fade_counter = 256
    else:
        pass


def won():
    pass


def exit_game():
    game_states.RUNNING = False


def cleanup_game():
    game_structures.BUTTONS.clear()
    for area in game_structures.AREA_QUEUE:
        area.cleanup()


dead_screen = game_structures.Place(
    tick=dead,
    enter=die,
    end=cleanup_game
)

won_screen = game_structures.Place(
    tick=won,
    enter=utility.passing,
    end=cleanup_game
)
