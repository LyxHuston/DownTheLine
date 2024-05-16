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

main ran file for the game
"""
import argparse
import cProfile
import ast

import pygame

from data import draw_constants, game_states
from general_use import game_structures, utility


def run():
    game_structures.switch_to_place(game_structures.PLACES.main)

    while game_states.RUNNING:  # outer loop only for when the try except successfully handles it
        try:  # try catch to see if the area knows how to handle the error
            while game_states.RUNNING:  # main loop
                game_structures.SCREEN.fill(backdrop)
                game_states.PLACE.tick()
                utility.tick()
            game_states.PLACE.exit()
        except Exception as E:
            if game_states.RUNNING:
                if not game_states.PLACE.crash(E):
                    utility.log_error(E)
                    game_states.RUNNING = False

    pygame.quit()


def int_tuple_from_string(num_args: int, argname: str, value_range: tuple[int | None, int | None] = (None, None)):
    def inner(string: str):
        try:
            val = ast.literal_eval(string)
            if not isinstance(val, tuple):
                raise TypeError("Argument must be a tuple.")
            if len(val) != num_args:
                raise ValueError(f"Argument must be {num_args}(s) items long.")
            for i, v in enumerate(val):
                if not isinstance(v, int):
                    raise TypeError(f"Item {i} is not an integer.")
                if (value_range[0] is not None and v < value_range[0]) or (
                        value_range[1] is not None and v > value_range[1]):
                    raise ValueError(
                        f"Item {i} is out of range: [{'' if value_range[0] is None else value_range[0]}:{'' if value_range[1] is None else value_range[1]}]"
                    )
            return val
        except Exception:
            raise ValueError(f"Command line argument {argname} was given invalid value: {ascii(string)}")
    return inner


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Down The Line")
    parser.add_argument(
        "mode", default="play", choices=["testing", "test_images", "play"], nargs="?",
        help="The mode for the program to run in."
    )
    parser.add_argument(
        "-c", "--with_interactive_console", action="store_true",
        help="Start up an interactive console during runtime.  Please close before exit."
    )
    parser.add_argument(
        "-s", "--print_seed", action="store_true",
        help="Print the seed to console at the start of the run."
    )
    parser.add_argument(
        "-p", "--profile", action="store_true",
        help="Run the code profiler during runtime"
    )
    parser.add_argument(
        "-d", "--dimensions",
        type=int_tuple_from_string(2, "dimensions", (1, None)), default=None,
        help="Set dimensions for the window.  If blank, is fullscreen.  Has priority over testing mode."
    )
    parser.add_argument(
        "-b", "--backdrop",
        type=int_tuple_from_string(3, "backdrop", (0, 255)), default=None,
        help="Set the backdrop color for the game.  Useful, occasionally, for testing purposes."
    )
    args = parser.parse_args()

    __run = True

    dimens = (0, 0)
    prompt = "run"
    if args.mode == "testing":
        backdrop = (128, 128, 128)
        dimens = (1000, 700)
    elif args.mode == "test_images":
        from data import images
        prompt = "images.test_images"
        __run = False
    elif args.mode == "play":
        backdrop = (0, 0, 0)

    if __run:
        if args.print_seed:
            game_states.PRINT_SEED = True
        if args.with_interactive_console:
            import code

            print("Warning: the interactive console causes the interpreter"
                  "\nto error on shutdown, which may cause improper closing"
                  "\nof resources, potentially leading to memory issues."
                  "\nIt is not recommended to use this option in regular use."
                  "\nTo prevent any errors, use exit() prior to shutting down"
                  "\nthe game.", flush=True)
            utility.make_async(code.InteractiveConsole().interact, daemon=True, log_errors=False)(
                banner="Interactive console for Down The Line", exitmsg="Ending interactive console")

        if args.dimensions is not None:
            dimens = args.dimensions

        if args.backdrop is not None:
            backdrop = args.backdrop

        game_structures.SCREEN = pygame.display.set_mode(dimens, pygame.FULLSCREEN if dimens == (0, 0) else 0)

        pygame.display.set_caption("Down the Line")
        pygame.display.set_icon(pygame.image.load("./resources/down_the_line.ico"))
        game_states.WIDTH, game_states.HEIGHT = game_structures.SCREEN.get_size()
        game_structures.determine_screen()
        # print(game_states.WIDTH, game_states.HEIGHT)
        game_states.CAMERA_THRESHOLDS = (
            min(400, round(game_states.HEIGHT // 5)), min(400, round(game_states.HEIGHT // 5))
        )

        pygame.init()
        game_structures.init()

        draw_constants.hearts_y = game_states.HEIGHT - draw_constants.row_separation

        game_structures.CUSTOM_EVENT_CATCHERS.append(lambda catch: game_states.PLACE.catcher(catch))

    # prompt is never user defined
    if not prompt.endswith("()"):
        prompt += "()"
    if args.profile:
        cProfile.run(prompt)
    else:
        exec(prompt)
