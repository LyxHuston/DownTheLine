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

describing all non-player entities.  Items and ability drops are not considered
entities
"""
import pygame

import game_states
import game_structures
import images
import random
from collections import deque


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
        if not type(self).seen:
            type(self).seen = True
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

    def transfer(self, area):
        """
        called when transferring an entity to a new area, in case the entity needs to do something there
        :param area:
        :return:
        """


class ItemEntity(Entity):
    """
    wrapper entity for items and abilities while on the ground to make them easier to work with
    """

    @property
    def pos(self):
        return self.item.pos

    @pos.setter
    def pos(self, val: tuple[int, int]):
        self.item.pos = (
            self.item.pos[0] if self.freeze_x() else val[0],
            self.item.pos[1] if self.freeze_y() else val[1]
        )

    @property
    def x(self):
        return self.item.pos[0]

    @x.setter
    def x(self, val: int):
        self.pos = (val, self.pos[1])

    @property
    def y(self):
        return self.item.pos[1]

    @y.setter
    def y(self, val: int):
        self.pos = (self.pos[0], val)

    @property
    def rotation(self):
        return self.__rotation

    @rotation.setter
    def rotation(self, val: int):
        self.__rotation = val
        self._rotated_img = None

    @property
    def img(self):
        if self._rotated_img is None and self.item.img is not None:
            self._rotated_img = pygame.transform.rotate(self.item.img, self.__rotation)
        return self._rotated_img

    @img.setter
    def img(self, val: pygame.Surface):
        self.item.img = val
        self._rotated_img = None

    def __init__(self, item):
        self.item = item
        super().__init__(item.img, 0, item.pos)

    def tick(self) -> bool:
        return self.item.tick(self.item)

    def draw(self):
        self.item.draw(self.item)


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
            if isinstance(entity, ItemEntity):
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
        if self.glide_speed == 0:
            self.start_glide(
                self.random.randint(1, 3) * 4,
                self.random.randint(4, 6) * 60,
                15,
                self.random.randint(-1, 1)
            )
            if abs(self.y - game_states.CAMERA_BOTTOM - game_states.HEIGHT // 2) > game_states.HEIGHT // 2 and self.glide_speed > 4:
                self.glide_speed = 4
        # print(self.health, self.frame, self.pos, game_states.DISTANCE)
        if abs(self.x) < 32 and abs(self.y - game_states.DISTANCE) < 32:
            game_states.HEALTH -= 1
            game_states.DISTANCE = self.y + 32 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            glide_player(5, 1, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            game_structures.begin_shake(6, (10, 10), (7, 5))
            self.start_glide(0, 30, 0, 0)
        return self.health > 0

    def first_seen(self):
        for i in range(1, 4):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img

    @classmethod
    def make(cls, determiner: int, area):
        new_slime = cls((0, area.random.randint(area.length // 3, area.length)))
        new_slime.random.seed(determiner)
        return new_slime


class Crawler(Glides):
    """
    crawls towards the player.  Slow, sometimes, but always a threat.
    """

    frame_change_frequency = 2

    cost = 3

    imgs = []

    def __init__(self, pos: tuple[int, int], speed: int, area):
        super().__init__(images.CRAWLER_1.img, 0, pos)
        self.speed = speed * 2
        self.switch_ticks = max(9 // speed, 1)
        self.frame = 0
        self.threshhold = area.start_coordinate
        self.health = 10
        self.max_health = 10

    def hit(self, damage: int, item):
        self.health -= damage
        self.start_glide(damage, 90, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)

    def tick(self) -> bool:
        # print(self.y, self.health)
        self.glide_tick()
        if (self.glide_speed == 0 or (
                self.taper == 0 and self.glide_direction != (self.y < game_states.DISTANCE) * 2 - 1)) and game_states.DISTANCE > self.threshhold:
            if self.threshhold != 0:
                self.threshhold = 0
            self.start_glide(
                self.speed,
                0,
                0,
                (self.y < game_states.DISTANCE) * 2 - 1
            )
        if self.glide_speed > 0 and self.taper == 0:
            self.frame = (self.frame + self.glide_direction) % (8 * self.frame_change_frequency * self.switch_ticks)
            self.img = self.imgs[self.frame // (self.frame_change_frequency * self.switch_ticks)]
        if abs(self.x) < 28 and abs(self.y - game_states.DISTANCE) < 34:
            game_states.HEALTH -= 1
            game_states.DISTANCE = self.y + 34 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            glide_player(round(self.speed * 1.5), 3, 10, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            game_structures.begin_shake(6, (10, 10), (7, 5))
        return self.health > 0

    def first_seen(self):
        self.__class__.imgs = [
            images.CRAWLER_1.img,
            images.CRAWLER_2.img,
            images.CRAWLER_3.img,
            pygame.transform.flip(images.CRAWLER_2.img, False, True),
            pygame.transform.flip(images.CRAWLER_1.img, False, True),
            pygame.transform.flip(images.CRAWLER_2.img, True, False),
            images.CRAWLER_3.img,
            pygame.transform.flip(images.CRAWLER_2.img, True, True)
        ]

    @classmethod
    def make(cls, determiner: int, area):
        return cls((0, area.random.randint(area.length // 3, area.length)), area.random.randint(1, min(area.difficulty // 4, 5)), area)


class Spawner(Entity):
    """
    superclass for any entity that spawns others.  Also probably its own entity?
    """

    frame_change_frequency = 3

    imgs = [images.SPAWNER_1, images.SPAWNER_2, images.SPAWNER_3, images.SPAWNER_4]

    allowable = ((Slime, 0), (Crawler, 8))

    def __init__(self, pos: tuple[int, int], limit: int | None, area, delay: int, entity: Entity, deposit: tuple[int | None, int | None], speed: int):
        super().__init__(self.imgs[0], 0, pos)
        self.area = area
        self.limit = limit
        self.__check: int = 0
        if limit is None:
            self.__list = None
        else:
            self.__list: list = [None for i in range(limit)]
        self.delay = delay
        self.timer = -1
        self.__entity = entity
        self.__spawning: Entity | None = None
        self.__destination = deposit
        self.__speed = speed
        self.switch_ticks = max(speed, 1)
        self.frame = 0

    def management_tick(self):
        if self.__spawning is not None:
            if abs(self.__spawning.x - self.__destination[0]) < self.__speed //\
                    2 and abs(self.__spawning.y - self.__destination[1]) < self.__speed // 2:
                self.__spawning.pos = self.__destination
                self.area.entity_list.append(self.__spawning)
                if self.__list is not None:
                    self.__list[self.__check] = self.__spawning
                self.__spawning = None
                return
            if self.__destination[0] is None:
                x_dist = 0
            else:
                x_dist = abs(self.__spawning.x - self.__destination[0])
            if self.__destination[1] is None:
                y_dist = 0
            else:
                y_dist = abs(self.__spawning.y - self.__destination[1])
            dist = x_dist + y_dist
            self.__spawning.x += self.__speed * round(x_dist / dist)
            self.__spawning.y += self.__speed * round(y_dist / dist)
        if self.timer == -1:
            if self.__list is None:
                self.timer = 0
                return
            self.__check = (self.__check + 1) % len(self.__list)
            if self.__list[self.__check] is None:
                self.timer = 0
            return
        if self.timer == self.delay:
            self.timer = -1
            self.__spawning = self.__entity.make(self.area.random.randint(0, 2**16 - 1), self.area)

            if self.__list is not None:
                index = self.__check

                def special_callback():
                    res = self.__spawning.tick()
                    if not res:
                        self.__list[index] = None
                    return res

                self.__spawning.tick = special_callback

            self.__spawning.pos = self.pos
            return
        self.timer += 1

    def tick(self):
        self.management_tick()
        self.frame = (self.frame + 1) % (4 * self.frame_change_frequency * self.switch_ticks)
        self.img = self.imgs[self.frame // (self.frame_change_frequency * self.switch_ticks)]
        return True

    def transfer(self, area):
        if self.__list is None:
            return
        for i in range(len(self.__list)):
            if self.__list[i] is None:
                continue
            if self.__list[i].y > self.area.end_coordinate:
                self.__list[i] = None

    @classmethod
    def make(cls, determiner: int, area):
        if area.random.randint(0, area.difficulty) > 20 + area.difficulty // 2:
            limit = None
            delay = area.random.randint(12, 17) * 100
        else:
            limit = area.random.randint(3, area.difficulty // 5)
            delay = area.random.randint(5, 8) * 20
        y = area.random.randint(area.length // 3, area.length)
        index = 0
        while index < len(cls.allowable) - 1:
            if area.difficulty < cls.allowable[index][1]:
                index -= 1
                break
            if area.random.randint(0, 1):
                break
        return cls((0, y), limit, area, delay, cls.allowable[index][0],
                   (0, None), area.difficulty // 10 + (area.difficulty % 10 == 0))

    def first_seen(self):
        for i in range(1, 4):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img


if __name__ == "__main__":
    import game_areas

    Crawler.first_seen(Crawler((0, 0), 1, game_areas.GameArea()))
    frame = 0
    direction = -1
    screen = pygame.display.set_mode((100, 100))
    clock = pygame.time.Clock()
    pygame.display.init()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                running = False
                break
        clock.tick(1)
        screen.fill((0, 0, 0))
        screen.blit(
            Crawler.imgs[frame],
            (0, 0)
        )
        pygame.display.flip()
        frame = (frame + direction) % 8