"""
draws, loads, and unloads the game scene.
"""


import game_states
import game_structures
from game_areas import add_game_area
import pygame


player_img = pygame.image.load("resources/player/player.png")
heart_img = pygame.image.load("resources/player/hearts.png")


def tick():
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    also, handles shaking the board
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
        for entity in game_structures.AREA_QUEUE[0].entity_list:
            if entity.y > game_states.BOTTOM:
                game_structures.AREA_QUEUE[1].entity_list.append(entity)
        del game_structures.AREA_QUEUE[0]
        add_game_area()
    if game_states.SHAKE_DURATION > 0:
        game_states.SHAKE_DURATION -= 1
        if game_states.SHAKE_DURATION == 0:
            game_states.X_DISPLACEMENT = 0
            game_states.Y_DISPLACEMENT = 0
        else:
            game_states.X_DISPLACEMENT += game_states.X_CHANGE
            if abs(game_states.X_DISPLACEMENT) > abs(game_states.X_LIMIT):
                game_states.X_DISPLACEMENT += 2 * (abs(game_states.X_DISPLACEMENT) - abs(game_states.X_LIMIT)) * ((game_states.X_DISPLACEMENT < 0) * 2 - 1)
                game_states.X_CHANGE *= -1
            game_states.Y_DISPLACEMENT += game_states.Y_CHANGE
            if abs(game_states.Y_DISPLACEMENT) > abs(game_states.Y_LIMIT):
                game_states.Y_DISPLACEMENT += 2 * (abs(game_states.Y_DISPLACEMENT) - abs(game_states.Y_LIMIT)) * ((game_states.Y_DISPLACEMENT < 0) * 2 - 1)
                game_states.Y_CHANGE *= -1
    pygame.draw.line(
        game_structures.SCREEN,
        (255, 255, 255),
        (game_states.WIDTH / 2 + game_states.X_DISPLACEMENT, game_states.HEIGHT),
        (game_states.WIDTH / 2 + game_states.X_DISPLACEMENT, 0),
        3
    )
    game_structures.SCREEN.blit(
        game_structures.FONTS[64].render(
            str(game_states.RECORD_DISTANCE),
            False,
            (255, 255, 255)
        ),
        (0, 0)
    )
    for i in range(game_states.HEALTH):
        game_structures.SCREEN.blit(
            heart_img,
            (i * 66, 68)
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
        (game_structures.to_screen_x(-32), game_structures.to_screen_y(game_states.DISTANCE + 32))
    )
    for i in range(len(game_structures.AREA_QUEUE)):
        area = game_structures.AREA_QUEUE[i]
        if not area.initialized:
            break
        area.tick()
        area.draw()
