"""
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

    def __init__(self, length: int = 0):
        self.start_coordinate = max(game_states.RECORD_DISTANCE + game_states.HEIGHT, game_states.LAST_AREA_END)
        self.length = length
        self.initialized = False
        self.entity_list = []
        self.random = random.Random()

    seen = False

    def enter(self):
        if not self.__class__.seen:
            print("first seen")
            self.__class__.seen = True
            self.start_tutorial()
        for entity in self.entity_list:
            if isinstance(entity, entities.Entity):
                entity.enter()

    def start_tutorial(self):
        pass

    def draw(self):
        for entity in self.entity_list:
            if isinstance(entity, entities.Entity):
                entity.draw()
            else:
                entity.draw(entity)

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


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    def __init__(self, determiner, count):
        print("Basic area")
        super().__init__()
        self.length = 200 + math.floor(math.log2(count)) * 100
        allowance = count
        allowable_entities = [[entities.Slime, 0]]
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            entity = allowable_entities[index][0]
            if entity.seen:
                allowance -= entity.cost + allowable_entities[index][1]
                allowable_entities[index][1] += 1
                self.entity_list.append(entity.make(determiner, self))
            else:
                self.entity_list.clear()
                self.length = 200
                add = entity.make(determiner, self)
                add.y = self.start_coordinate + self.length // 2
                self.entity_list.append(add)
                self.entity_list.append(entities.Obstacle(pos=(0, self.end_coordinate)))
                break


@make_async(with_lock=True)
def add_game_area():
    match game_states.LAST_AREA:
        case 0:
            area = GameArea(200)
            area.entity_list.append(entities.Obstacle(pos=(0, area.start_coordinate + 170)))
            area.entity_list.append(items.simple_stab(
                60,
                20,
                images.SIMPLE_SWORD.img,
                (0, area.start_coordinate + 40)
            ))
        case 1:
            area = GameArea(300)
            area.entity_list.append(entities.Obstacle(pos=(0, area.end_coordinate)))
            area.entity_list.append(entities.Slime((0, area.start_coordinate + area.length // 2)))
        case 2:
            area = GameArea(500)
            area.entity_list.append(entities.Obstacle(pos=(0, area.start_coordinate + area.length)))
            area.entity_list.append(entities.Slime((0, area.start_coordinate + area.length // 3)))
            area.entity_list.append(entities.Slime((0, area.start_coordinate + 2 * area.length // 2)))
            area.entity_list.append(items.simple_stab(
                120,
                10,
                images.SIMPLE_SPEAR.img,
                (15, area.start_coordinate + 120),
                2
            ))
            game_states.AREA_QUEUE_MAX_LENGTH = 3
        case _:
            determinator = hash(str(game_states.SEED + game_states.LAST_AREA))
            print(determinator, game_states.SEED + game_states.LAST_AREA)
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
                # breakthrough
                pass
            else:  # 32/64
                area = BasicArea(determinator, game_states.LAST_AREA)
                pass
            if area is None:
                area = GameArea(400)
    game_states.LAST_AREA += 1
    game_states.LAST_AREA_END = area.end_coordinate
    game_structures.AREA_QUEUE.append(area)
