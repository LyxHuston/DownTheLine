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
import utility
import game_structures
import game_states
import pygame
import sys
import draw_constants


def check_flags(flags: list[str], error_on_duplicates: bool = False):
    """
    checks for if flags exist, and if so where.  If appears twice (or different versions) errors
    :return: index of flag
    """
    index = 0
    for flag in flags:
        if flag in sys.argv:
            if index:
                raise SyntaxError("Duplicate flags")
            if sys.argv.count(flag) > 1:
                raise SyntaxError("Duplicate flags")
            index = sys.argv.index(flag)
            if not error_on_duplicates:
                return index
    return index


if len(sys.argv) > 1:
    if sys.argv[1] == "testing":
        backdrop = (128, 128, 128)
        game_structures.SCREEN = pygame.display.set_mode((1000, 700))
    else:
        backdrop = (0, 0, 0)
        game_structures.SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    flag = check_flags(["--autosave", "-a"])
    if flag:
        game_states.AUTOSAVE = True
    flag = check_flags(["--invulnerable", "-i"])
    if flag:
        game_states.INVULNERABLE = True
    flag = check_flags(["--seed", "-s"], error_on_duplicates=True)
    if flag:
        game_states.CUSTOM_SEED = True
        try:
            game_states.SEED = int(sys.argv[flag + 1])
        except IndexError:
            print("Provide a seed.")
            exit(2)
        except ValueError:
            print("The seed must be an integer.")
            exit(2)
    flag = check_flags(["--print_seed", "-p"])
    if flag:
        game_states.PRINT_SEED = True
else:
    backdrop = (0, 0, 0)
    game_structures.SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN + pygame.SRCALPHA)
pygame.display.set_caption("Down the Line")
game_states.WIDTH, game_states.HEIGHT = game_structures.SCREEN.get_size()
game_structures.determine_screen()
# print(game_states.WIDTH, game_states.HEIGHT)
game_states.CAMERA_THRESHOLDS = (min(400, round(game_states.HEIGHT // 5)), min(400, round(game_states.HEIGHT // 5)))

pygame.init()
game_structures.init()

draw_constants.hearts_y = game_states.HEIGHT - draw_constants.row_separation


game_structures.CUSTOM_EVENT_CATCHERS.append(lambda catch: game_states.PLACE.catcher(catch))


if __name__ == "__main__":

    game_structures.switch_to_place(game_structures.PLACES.main)

    while game_states.RUNNING:  # outer loop only for when the try except successfully handles it
        try:  # try catch to see if the area knows how to handle the error
            while game_states.RUNNING:  # main loop
                game_structures.SCREEN.fill(backdrop)
                game_states.PLACE.tick()
                utility.tick()
            game_states.PLACE.exit()
        except RuntimeError as E:
            if not game_states.PLACE.crash(E):
                utility.log_error(E)
                game_states.RUNNING = False
