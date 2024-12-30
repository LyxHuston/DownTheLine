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
from data import game_states
from general_use import game_structures
from run_game import gameboard
from screens import end_screens


def setup_main_screen():
    """
    sets up the main screen with buttons and such
    :return:
    """

    run_start_end.start(full=False)

    game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0]

    game_structures.BUTTONS.clear()

    game_structures.BUTTONS.add_button(
        game_structures.Button.make_text_button(
            "Down The Line", 300, (game_states.WIDTH // 2, 0), None, max_line_words=2,
            text_align=0.5, x_align=0.5, y_align=0, background_color=(0, 0, 0, 0)
        )
    )
    game_structures.BUTTONS.add_button(
        game_structures.Button.make_text_button(
            "Play", 100, (
                game_states.WIDTH // 2,
                round(game_states.HEIGHT - 1.5 * (game_states.DISTANCE - game_states.CAMERA_BOTTOM))
            ), game_structures.PLACES.in_game.value.start, text_align=0.5, x_align=0.5, y_align=1,
            background_color=(0, 0, 0, 0)
        )
    )
    game_structures.BUTTONS.add_button(
        game_structures.Button.make_text_button(
            "Quit", 50,
            (game_states.WIDTH // 2, game_states.HEIGHT), end_screens.exit_game, text_align=0.5, x_align=0.5,
            y_align=1, background_color=(0, 0, 0, 0)
        )
    )
    game_structures.BUTTONS.add_button(
        game_structures.Button.make_text_button(
            "Logs", 75, (game_states.WIDTH, game_states.HEIGHT), log_screen.screen.start,
            text_align=0.5, x_align=1, y_align=1, background_color=(0, 0, 0, 0)
        )
    )

    if game_states.ADMIN:
        game_structures.BUTTONS.add_button(
            game_structures.Button.make_text_button(
                "Custom Runs", 75, (0, 0), custom_runs.custom_runs_screen.start, x_align=0,
                y_align=0
            )
        )

    def swap_custom_seed():
        game_states.CUSTOM_SEED = not game_states.CUSTOM_SEED

    custom_seed_button = game_structures.Button.make_text_button(
        "Custom seed?", 75, (0, game_states.HEIGHT), swap_custom_seed, border_width=0,
        text_align=0.5, x_align=0, y_align=1, background_color=(0, 0, 0, 0)
    )
    game_structures.BUTTONS.add_button(custom_seed_button)

    def set_seed(text: str):
        game_states.SEED = get_seed_from_text(text)

    seed_setter_button = game_structures.Button.make_text_button(
        f"seed: {game_states.SEED}", 75, (0, game_states.HEIGHT - custom_seed_button.rect.height),
        lambda: seed_setter_button.write_button_text(
            75, prepend="seed: ", callback=set_seed, x_align=0, y_align=1, start_text=(lambda: str(game_states.SEED))()
        ), border_width=0, text_align=0.5, x_align=0, y_align=1, visible_check=lambda: game_states.CUSTOM_SEED,
        background_color=(0, 0, 0, 0)
    )
    game_structures.BUTTONS.add_button(seed_setter_button)


def get_seed_from_text(text: str):
    try:
        return int(text)
    except:
        # ok, so hashing is a bit.... nondeterministic between runs oops, so instead pretend everything is base 256
        # kinda.
        res = 0
        pw = 0
        for char in reversed(text):
            res = ((res + ord(char) % 256) * 256 ** pw) % (256 ** 8)
            pw = (pw + 1) % 8
        return res


def end():
    game_structures.BUTTONS.clear()


def main_screen():
    """
    draws main screen.  Actually, just draws what's behind it.
    :return:
    """
    gameboard.tick(False, False)


main_screen_place = game_structures.Place(
    tick=main_screen,
    enter=setup_main_screen,
    end=end
)

from screens import run_start_end, log_screen, custom_runs
