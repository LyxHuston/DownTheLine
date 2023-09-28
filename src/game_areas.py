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

handles making and managing game areas
"""
import random

import pygame

import game_structures
import game_states
from utility import make_async
import entities
import items
import images
import math
from collections import deque



class GameArea:
    """
    an area with entities to interact with.  Must always be initialized offscreen

    this superclass should only be directly initialized for a tutorial instance
    """

    @property
    def end_coordinate(self):
        return self.start_coordinate + self.length

    def __init__(self, length: int = 0, seed: int = None):
        self.start_coordinate = max(game_states.RECORD_DISTANCE + game_states.HEIGHT, game_states.LAST_AREA_END)
        self.length = length
        self.initialized = False
        self.entity_list = []
        self.particle_args: tuple[list[images.Image] | list[pygame.Surface], int, int] = (
            images.VOID_PARTICLES, 30, 120
        )
        self.particle_list = set()
        if seed is None:
            self.random = random.Random()
        else:
            self.random = random.Random(seed)
        self.spawn_end = 0  # track which end to spawn a particle on

    seen = False

    def enter(self):
        if not self.__class__.seen:
            self.__class__.seen = True
            self.start_tutorial()
        for entity in self.entity_list:
            entity.enter()

    def start_tutorial(self):
        pass

    def draw(self):
        remove_list = deque()
        for particle in self.particle_list:
            if particle.tick():
                particle.draw()
            else:
                remove_list.append(particle)
        for particle in remove_list:
            self.particle_list.remove(particle)
        for entity in self.entity_list:
            entity.draw()

    region_length = 32000
    taper_length = 100

    def tick(self):
        region = 0
        while region * self.region_length + self.taper_length < self.length:  # spawn particles for middle regions
            height = self.start_coordinate + self.random.randint(0, self.region_length - 1) + region * self.region_length
            if height > self.end_coordinate - self.taper_length // 2:
                break
            self.particle_list.add(entities.Particle(
                *self.particle_args,
                (
                    self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                    height
                )
            ))
            region += 1
        self.spawn_end = not self.spawn_end
        if self.random.randint(0, self.region_length // self.taper_length) == 0:
            self.particle_list.add(entities.Particle(
                *self.particle_args,
                (
                    self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                    self.start_coordinate + self.length // 2 + (self.spawn_end * 2 - 1) * (
                            self.length +
                            self.taper_length - (math.sqrt(1 + 8 * self.random.randint(0, (self.taper_length + 1) * self.taper_length // 2) - 1) - 1)
                    ) // 2
                )
            ))
        # print(len(self.particle_list))
        i = 0
        while i < len(self.entity_list):
            if self.entity_list[i].tick():
                i += 1
            else:
                del self.entity_list[i]

    def finalize(self):
        """
        called at the end of an intialization.  Ensures that the start
        coordinate is offscreen and moves everything to correct position

        DON'T CALL THIS IN __INIT__!!!  Called during add_area().
        :return:
        """
        if self.start_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT + 100 or self.start_coordinate < game_states.LAST_AREA_END:
            self.start_coordinate = max(game_states.CAMERA_BOTTOM + game_states.HEIGHT + 100, game_states.LAST_AREA_END)
        game_states.LAST_AREA_END = self.end_coordinate
        for entity in self.entity_list:
            entity.y += self.start_coordinate


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    allowable_thresh_holds = [(entities.Slime, 0), (entities.Crawler, 5), (entities.Fencer, 10), (entities.Archer, 10), (entities.Knight, 15)]
    # allowable_thresh_holds = [(entities.Knight, 0)]

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.length = 200 + math.floor(math.log2(count)) * 100
        self.difficulty = count
        allowance = count
        allowable_entities = []
        for entry in self.allowable_thresh_holds:
            if entry[1] > count:
                break
            allowable_entities.append([entry[0], 0])
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            num += 1
            entity = allowable_entities[index][0]
            if entity.seen:
                allowance -= entity.cost + allowable_entities[index][1]
                allowable_entities[index][1] += 1
                self.entity_list.append(entity.make(determiner, self))
            else:
                self.entity_list.clear()
                self.length = 1000
                add = entity.make(determiner, self)
                add.y = self.length // 2
                self.entity_list.append(add)
                self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=5))
                break


class BreakThroughArea(GameArea):
    """
    area that continually spawns monsters, objective to break through them and
    destroy the wall at the end
    """

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.length = game_states.HEIGHT // 2 + math.floor(math.log2(count)) * 100
        allowance = count
        while allowance > 0:
            spawner = entities.Spawner.make(determiner, self)
            self.entity_list.append(spawner)
            if spawner.limit is None:
                allowance -= 2 * (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
            else:
                allowance -= 2 * (spawner.limit + 1) * spawner.entity.cost ** 2
        allowance = count // 3
        allowable_entities = []
        for entry in BasicArea.allowable_thresh_holds:
            if entry[1] > count or not entry[0].seen:
                break
            allowable_entities.append([entry[0], 0])
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            num += 1
            entity = allowable_entities[index][0]
            allowance -= entity.cost + allowable_entities[index][1] ** 2
            allowable_entities[index][1] += 1
            self.entity_list.append(entity.make(determiner, self))
        self.entity_list.append(entities.Obstacle(pos=(0, self.length)))


class GiftArea(GameArea):
    """
    gives player a new item and area to practice it with.
    """

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.length = 1000
        spawn = entities.Spawner.make(determiner, self)
        experiment_area = 500
        spawn.y += experiment_area
        self.length += experiment_area
        self.entity_list.append(spawn)
        self.entity_list.append(entities.Obstacle(pos=(0, experiment_area), health=1))
        self.entity_list.append(entities.Obstacle(pos=(0, 1000 + experiment_area), health=10))
        self.entity_list.append(entities.ItemEntity(items.make_random_reusable(self.random, (0, experiment_area // 2))))


class EnslaughtArea(GameArea):
    """
    game area that is just surviving a bunch of enemies
    """

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.current_difficulty = count
        self.length = game_states.HEIGHT * 4
        self.entity_list.append(entities.InvulnerableObstacle(pos=(0, self.length), health=1))
        self.state = 0  # 0: not started 1: in progress 2: finished, killing off entities
        self.timer = 30 * 60 + 120 * math.floor(math.log2(count))
        self.max = self.timer
        self.cooldown_ticks = 0

    def draw(self):
        super(EnslaughtArea, self).draw()
        if self.state == 1:
            width = 3 * game_states.WIDTH // 4 * self.timer / self.max
            pygame.draw.line(
                game_structures.SCREEN,
                (255, 255, 255),
                (game_states.WIDTH // 2 - width // 2, 20),
                (game_states.WIDTH // 2 + width // 2, 20),
                20
            )

    cooldown = 300

    def tick(self):
        super(EnslaughtArea, self).tick()
        match self.state:
            case 0:
                if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                    self.state = 1
                    end_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate))
                    end_wall.enter()
                    self.entity_list.append(end_wall)
                    self.cooldown_ticks = self.cooldown
            case 1:
                self.timer -= 1
                if self.cooldown_ticks <= 0:
                    self.cooldown_ticks = self.cooldown
                    self.event()
                self.cooldown_ticks -= 1
                if self.timer <= 0:
                    self.state = 2
                    self.cooldown_ticks = 0
                    del self.entity_list[0]
            case 2:
                if self.cooldown_ticks <= 0:
                    self.cooldown_ticks = 30
                    for entity in self.entity_list:
                        entity.health -= 1
                self.cooldown_ticks -= 1

    def event(self):
        target_change = (self.difficulty - self.current_difficulty) // 2 + 8 * self.random.randint(-1, 3)
        if target_change < 0:
            print("Item duplicator")
            pos = (
                self.random.randint(100, game_states.WIDTH // 2) * (self.random.randint(0, 1) * 2 - 1),
                self.random.randint(self.start_coordinate + 100, self.end_coordinate - 100)
            )
            self.entity_list.append(entities.Spawner(
                pos,
                1,
                self,
                0,
                entities.make_item_duplicator(items.make_random_single_use(self.random, pos)),
                (0, None),
                1
            ))
            self.current_difficulty -= 20
        elif target_change < 10:
            print("Lazers")
            for i in range(target_change):
                self.entity_list.append(entities.DelayedDeploy(
                    i * 60,
                    self,
                    entities.TrackingLazer,
                    (
                        self.end_coordinate,
                        60,
                        60,
                        self
                    )
                ))
        elif target_change < 15:
            print("Fishies")
            for i in range(target_change // 3):
                self.entity_list.append(entities.Fish(self))
                self.current_difficulty += 2
        elif target_change < 30:
            # print("Spawning")
            allowable_entities = []
            for entry in BasicArea.allowable_thresh_holds:
                if entry[1] > self.difficulty or not entry[0].seen:
                    break
                allowable_entities.append([entry[0], 0])
            num = 3
            determiner = self.random.randint(0, 2 ** 31)
            while target_change > 0:
                index = (determiner % num) % len(allowable_entities)
                num += 1
                entity = allowable_entities[index][0]
                target_change -= entity.cost + allowable_entities[index][1] ** 2
                self.current_difficulty += entity.cost + allowable_entities[index][1] ** 2
                allowable_entities[index][1] += 1
                made_entity = entity.make(determiner, self)
                made_entity.y += self.start_coordinate
                if game_states.CAMERA_BOTTOM + made_entity.height < made_entity.y < game_states.CAMERA_BOTTOM + game_states.HEIGHT - made_entity.height:
                    if game_states.DISTANCE - self.start_coordinate < self.length // 2:
                        made_entity.y = self.end_coordinate - 100
                    else:
                        made_entity.y = self.start_coordinate + 100
                self.entity_list.append(made_entity)
                print(made_entity)
        else:
            print("Spawners")
            for i in range(target_change // 15):
                spawner = entities.Spawner.make(self.random.randint(0, 2 ** 31), self)
                if spawner.limit is None:
                    self.current_difficulty += (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
                else:
                    self.current_difficulty += (spawner.limit + 1) * spawner.entity.cost ** 2
                spawner.y += self.start_coordinate
                self.entity_list.append(spawner)
        print(f"{self.current_difficulty}/{self.difficulty}")


@make_async(with_lock=True)
def add_game_area():
    # print(game_states.LAST_AREA)
    determinator = hash(str(game_states.SEED + game_states.LAST_AREA))
    match game_states.LAST_AREA:
        case 0:
            area = GameArea(200, determinator)
            area.entity_list.append(entities.Obstacle(pos=(0, 170)))
            area.entity_list.append(entities.ItemEntity(items.simple_stab(
                60,
                20,
                images.SIMPLE_SWORD.img,
                (0, 40)
            )))
        case 1:
            area = GameArea(300, determinator)
            area.entity_list.append(entities.Obstacle(pos=(0, area.length), health=5))
            area.entity_list.append(entities.Slime((0, area.length // 2), area.random.randint(0, 2 ** 32 - 1)))
        case 2:
            area = GameArea(500, determinator)
            area.entity_list.append(entities.Obstacle(pos=(0, + area.length), health=5))
            area.entity_list.append(entities.Slime((0, area.length // 3), area.random.randint(0, 2 ** 32 - 1)))
            area.entity_list.append(entities.Slime((0, 2 * area.length // 2), area.random.randint(0, 2 ** 32 - 1)))
            area.entity_list.append(entities.ItemEntity(items.simple_stab(
                120,
                10,
                images.SIMPLE_SPEAR.img,
                (15, 120),
                2
            )))
            game_states.AREA_QUEUE_MAX_LENGTH = 3
        case _:
            # print(determinator, game_states.SEED + game_states.LAST_AREA)
            area = None
            typ = determinator % 64
            if typ < 2 and game_states.LAST_AREA < 40:
                typ = 2
            if typ < 4 and game_states.LAST_AREA < 20:
                typ = 4
            if typ < 13 and game_states.LAST_AREA < 10:
                typ = 13
            if typ < 33 and game_states.LAST_AREA < 4:
                typ = 33
            if typ == 0:  # 1/64
                # GOD room
                pass
            elif typ <= 1:  # 1/64
                # player room
                pass
            elif typ <= 3:  # 3/64
                # boss room
                pass
            elif typ <= 6:  # 3/64
                # minigame room
                pass
            elif typ <= 12:  # 6/64
                area = EnslaughtArea(determinator, game_states.LAST_AREA)
            elif typ <= 18:  # 6/64
                area = GiftArea(determinator, game_states.LAST_AREA)
            elif typ <= 32:  # 14/64
                area = BreakThroughArea(determinator, game_states.LAST_AREA)
            else:  # 32/64
                area = BasicArea(determinator, game_states.LAST_AREA)
            if area is None:
                area = GameArea(400)
    game_states.LAST_AREA += 1
    area.finalize()
    # print(game_states.LAST_AREA_END)
    game_structures.AREA_QUEUE.append(area)
    game_structures.make_save()