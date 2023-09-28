"""
draws, loads, and unloads the game scene.
"""


import game_states
import game_structures
from game_areas import add_game_area
import pygame


def tick():
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    :return:
    """
    # if game_structures.AREA_QUEUE[0].end_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT:
    #     del game_structures.AREA_QUEUE[0]
    #     add_game_area()
    pygame.draw.line(
        game_structures.SCREEN,
        (255, 255, 255),
        (game_states.WIDTH / 2, game_states.HEIGHT),
        (game_states.WIDTH / 2, 0),
        3
    )
    game_structures.SCREEN.blit(
        game_structures.FONTS[20].render(
            str(game_states.RECORD_DISTANCE),
            False,
            (255, 255, 255)
        ),
        (0, 0)
    )
    pygame.draw.circle(
        game_structures.SCREEN,
        (255, 255, 255),
        (game_states.WIDTH / 2, game_states.HEIGHT - game_states.DISTANCE + game_states.CAMERA_BOTTOM),
        20
    )
    for area in game_structures.AREA_QUEUE:
        if area.start_coordinate > game_states.CAMERA_BOTTOM + game_states.HEIGHT:
            break
        area.draw()