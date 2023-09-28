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

import game_structures
import game_states
from utility import make_async
import entities
import items
import images
import math


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
        if seed is None:
            self.random = random.Random()
        else:
            self.random = random.Random(seed)

    seen = False

    def enter(self):
        if not self.__class__.seen:
            self.__class__.seen = True
            self.start_tutorial()
        for entity in self.entity_list:
            if isinstance(entity, entities.Entity):
                entity.enter()

    def start_tutorial(self):
        pass

    def draw(self):
        for entity in self.entity_list:
            entity.draw()

    def tick(self):
        i = 0
        while i < len(self.entity_list):
            entity = self.entity_list[i]
            if isinstance(entity, items.Item):
                res = entity.tick(entity)
            else:
                res = entity.tick()
            if res:
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
        for entity in self.entity_list:
            entity.pos = (entity.pos[0], entity.pos[1] + self.start_coordinate)


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    allowable_thresh_holds = [(entities.Slime, 0), (entities.Crawler, 5)]
    # allowable_thresh_holds = [(entities.Crawler, 0)]

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
                allowance -= (spawner.delay // 200 + 1) * (spawner.entity.cost + 1)
            else:
                allowance -= (spawner.limit + 1) * spawner.entity.cost
        self.entity_list.append(entities.Obstacle(pos=(0, self.length)))


@make_async(with_lock=True)
def add_game_area():
    # print(game_states.LAST_AREA)
    match game_states.LAST_AREA:
        case 0:
            area = GameArea(200)
            area.entity_list.append(entities.Obstacle(pos=(0, 170)))
            area.entity_list.append(entities.ItemEntity(items.simple_stab(
                60,
                20,
                images.SIMPLE_SWORD.img,
                (0, 40)
            )))
        case 1:
            area = GameArea(300)
            area.entity_list.append(entities.Obstacle(pos=(0, area.length), health=5))
            area.entity_list.append(entities.Slime((0, area.length // 2)))
        case 2:
            area = GameArea(500)
            area.entity_list.append(entities.Obstacle(pos=(0, + area.length), health=5))
            area.entity_list.append(entities.Slime((0, area.length // 3)))
            area.entity_list.append(entities.Slime((0, 2 * area.length // 2)))
            area.entity_list.append(entities.ItemEntity(items.simple_stab(
                120,
                10,
                images.SIMPLE_SPEAR.img,
                (15, 120),
                2
            )))
            game_states.AREA_QUEUE_MAX_LENGTH = 3
        case _:
            determinator = hash(str(game_states.SEED + game_states.LAST_AREA))
            # print(determinator, game_states.SEED + game_states.LAST_AREA)
            area = None
            typ = determinator % 64
            if typ < 2 and game_states.LAST_AREA < 40:
                typ = 2
            if typ < 4 and game_states.LAST_AREA < 20:
                typ = 4
            if typ < 13 and game_states.LAST_AREA < 10:
                typ = 13
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
                # enslaught room
                pass
            elif typ <= 18:  # 6/64
                # gift room
                pass
            elif typ <= 32:  # 14/64
                area = BreakThroughArea(determinator, game_states.LAST_AREA)
                pass
            else:  # 32/64
                area = BasicArea(determinator, game_states.LAST_AREA)
                pass
            if area is None:
                area = GameArea(400)
    game_states.LAST_AREA += 1
    area.finalize()
    game_states.LAST_AREA_END = area.end_coordinate
    # print(game_states.LAST_AREA_END)
    game_structures.AREA_QUEUE.append(area)
