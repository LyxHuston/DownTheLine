"""
handles making and managing game areas
"""

import game_structures
import game_states
from utility import make_async
import entities


class GameArea:
    """
    an area with entities to interact with.  Must always be initialized offscreen

    this superclass should only be directly initialized for a tutorial instance
    """

    @property
    def end_coordinate(self):
        return self.start_coordinate + self.length

    def __init__(self):
        self.start_coordinate = None
        self.length = None
        self.initialized = False
        self.entity_list = []

    seen = False

    def enter(self):
        if not self.__class__.seen:
            self.start_tutorial()
        for entity in self.entity_list:
            entity.enter()

    def start_tutorial(self):
        pass

    def draw(self):
        for entity in self.entity_list:
            entity.draw()

    def tick(self):
        i = 0
        while i < len(self.entity_list):
            if self.entity_list[i].tick():
                i += 1
            else:
                del self.entity_list[i]


@make_async(with_lock=True)
def add_game_area():
    match game_states.LAST_AREA:
        case 0:
            area = GameArea()
            area.start_coordinate = game_states.RECORD_DISTANCE + game_states.HEIGHT
            area.length = 100
            wall = entities.Obstacle()
            wall.pos = (0, area.start_coordinate + 50)
            area.entity_list.append(wall)
        case _:
            area = None
    game_states.LAST_AREA += 1
    game_structures.AREA_QUEUE.append(area)