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
from game_areas import add_game_area
import ingame
import random
import sys


match sys.argv[1] if len(sys.argv) > 1 else None:
    case "testing":
        backdrop = (128, 128, 128)
        game_structures.SCREEN = pygame.display.set_mode((1000, 700))
    case _:
        backdrop = (0, 0, 0)
        game_structures.SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Down the Line")
game_states.WIDTH, game_states.HEIGHT = game_structures.SCREEN.get_size()
game_states.CAMERA_THRESHOLDS = (min(100, round(game_states.HEIGHT / 4)), min(500, round(game_states.HEIGHT / 2)))


def start():
    game_structures.BUTTONS.clear()
    game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)

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
    # area management
    game_states.AREAS_PASSED = 0
    game_states.LAST_AREA = 0
    game_states.AREA_QUEUE_MAX_LENGTH = 3

    game_structures.HANDS = [None, None]

    # print(sys.int_info)
    # print(game_states.SEED)

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