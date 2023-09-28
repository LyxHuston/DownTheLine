"""
describing all non-player entities
"""
import pygame

import game_states
import game_structures
import images


class Entity(game_structures.Body):
    """
    base entity class that describes a few things most entities need to do
    """

    seen = False

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.health = 0
        self.max_health = 0

    def first_seen(self):
        """
        function to run when an entity is first encountered.  Usually triggers a
        tutorial, and gets imgs
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
        game_structures.SCREEN.blit(
            self.img,
            (
                self.pos[0] + game_states.WIDTH // 2 - self.img.get_width() // 2,
                game_states.HEIGHT + game_states.CAMERA_BOTTOM - self.pos[1] - self.img.get_height() // 2
            )
        )

    def hit(self, damage: int):
        """
        run when the entity takes damage
        :return:
        """
        self.health -= damage

    def tick(self) -> bool:
        """
        runs a tick of the entity
        :return: if the entity should still exist.  False to delete the entity.
        NOTE: if there's a death animation or something, do not delete until
        after death
        """
        return self.health > 0

    def enter(self):
        """
        called when an area initializes.  In most cases, starts AI/movement
        :return:
        """
        if not self.__class__.seen:
            self.__class__.seen = True
            self.first_seen()


class Obstacle(Entity):
    """
    harmless obstacles on path.
    """

    full = images.WALL_FULL
    half = images.WALL_HALF
    fragile = images.WALL_FRAGILE

    def __init__(self, rotation: int = 0, pos: tuple[int, int] = (0, 0)):
        super().__init__(self.full.img, rotation, pos)
        self.health = 10
        self.max_health = 10

    def hit(self, damage: int):
        self.health -= damage
        if self.health > self.max_health // 2:
            self.img = self.full.img
        elif self.health > 1:
            self.img = self.half.img
        else:
            self.img = self.fragile.img

    def tick(self):
        if abs(self.pos[0]) < 128 + 32 and abs(game_states.DISTANCE - self.pos[1]) < 56:
            game_states.DISTANCE = self.pos[1] + ((game_states.DISTANCE - self.pos[1] > 0) * 2 - 1) * 56

        return self.health > 0

    def first_seen(self):
        self.full.img
        self.half.img
        self.fragile.img
        self.hit(0)