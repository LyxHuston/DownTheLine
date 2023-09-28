"""
main ran file for the game
"""


import utility
import game_structures
import game_states
import pygame
from game_areas import add_game_area
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
game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
add_game_area().join()
for i in range(game_states.AREA_QUEUE_MAX_LENGTH - 1):
    add_game_area()
pygame.init()
game_structures.init()
game_states.PLACE = game_structures.PLACES.in_game
# print(sys.int_info)
# print(game_states.SEED)


while game_states.RUNNING:
    game_structures.SCREEN.fill(backdrop)
    game_states.PLACE()
    utility.tick()