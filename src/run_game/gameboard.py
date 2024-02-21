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
from general_use import game_structures
from run_game.game_areas import add_game_area
import pygame
from run_game import abilities, game_areas, ingame, tutorials, entities
from data import draw_constants, game_states
from screens import run_start_end
import math


player_img = pygame.image.load("./resources/player/player.png")
heart_img = pygame.image.load("./resources/player/hearts.png")


class HeartData:
    """
    helper class to compute heart jiggle.
    """

    def __init__(self, direction):
        self.x = 0
        self.y = 0
        self.x_dir = math.cos(direction)
        self.y_dir = math.sin(direction)
        self.since_last_direction_change = 0

    def tick(self):
        limit = 5 * max(4 - game_states.HEALTH, 0) * max(3 - game_states.HEALTH, 1)
        if limit == 0:
            self.x = 0
            self.y = 0
            return
        speed = (4 - game_states.HEALTH) * max(1, (3 - game_states.HEALTH))
        self.x += self.x_dir * speed
        if abs(self.x) > limit:
            self.x_dir *= -1
            self.x = 0 if abs(self.x) > 2 * limit else 2 * (abs(self.x) - limit) * ((self.x > 0) * 2 - 1)
        self.y += self.y_dir * speed
        if abs(self.y) > limit:
            self.y_dir *= -1
            self.y = 0 if abs(self.y) > 2 * limit else 2 * (abs(self.y) - limit) * ((self.y > 0) * 2 - 1)
        if game_states.HEALTH <= 2:
            if self.since_last_direction_change >= 30 * game_states.HEALTH + 10:
                self.since_last_direction_change = 0
                angle = 224 - 67 * game_states.HEALTH
                cos, sin = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                self.x_dir, self.y_dir = self.x_dir*cos - self.y_dir*sin, self.x_dir*sin + self.y_dir*cos
            else:
                self.since_last_direction_change += 1

    def generate_pos(self, pos: tuple[int, int]):
        return pos[0] + self.x, pos[1] + self.y - 5 * max(4 - game_states.HEALTH, 0) ** 2 / 2


heart_data: list[HeartData] = []


camera_move = 0


ENTITY_BOARD: list[entities.Entity] = []
NEW_ENTITIES: list[entities.Entity] = []

PARTICLE_BOARD: set[entities.Particle] = set()


def tick(do_tick: bool = True, draw_gui: bool = True):
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    also, handles shaking the board
    :return:
    """
    global camera_move
    if do_tick:
        if game_structures.AREA_QUEUE[0].end_coordinate < game_states.CAMERA_BOTTOM:  # despawn
            removing: game_areas.GameArea = game_structures.AREA_QUEUE.popleft()
            i = 0
            for entity in ENTITY_BOARD:
                entity.despawn()
                i += 1
                if isinstance(entity, entities.AreaStopper):
                    break
            del ENTITY_BOARD[:i]
            if removing.__class__.__name__ in run_start_end.GameAreaLog.areas_dict:
                run_start_end.GameAreaLog.areas_dict[removing.__class__.__name__] += 1
            game_states.AREAS_PASSED += 1
            add_game_area()
        with game_structures.AREA_QUEUE_LOCK:
            for area in game_structures.AREA_QUEUE:  # load next that is becoming onscreen
                if area.start_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT and not area.initialized:
                    area.initialized = True
                    area.final_load()
                    ENTITY_BOARD.extend(area.entity_list)
                    area.entity_list = None  # so that it will be forced to error
                    break
                if area.start_coordinate > game_states.CAMERA_BOTTOM + game_states.HEIGHT:
                    break
        if game_states.SHAKE_DURATION > 0:
            game_states.SHAKE_DURATION -= 1
            if game_states.SHAKE_DURATION == 0:
                game_states.X_DISPLACEMENT = 0
                game_states.Y_DISPLACEMENT = 0
            else:
                game_states.X_DISPLACEMENT += game_states.X_CHANGE
                if abs(game_states.X_DISPLACEMENT) > abs(game_states.X_LIMIT):
                    game_states.X_DISPLACEMENT += 2 * (abs(game_states.X_DISPLACEMENT) - abs(game_states.X_LIMIT)) * ((
                                                                                                                                  game_states.X_DISPLACEMENT < 0) * 2 - 1)
                    game_states.X_CHANGE *= -1
                game_states.Y_DISPLACEMENT += game_states.Y_CHANGE
                if abs(game_states.Y_DISPLACEMENT) > abs(game_states.Y_LIMIT):
                    game_states.Y_DISPLACEMENT += 2 * (abs(game_states.Y_DISPLACEMENT) - abs(game_states.Y_LIMIT)) * ((
                                                                                                                                  game_states.Y_DISPLACEMENT < 0) * 2 - 1)
                    game_states.Y_CHANGE *= -1
    pygame.draw.line(
        game_structures.SCREEN,
        (255, 255, 255),
        (game_states.WIDTH / 2 + game_states.X_DISPLACEMENT, game_states.HEIGHT),
        (game_states.WIDTH / 2 + game_states.X_DISPLACEMENT, 0),
        3
    )
    if do_tick:
        enforce_goal: int | None = None
        ENTITY_BOARD.extend(NEW_ENTITIES)
        NEW_ENTITIES.clear()
        i: int = 0
        while i < len(ENTITY_BOARD):
            e: entities.Entity = ENTITY_BOARD[i]
            if e.alive:
                i += 1
            else:
                e.die()
                del ENTITY_BOARD[i]
        ENTITY_BOARD.sort(key=lambda e: e.y)
        for area in game_structures.AREA_QUEUE:
            if not area.initialized:
                break
            area.tick()
            if enforce_goal is None:
                enforce_goal = area.enforce_center
        if enforce_goal is None:
            mass: float = 0
            total: int = 0
            i = 0
            for e in ENTITY_BOARD:
                e.index = i
                i += 1
                e.tick()
                dist = e.distance_to_player()
                if dist < game_states.HEIGHT:
                    if not e.in_view(game_states.CAMERA_THRESHOLDS[0]) or dist > 600:
                        mass += (game_states.DISTANCE < e.y) * 2 - 1
                        total += 1
                    elif dist > 300:
                        mass += ((game_states.DISTANCE < e.y) * 2 - 1) * (dist / 300 - 1)
                        total += 1
        else:
            for e in ENTITY_BOARD:
                e.tick()
    # particles need to go on bottom
    with game_structures.AREA_QUEUE_LOCK:
        for area in game_structures.AREA_QUEUE:
            area.draw_particles()
    # entities over particles
    for e in ENTITY_BOARD:
        e.draw()
    # whatever special effects an area needs
    for area in game_structures.AREA_QUEUE:
        area.draw()
    # draw hands
    for item in game_structures.HANDS:
        if item is None:
            continue
        if do_tick:
            item.tick(item)
        if draw_gui:
            item.draw(item)
    if draw_gui:
        # draw distance record
        game_structures.SCREEN.blit(
            game_structures.FONTS[128].render(
                str(game_states.RECORD_DISTANCE),
                False,
                (255, 255, 255)
            ),
            (0, 0)
        )
        # draw dash
        abilities.draw_dash_icon(ingame.tick_counter)
        # draw hearts
        for i in range(game_states.HEALTH):
            # compute jiggle
            # draw final
            if do_tick:
                heart_data[i].tick()
            game_structures.SCREEN.blit(
                heart_img,
                heart_data[i].generate_pos((game_states.WIDTH // 2 - (game_states.HEALTH / 2) * (
                            draw_constants.icon_size + 4) + i * (draw_constants.icon_size + 4), draw_constants.hearts_y - tutorials.display_height))
            )
    # draw player
    game_structures.SCREEN.blit(
        pygame.transform.flip(
            player_img,
            False,
            game_states.LAST_DIRECTION == -1
        ),
        (game_structures.to_screen_x(-32), game_structures.to_screen_y(game_states.DISTANCE + 32))
    )
    # camera movement
    if do_tick:
        camera_move = camera_move // 2
        if enforce_goal is not None:
            goal = enforce_goal
            total = 2
        elif total > 0:
            goal = game_states.DISTANCE + game_states.HEIGHT / 2 * (abs(mass) * mass / total ** 2)
        else:
            goal = game_states.DISTANCE + game_states.HEIGHT * game_states.LAST_DIRECTION
        goal -= game_states.HEIGHT // 2

        if tutorials.display is not None:
            goal -= 2 * tutorials.display.get_height()
            total *= 3

        camera_move += (min(total, 2) + 2) / 324 * (goal - game_states.CAMERA_BOTTOM)
        if enforce_goal is not None and camera_move < 1 and goal != game_states.CAMERA_BOTTOM:
            game_states.CAMERA_BOTTOM += goal - game_states.CAMERA_BOTTOM > 0
        game_states.CAMERA_BOTTOM += round(camera_move)

        if game_states.DISTANCE < game_states.CAMERA_BOTTOM + game_states.CAMERA_THRESHOLDS[0] + tutorials.display_height:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0] - tutorials.display_height
        if game_states.DISTANCE > game_states.CAMERA_BOTTOM + game_states.HEIGHT - game_states.CAMERA_THRESHOLDS[1]:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE + game_states.CAMERA_THRESHOLDS[1] - game_states.HEIGHT
    tutorials.tick(do_tick)
