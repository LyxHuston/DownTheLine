"""
describing all non-player entities
"""


import game_structures


class Entity:
    """
    base entity class that describes a few things most entities need to do
    """

    seen = False

    def __init__(self):
        if not self.__class__.seen:
            self.__class__.seen = True
            self.first_seen()
        self.health = 0
        self.max_health = 0
        self.img = None
        self.pos = (0, 0)

    def first_seen(self):
        """
        function to run when an entity is first encountered.  Usually triggers a
        tutorial
        :return:
        """
        pass

    def draw(self):
        """
        draw img to screen, in the simplest of cases.  Base entity has no img!
        :return:
        """
        if self.img is None:
            return
        self.img.blit(
            game_structures.SCREEN,
            self.pos
        )

    def tick(self) -> bool:
        """
        runs a tick of the entity
        :return: if the entity should still exist.  False to delete the entity.
        NOTE: if there's a death animation or something, do not delete until
        after death
        """

    def enter(self):
        """
        called when an area initializes.  In most cases, starts
        :return:
        """