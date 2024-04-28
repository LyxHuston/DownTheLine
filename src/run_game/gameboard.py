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
from collections import deque
from run_game.game_areas import add_game_area
import pygame
from run_game import abilities, game_areas, ingame, tutorials, entities
from data import draw_constants, game_states, switches
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


camera_move: int = 0
steepness: int = 10
liminal_mass_factor: float = 1 / (2 * (1 / (math.exp(steepness * -0.5) + 1) - 0.5))
max_tolerance: int = 2

ENTITY_BOARD: list[entities.Entity] = []
NEW_ENTITIES: list[entities.Entity] = []

PARTICLE_BOARD: set[entities.Particle] = set()


def particle_set_tick(particle_set: set[entities.Particle]):
    remove_list = deque()
    for particle in particle_set:
        if not particle.tick():
            remove_list.append(particle)
    for particle in remove_list:
        particle_set.remove(particle)
        particle.reset_id_check()


def filter_entities(lst: list[entities.Entity]) -> None:
    """
    filters an entity list in place
    :param lst: a list of entities
    :return: None
    """
    l: int = 0
    for u in range(len(lst)):
        if lst[u].alive:
            lst[l] = lst[u]
            l += 1
        else:
            lst[u].die()
    del lst[l:]


def tick(do_tick: bool = True, draw_gui: bool = True):
    """
    draws the gameboard and handles checking if we need to unload and load a new
    area.  If so, dispatches a thread.
    also, handles shaking the board
    :return:
    """
    global camera_move
    if do_tick:
        if game_structures.NEW_AREAS:
            if game_structures.NEW_AREAS[0].start_coordinate < game_states.CAMERA_BOTTOM + 2 * game_states.HEIGHT:
                area = game_structures.NEW_AREAS.popleft()
                area.initialized = True
                area.final_load()
                NEW_ENTITIES.extend(area.entity_list)
                area.entity_list = None  # so that it will be forced to error
                game_structures.AREA_QUEUE.append(area)
        if game_structures.AREA_QUEUE[0].end_coordinate < game_states.CAMERA_BOTTOM - game_states.HEIGHT:  # despawn
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
        [entity.final_load() for entity in NEW_ENTITIES]
        ENTITY_BOARD.extend(NEW_ENTITIES)
        NEW_ENTITIES.clear()
        ENTITY_BOARD.sort(key=lambda e: e.y)
        filter_entities(ENTITY_BOARD)
        entities.Entity.biggest_radius = max(ENTITY_BOARD, key=entities.Entity.radius).radius()
        area: game_areas.GameArea
        for area in game_structures.AREA_QUEUE:
            area.tick()
            if area.player_in():
                enforce_goal = area.enforce_center
        if enforce_goal is None:
            mass: float = 0
            total: float = 0
            for e in ENTITY_BOARD:
                # if isinstance(e, entities.AreaStopper):
                #     continue
                # if isinstance(e, entities.AreaStarter):
                #     continue
                e.tick()
                if not e.has_camera_mass:
                    continue
                dist: int = e.distance_to_player()
                if dist > game_states.HEIGHT:
                    continue
                direction: int = (game_states.DISTANCE < e.y) * 2 - 1
                k: float = max(3 - e.distance_to_view_edge() / game_states.CAMERA_THRESHOLDS[0], dist / 600, 1) - 1
                if k > 1:
                    mass += direction
                    total += 1
                elif k > 0:
                    diff: float = (1 / (math.exp(steepness * (0.5 - k)) + 1) - 0.5) * liminal_mass_factor + 0.5
                    mass += direction * diff
                    total += diff
        else:
            for e in ENTITY_BOARD:
                # if isinstance(e, entities.AreaStopper):
                #     continue
                # if isinstance(e, entities.AreaStarter):
                #     continue
                e.tick()
    # particles need to go on bottom
    for area in game_structures.AREA_QUEUE:
        area.draw_particles()
    # handle global particle board
    for particle in PARTICLE_BOARD:
        particle.draw()
    if do_tick:
        particle_set_tick(PARTICLE_BOARD)
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
                str(run_start_end.visual_distance()),
                False,
                (255, 255, 255)
            ),
            (0, (1 - switches.TUTORIAL_TEXT_POSITION) * tutorials.display_height)
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
                        draw_constants.icon_size + 4) + i * (draw_constants.icon_size + 4),
                        draw_constants.hearts_y - tutorials.display_height * switches.TUTORIAL_TEXT_POSITION)
                )
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
        camera_move //= 2
        if enforce_goal is not None:
            total = 2
            goal = enforce_goal
        elif total > 0:
            tolerance: float = min(total - abs(mass), max_tolerance)
            goal = game_states.DISTANCE + math.copysign(
                (1 - tolerance / max_tolerance) ** 2 * game_states.HEIGHT / 2,
                mass
            )
            # print(total, mass, goal, game_states.CAMERA_BOTTOM)
        else:
            goal = game_states.DISTANCE + game_states.HEIGHT * game_states.LAST_DIRECTION * 1.5

        # if tutorials.display is not None:
        #     goal -= 2 * tutorials.display.get_height()
        #     mass *= 3

        goal -= game_states.HEIGHT // 2
        camera_move += round(min(total, 2) / 90 * (goal - game_states.CAMERA_BOTTOM))

        if enforce_goal is None:
            pass
            # if abs(camera_move) < 5 and abs(mass) != total:
            #     camera_move = 0
        elif camera_move < 1 and goal != game_states.CAMERA_BOTTOM:
            game_states.CAMERA_BOTTOM += math.copysign(1, goal - game_states.CAMERA_BOTTOM)
        game_states.CAMERA_BOTTOM += camera_move
        # game_states.CAMERA_BOTTOM = goal

        # # move actual camera now
        # if abs(game_states.JITTER_PROTECTION_CAMERA - game_states.CAMERA_BOTTOM
        #        ) > game_states.JITTER_PROTECTION_DISTANCE:
        #     game_states.CAMERA_BOTTOM = game_states.JITTER_PROTECTION_CAMERA + math.copysign(
        #         game_states.JITTER_PROTECTION_DISTANCE,
        #         game_states.CAMERA_BOTTOM - game_states.JITTER_PROTECTION_CAMERA
        #     )
        # elif camera_move == 0 and game_states.JITTER_PROTECTION_CAMERA != game_states.CAMERA_BOTTOM:
        #     game_states.CAMERA_BOTTOM += math.copysign(
        #         1,
        #         game_states.JITTER_PROTECTION_CAMERA - game_states.CAMERA_BOTTOM
        #     )

        if game_states.DISTANCE < game_states.CAMERA_BOTTOM + game_states.CAMERA_THRESHOLDS[0] + tutorials.display_height * switches.TUTORIAL_TEXT_POSITION:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0] - tutorials.display_height * switches.TUTORIAL_TEXT_POSITION
        if game_states.DISTANCE > game_states.CAMERA_BOTTOM + game_states.HEIGHT - game_states.CAMERA_THRESHOLDS[1]:
            game_states.CAMERA_BOTTOM = game_states.DISTANCE + game_states.CAMERA_THRESHOLDS[1] - game_states.HEIGHT
    tutorials.tick(do_tick)
