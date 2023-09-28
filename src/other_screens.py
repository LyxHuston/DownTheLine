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


fade_counter = 0
tick_counter = 0
next_tick_max = 0

overlay = pygame.Surface(game_structures.SCREEN.get_size(), pygame.SRCALPHA)


def lose():
    global fade_counter, tick_counter, next_tick_max

    fade_counter = 0
    tick_counter = 0
    next_tick_max = 0
    del game_structures.CUSTOM_EVENT_CATCHERS[1]


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
        print("adding end screen buttons")
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "You Died",
            200,
            None,
            (game_states.WIDTH // 2, 200),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255)
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            f"You traveled {game_states.DISTANCE} units",
            40,
            None,
            (game_states.WIDTH // 2 - 300, 300),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            text_align=0,
            x_align=0
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            f"You passed {game_states.AREAS_PASSED} areas",
            40,
            None,
            (game_states.WIDTH // 2 - 300, 350),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            text_align=0,
            x_align=0
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "Play Again",
            50,
            main.start,
            (game_states.WIDTH // 2 - 200, game_states.HEIGHT - 100),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            enforce_width=300,
            border_width=5,
            text_align=0.5
        ))
        game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
            "Quit",
            50,
            exit,
            (game_states.WIDTH // 2 + 200, game_states.HEIGHT - 100),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            enforce_width=300,
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