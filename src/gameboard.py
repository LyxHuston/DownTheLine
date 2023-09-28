"""
draws, loads, and unloads the game scene.
"""


import game_states
import game_structures
from game_areas import add_game_area
import pygame


player_img = pygame.image.load("resources/player/player.png")


def tick():
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    :return:
    """
    for i in range(len(game_structures.AREA_QUEUE)):
        if game_structures.AREA_QUEUE[i].start_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT and not game_structures.AREA_QUEUE[i].initialized:
            game_structures.AREA_QUEUE[i].initialized = True
            game_structures.AREA_QUEUE[i].enter()
            break
        if game_structures.AREA_QUEUE[i].start_coordinate > game_states.CAMERA_BOTTOM + game_states.HEIGHT:
            break
    if game_structures.AREA_QUEUE[0].end_coordinate < game_states.CAMERA_BOTTOM:
        del game_structures.AREA_QUEUE[0]
        add_game_area()
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
    game_structures.SCREEN.blit(
        game_structures.FONTS[20].render(
            str(game_states.HEALTH) + "/5",
            False,
            (255, 255, 255)
        ),
        (0, 30)
    )
    # pygame.draw.circle(
    #     game_structures.SCREEN,
    #     (255, 255, 255),
    #     (game_states.WIDTH / 2, game_states.HEIGHT - game_states.DISTANCE + game_states.CAMERA_BOTTOM),
    #     20
    # )
    for item in game_structures.HANDS:
        if item is None:
            continue
        item.tick(item)
        item.draw(item)
    game_structures.SCREEN.blit(
        pygame.transform.flip(
            player_img,
            False,
            game_states.LAST_DIRECTION == -1
        ),
        (game_states.WIDTH / 2 - 32, game_states.HEIGHT - game_states.DISTANCE + game_states.CAMERA_BOTTOM - 32)
    )
    for area in game_structures.AREA_QUEUE:
        if not area.initialized:
            break
        area.tick()
    for area in game_structures.AREA_QUEUE:
        if not area.initialized:
            break
        area.draw()