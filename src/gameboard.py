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

draws, loads, and unloads the game scene.
"""


import game_states
import game_structures
from game_areas import add_game_area
import pygame
import abilities
import ingame
import draw_constants


player_img = pygame.image.load("resources/player/player.png")
heart_img = pygame.image.load("resources/player/hearts.png")


camera_move = 0


def tick(do_tick: bool = True):
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    also, handles shaking the board
    :return:
    """
    global camera_move
    if do_tick:
        for i in range(len(game_structures.AREA_QUEUE)):
            if game_structures.AREA_QUEUE[i].start_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT and not game_structures.AREA_QUEUE[i].initialized:
                game_structures.AREA_QUEUE[i].initialized = True
                game_structures.AREA_QUEUE[i].final_load()
                break
            if game_structures.AREA_QUEUE[i].start_coordinate > game_states.CAMERA_BOTTOM + game_states.HEIGHT:
                break
        if game_structures.AREA_QUEUE[0].end_coordinate < game_states.CAMERA_BOTTOM:
            for entity in game_structures.AREA_QUEUE[0].entity_list:
                if entity.y > game_structures.AREA_QUEUE[0].end_coordinate:
                    entity.transfer(game_structures.AREA_QUEUE[1])
                    game_structures.AREA_QUEUE[1].entity_list.append(entity)
            del game_structures.AREA_QUEUE[0]
            game_states.AREAS_PASSED += 1
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
    if game_states.DISTANCE < game_states.CAMERA_BOTTOM + game_states.CAMERA_THRESHOLDS[0]:
        game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0]
    if game_states.DISTANCE > game_states.CAMERA_BOTTOM + game_states.HEIGHT - game_states.CAMERA_THRESHOLDS[1]:
        game_states.CAMERA_BOTTOM = game_states.DISTANCE + game_states.CAMERA_THRESHOLDS[1] - game_states.HEIGHT
    mass = 0
    total = 0
    for i in range(len(game_structures.AREA_QUEUE)):
        area = game_structures.AREA_QUEUE[i]
        if not area.initialized:
            break
        if do_tick:
            ret = area.tick()
            mass += ret[0]
            total += ret[1]
        area.draw()
    game_structures.SCREEN.blit(
        game_structures.FONTS[128].render(
            str(game_states.RECORD_DISTANCE),
            False,
            (255, 255, 255)
        ),
        (0, 0)
    )
    for i in range(game_states.HEALTH):
        game_structures.SCREEN.blit(
            heart_img,
            (i * (draw_constants.icon_size + 4), draw_constants.row_separation)
        )
    abilities.draw_dash_icon(ingame.tick_counter)
    # pygame.draw.circle(
    #     game_structures.SCREEN,
    #     (255, 255, 255),
    #     (game_states.WIDTH / 2, game_states.HEIGHT - game_states.DISTANCE + game_states.CAMERA_BOTTOM),
    #     20
    # )
    for item in game_structures.HANDS:
        if item is None:
            continue
        if do_tick:
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
    camera_move = camera_move // 2
    if total > 0:
        goal = game_states.DISTANCE + game_states.HEIGHT / 2 * (abs(mass) * mass / total ** 2)
    else:
        goal = game_states.DISTANCE + game_states.HEIGHT * game_states.LAST_DIRECTION
    goal -= game_states.HEIGHT / 2
    camera_move += (min(total, 2) + 2) / 324 * (goal - game_states.CAMERA_BOTTOM)
    game_states.CAMERA_BOTTOM += camera_move
