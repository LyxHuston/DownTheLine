"""
describing all non-player entities
"""
import pygame

import game_states
import game_structures
import images
import random


def glide_player(speed: int, duration: int, taper: int, direction: int):
    game_states.GLIDE_SPEED = speed
    game_states.GLIDE_DURATION = duration
    game_states.TAPER_AMOUNT = taper
    game_states.GLIDE_DIRECTION = direction


class Entity(game_structures.Body):
    """
    base entity class that describes a few things most entities need to do
    """

    seen = False

    cost = 2

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
                game_structures.to_screen_x(self.x) - self.img.get_width() // 2,
                game_structures.to_screen_y(self.y) - self.img.get_height() // 2
            )
        )

    def hit(self, damage: int, item):
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

    @classmethod
    def make(cls, determiner: int, area):
        """
        makes an entity in the given area of the specific entity
        :param determiner:
        :param area:
        :return:
        """
        raise NotImplementedError(f"Attempted to use make method from generic Entity superclass: {cls.__name__} should implement it separately.")


class Glides(Entity):
    """
    an entity that has the glide action.  typically for knockback
    """

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.glide_speed = 0
        self.glide_direction = 0
        self.taper = 0
        self.glide_duration = 0

    def glide_tick(self) -> bool:
        """
        a single tick of gliding motion
        :return:
        """
        if self.glide_speed <= 0:
            return False
        if self.glide_duration == 0:
            self.glide_speed -= self.taper
            if self.glide_speed < 0:
                self.glide_speed = 0
        else:
            self.glide_duration -= 1
        self.y += self.glide_speed * self.glide_direction
        return True

    def start_glide(self, speed: int, duration: int, taper: int, direction: int):
        self.glide_speed = speed
        self.glide_duration = duration
        self.taper = taper
        self.glide_direction = direction


class Obstacle(Entity):
    """
    harmless obstacles on path.
    """

    cost = 0

    full = images.WALL_FULL
    half = images.WALL_HALF
    fragile = images.WALL_FRAGILE

    def __init__(self, rotation: int = 0, pos: tuple[int, int] = (0, 0)):
        super().__init__(self.full.img, rotation, pos)
        self.health = 10
        self.max_health = 10

    def hit(self, damage: int, item):
        self.health -= damage
        if self.health > self.max_health // 2:
            self.img = self.full.img
        elif self.health > 1:
            self.img = self.half.img
        else:
            self.img = self.fragile.img

    def tick(self):
        if abs(self.x) < 128 + 32 and abs(game_states.DISTANCE - self.y) < 56:
            game_states.DISTANCE = self.y + ((game_states.DISTANCE - self.y > 0) * 2 - 1) * 56
        rect = self.img.get_rect(center=self.pos)
        for entity in game_structures.all_entities():
            if entity is self:
                continue
            if not isinstance(entity, Entity):
                continue
            entity_rect = entity.rect
            if rect.colliderect(entity_rect):
                if abs(entity.y - self.y) < abs(entity.x - self.x) - 12:
                    entity.x = self.x + (32 + entity_rect.width // 2) * ((entity.x - self.x > 0) * 2 - 1)
                else:
                    entity.y = self.y + (24 + entity_rect.height // 2) * ((entity.y - self.y > 0) * 2 - 1)
                    pass
        return self.health > 0

    def first_seen(self):
        self.full.img
        self.half.img
        self.fragile.img
        self.hit(0, None)


class Slime(Glides):
    """
    slime.  Moves up or down the path.
    """

    cost = 1

    frame_change_frequency = 16
    imgs = [images.SLIME_1, images.SLIME_2, images.SLIME_3, images.SLIME_4]

    def __init__(self, pos: tuple[int, int] = (0, 0)):
        if isinstance(self.imgs[0], images.Image):
            self.imgs[0] = self.imgs[0].img
        super().__init__(self.imgs[0], 0, pos)
        self.frame = 0
        self.health = 7
        self.max_health = 7
        self.random = random.Random()

    def hit(self, damage: int, item):
        self.health -= damage
        self.start_glide(damage, 90, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)

    def tick(self):
        self.frame = (self.frame + 1) % (4 * self.frame_change_frequency)
        self.img = self.imgs[self.frame // self.frame_change_frequency]
        self.glide_tick()
        if self.glide_duration == 0:
            self.start_glide(
                self.random.randint(1, 3) * 4,
                self.random.randint(4, 6) * 60,
                15,
                self.random.randint(-1, 1)
            )
            if abs(self.y - game_states.CAMERA_BOTTOM - game_states.HEIGHT // 2) > game_states.HEIGHT // 2 and self.glide_speed > 4:
                self.glide_speed = 4
        else:
            self.glide_duration -= 1
        # print(self.health, self.frame, self.pos, game_states.DISTANCE)
        if abs(self.x) < 32 and abs(self.y - game_states.DISTANCE) < 64:
            game_states.HEALTH -= 1
            game_states.DISTANCE = self.y + 64 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            glide_player(5, 1, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            game_structures.begin_shake(6, (10, 10), (7, 5))
            self.start_glide(0, 30, 0, 0)
        return self.health > 0

    def first_seen(self):
        for i in range(1, 4):
            self.__class__.imgs[i] = self.__class__.imgs[i].img

    @classmethod
    def make(cls, determiner: int, area):
        return cls((0, area.random.randint(area.length // 3, area.length)))