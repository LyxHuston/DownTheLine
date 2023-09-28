"""
handles making and managing game areas
"""


from utility import make_async


class GameArea:
    """
    an area with entities to interact with.  Must always be initialized offscreen
    """

    @property
    def end_coordinate(self):
        return self.start_coordinate + self.length

    def __init__(self):
        self.start_coordinate = None
        self.length = None
        self.entity_list = []

    seen = False

    def enter(self):
        if not self.__class__.seen:
            self.start_tutorial()

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
    pass