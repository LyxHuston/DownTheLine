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

describe the home screen of the game
"""
import game_states
import game_structures
import gameboard
import other_screens
import run_start_end


def setup_main_screen():
    """
    sets up the main screen with buttons and such
    :return:
    """

    run_start_end.start()

    game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0]

    game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
        "Down The Line",
        300,
        None,
        (game_states.WIDTH // 2, 0),
        (0, 0, 0, 0),
        (255, 255, 255),
        0,
        text_align=0.5,
        x_align=0.5,
        y_align=0,
        max_line_words=2
    ))
    game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
        "Play",
        100,
        game_structures.PLACES.in_game.value.start,
        (game_states.WIDTH // 2, game_states.HEIGHT - 1.5 * (game_states.DISTANCE - game_states.CAMERA_BOTTOM)),
        (0, 0, 0, 0),
        (255, 255, 255),
        0,
        text_align=0.5,
        x_align=0.5,
        y_align=1,
        max_line_words=2
    ))
    game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
        "Quit",
        50,
        other_screens.exit,
        (game_states.WIDTH // 2, game_states.HEIGHT),
        (0, 0, 0, 0),
        (255, 255, 255),
        0,
        text_align=0.5,
        x_align=0.5,
        y_align=1,
        max_line_words=2
    ))
    game_structures.BUTTONS.add_button(game_structures.Button.make_text_button(
        "Logs",
        75,
        log_screen.screen.start,
        (game_states.WIDTH, game_states.HEIGHT),
        (0, 0, 0, 0),
        (255, 255, 255),
        0,
        text_align=0.5,
        x_align=1,
        y_align=1,
        max_line_words=2
    ))


def main_screen():
    """
    draws main screen.  Actually, just draws what's behind it.
    :return:
    """
    gameboard.tick(False, False)


def end():
    game_structures.BUTTONS.clear()


main_screen_place = game_structures.Place(
    tick=main_screen,
    enter=setup_main_screen,
    end=end
)

import log_screen
