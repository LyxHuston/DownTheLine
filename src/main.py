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
import tutorials
import utility
import game_structures
import game_states
import pygame
from game_areas import add_game_area
import ingame
import random
import sys


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
    match sys.argv[1]:
        case "testing":
            backdrop = (128, 128, 128)
            game_structures.SCREEN = pygame.display.set_mode((1000, 700))
        case _:
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
    game_structures.SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Down the Line")
game_states.WIDTH, game_states.HEIGHT = game_structures.SCREEN.get_size()
game_structures.determine_screen()
# print(game_states.WIDTH, game_states.HEIGHT)
game_states.CAMERA_THRESHOLDS = (min(200, round(game_states.HEIGHT // 6)), min(200, round(game_states.HEIGHT // 6)))


def start():
    game_structures.BUTTONS.clear()
    if not game_states.CUSTOM_SEED:
        game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
    if game_states.PRINT_SEED:
        print("The seed is:", game_states.SEED)

    # game_structures.CUSTOM_EVENT_CATCHERS.append(game_structures.ALERTS.catch_event)  # (commented out because this one should never be removed)
    game_structures.CUSTOM_EVENT_CATCHERS.append(ingame.event_catcher)
    game_states.PLACE = game_structures.PLACES.in_game

    game_states.DISTANCE = 100
    game_states.BOTTOM = 0
    game_states.RECORD_DISTANCE = 0
    game_states.LAST_AREA_END = 0
    # player state management
    game_states.HEALTH = 5
    game_states.LAST_DIRECTION = 1
    game_states.GLIDE_SPEED = 0
    game_states.GLIDE_DIRECTION = 0
    game_states.GLIDE_DURATION = 0
    game_states.TAPER_AMOUNT = 0
    # screen shake management
    game_states.X_DISPLACEMENT = 0
    game_states.Y_DISPLACEMENT = 0
    game_states.SHAKE_DURATION = 0
    game_states.X_LIMIT = 0
    game_states.Y_LIMIT = 0
    game_states.X_CHANGE = 0
    game_states.Y_CHANGE = 0
    # screen
    game_states.CAMERA_BOTTOM = 0
    # area management
    game_states.AREAS_PASSED = 0
    game_states.LAST_AREA = 0

    game_structures.HANDS = [None, None]

    # print(sys.int_info)
    # print(game_states.SEED)

    import entities
    for attr_value in entities.__dict__.values():
        if isinstance(attr_value, type):
            if issubclass(attr_value, entities.Entity):
                attr_value.seen = False
    entities.Slime.seen = True
    import game_areas
    for attr_value in game_areas.__dict__.values():
        if isinstance(attr_value, type):
            if issubclass(attr_value, game_areas.GameArea):
                attr_value.seen = False

    tutorials.add_text(
        "Oh, you're awake.  Good.",
        game_structures.FONTS[100]
    )
    tutorials.add_text(
        "You need to be able to defend yourself.  They won't let you live in peace.",
        game_structures.FONTS[100]
    )
    tutorials.add_text(
        "Can you go up?",
        game_structures.FONTS[100]
    )
    tutorials.add_text(
        "Use the w and s keys to move up and down.",
        game_structures.TUTORIAL_FONTS[90]
    )

    game_structures.AREA_QUEUE.clear()
    add_game_area().join()
    for i in range(game_states.AREA_QUEUE_MAX_LENGTH - 1):
        add_game_area()


pygame.init()
game_structures.init(start)

if __name__ == "__main__":
    start()

    while game_states.RUNNING:
        game_structures.SCREEN.fill(backdrop)
        game_states.PLACE()
        utility.tick()