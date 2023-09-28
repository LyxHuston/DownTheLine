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


pygame.init()
pygame.display.set_caption("Down the Line")
game_states.WIDTH, game_states.HEIGHT = game_structures.SCREEN.get_size()
game_states.CAMERA_THRESHOLDS = (min(100, round(game_states.HEIGHT / 4)), min(500, round(game_states.HEIGHT / 2)))
game_structures.init()
# print(sys.int_info)
game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
# print(game_states.SEED)
game_states.PLACE = game_structures.PLACES.in_game
for i in range(game_states.AREA_QUEUE_MAX_LENGTH):
    add_game_area().join()

while game_states.RUNNING:
    game_structures.SCREEN.fill((0, 0, 0))
    game_states.PLACE()
    utility.tick()