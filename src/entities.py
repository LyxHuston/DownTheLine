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
import math
from typing import Type


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

    is_item_entity = False
    is_holder = False

    allied_with_player = False

    cost = 2

    @property
    def health(self):
        return self.__health

    @health.setter
    def health(self, val):
        if val < self.__health:
            self.flashing = 6 * (self.__health - val) + 2
            self.__shake_limit = 2 * (self.__health - val)
            self.__x_shake_momentum = (self.__health - val) ** 1.5 // 2
            self.__y_shake_momentum = 3 * (self.__health - val) ** 1.5 // 4
            # print(self.y, game_states.DISTANCE, self.tick, val, self.tick())
        elif val > self.max_health:
            val = self.max_health
        self.__health = val

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.__health = 0
        self.max_health = 0
        self.flashing = 0
        self.__x_shake_momentum = 0
        self.__x_shake = 0
        self.__y_shake_momentum = 0
        self.__y_shake = 0
        self.__shake_limit = 0

    def first_seen(self):
        """
        function to run when an entity is first encountered.  Usually triggers a
        tutorial, and gets imgs
        :return:
        """
        pass

    def draw(self):
        """
        draw img to screen, in the simplest of cases.  Base entity has no img!  Handles inverting colors for damage
        :return:
        """
        if self.img is None:
            return
        if self.flashing > 0:
            self.flashing -= 1
            self.__x_shake += self.__x_shake_momentum
            if abs(self.__x_shake) > self.__shake_limit:
                self.__x_shake += 2 * (abs(self.__x_shake) - self.__shake_limit) * ((self.__x_shake < 0) * 2 - 1)
                self.__x_shake_momentum *= -1
            self.__y_shake += self.__y_shake_momentum
            if abs(self.__y_shake) > self.__shake_limit:
                self.__y_shake += 2 * (abs(self.__y_shake) - self.__shake_limit) * ((self.__y_shake < 0) * 2 - 1)
                self.__y_shake_momentum *= -1
            img = pygame.Surface(self.img.get_rect().size, flags=pygame.SRCALPHA)
            img.blit(self.img, (0, 0))
            img.fill((255, 255, 255), special_flags=pygame.BLEND_ADD)
            img.blit(self.img, (0, 0), None, pygame.BLEND_RGB_SUB)
        else:
            self.__x_shake = self.__y_shake = self.__x_shake_momentum = self.__y_shake_momentum = 0
            img = self.img
        game_structures.SCREEN.blit(
            img,
            (
                game_structures.to_screen_x(self.x + self.__x_shake) - img.get_width() // 2,
                game_structures.to_screen_y(self.y + self.__y_shake) - img.get_height() // 2
            )
        )
        return self.pos

    def hit(self, damage: int, source):
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
        pass


EntityType = Type[Entity]


def make_invulnerable_version(entity_class: type(Entity)) -> type(Entity):
    """
    make invulnerable subclass of an entity class
    :param entity_class: an entity subclass
    :return:
    """

    class New(entity_class):
        """
        new class with frozen health
        """

        @property
        def health(self):
            """always return 1, setter just passes to avoid errors"""
            return 1

        @health.setter
        def health(self, val: int):
            pass

    return New


class ItemEntity(make_invulnerable_version(Entity)):
    """
    wrapper entity for items and abilities while on the ground to make them easier to work with
    """

    is_item_entity = True

    @property
    def pos(self):
        if isinstance(self.item.pos, int):
            return 0, 0
        if isinstance(self.item.pos[0], int):
            return self.item.pos
        return 0, 0

    @pos.setter
    def pos(self, val: tuple[int, int]):
        if isinstance(self.item.pos, int):
            return
        if not isinstance(self.item.pos[0], int):
            return
        self.item.pos = (
            self.item.pos[0] if self.freeze_x() else val[0],
            self.item.pos[1] if self.freeze_y() else val[1]
        )

    @property
    def x(self):
        return self.pos[0]

    @x.setter
    def x(self, val: int):
        self.pos = (val, self.pos[1])

    @property
    def y(self):
        return self.pos[1]

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
        self.picked_up = False
        super().__init__(item.img, 0, item.pos)

    def pick_up(self, hand):
        if self.picked_up:
            return None
        self.picked_up = True
        self.item.pos = hand
        return self.item

    def tick(self) -> bool:
        if self.picked_up:
            return False
        held = isinstance(self.item.pos, int)
        if not held:
            held = not isinstance(self.item.pos[0], int)
        if held:
            return False
        return self.item.tick(self.item)

    def draw(self):
        self.item.draw(self.item)


import items


def make_item_duplicator(item: items.Item):
    """
    creates a class that just duplicates the given items
    :param item:
    :return:
    """

    action, tick, img, pos, draw, icon, data_pack_factory, typ = items.deepcopy_datapack_factory(item)

    class ItemDuplicator(ItemEntity):

        @classmethod
        def make(cls, determiner: int, area):
            return cls(items.Item(
                action,
                tick,
                img,
                pos,
                draw,
                icon,
                data_pack_factory(),
                typ
            ))

    return ItemDuplicator


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

    def __init__(self, rotation: int = 0, pos: tuple[int, int] = (0, 0), health: int = 10):
        super().__init__(self.full.img, rotation, pos)
        self.max_health = health
        self.health = health

    def hit(self, damage: int, source):
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

    def enter(self):
        self.freeze_y(True)
        self.freeze_x(True)
        super().enter()

    def first_seen(self):
        self.full.img
        self.half.img
        self.fragile.img
        self.hit(0, None)


InvulnerableObstacle = make_invulnerable_version(Obstacle)


class Slime(Glides):
    """
    slime.  Moves up or down the path.
    """

    cost = 2

    frame_change_frequency = 16
    alert = images.SLIME_ALERT
    imgs = [images.SLIME_1, images.SLIME_2, images.SLIME_3, images.SLIME_4]

    def __init__(self, pos: tuple[int, int] = (0, 0), seed: int = 0):
        if isinstance(self.imgs[0], images.Image):
            self.imgs[0] = self.imgs[0].img
        super().__init__(self.imgs[0], 0, pos)
        self.frame = 0
        self.max_health = 7
        self.health = 7
        self.random = random.Random(seed)
        self.wait = 36

    def hit(self, damage: int, source):
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(damage, 90, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(damage, 90, 1, ((self.y - source.pos[1]) > 0) * 2 - 1)

    def tick(self):
        self.glide_tick()
        if self.glide_speed == 0:
            self.wait -= 1
            if self.wait // 12 == 1:
                self.img = self.imgs[self.frame // self.frame_change_frequency]
            else:
                self.img = self.alert
            if self.wait == 0:
                self.start_glide(
                    self.random.randint(1, 3) * 4,
                    self.random.randint(4, 6) * 60,
                    15,
                    self.random.randint(-1, 1)
                )
                if abs(self.y - game_states.CAMERA_BOTTOM - game_states.HEIGHT // 2) > game_states.HEIGHT // 2 and self.glide_speed > 4:
                    self.glide_speed = 4
                self.wait = 36
        else:
            self.glide_tick()
            self.frame = (self.frame + 1) % (4 * self.frame_change_frequency)
            self.img = self.imgs[self.frame // self.frame_change_frequency]
        # print(self.health, self.frame, self.pos, game_states.DISTANCE)
        # pygame.draw.circle(
        #     game_structures.SCREEN,
        #     (255, 255, 255),
        #     game_structures.to_screen_pos(self.pos),
        #     32,
        #     5
        # )
        # if self.draw() != self.pos:
        #     # print("Position discrepancy")
        if abs(self.x) < 32 and abs(self.y - game_states.DISTANCE) < 64:
            game_structures.deal_damage(1, self)
            game_states.DISTANCE = self.y + 64 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            glide_player(5, 2, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            game_structures.begin_shake(6, (10, 10), (7, 5))
            self.start_glide(5, 30, 5, (self.y > game_states.DISTANCE) * 2 - 1)
        return self.health > 0

    def first_seen(self):
        self.alert.img
        for i in range(1, 4):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img

    @classmethod
    def make(cls, determiner: int, area):
        new_slime = cls((0, area.random.randint(area.length // 3, area.length)))
        new_slime.random.seed(area.random.randint(0, 2 ** 32 - 1))
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
        self.max_health = 6
        self.health = 6

    def hit(self, damage: int, source):
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(damage, 90, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(damage, 90, 1, ((self.y - source.pos[0]) > 0) * 2 - 1)

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
        # pygame.draw.circle(
        #     game_structures.SCREEN,
        #     (255, 255, 255),
        #     game_structures.to_screen_pos(self.pos),
        #     32,
        #     5
        # )
        if abs(self.x) < 28 and abs(self.y - game_states.DISTANCE) < 66:
            game_structures.deal_damage(1, self)
            self.y -= self.glide_speed * self.glide_direction
            game_states.DISTANCE = self.y + 66 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
            glide_player(round(self.speed * 1.5), 5, 10, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
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


class Fencer(Glides):
    """
    the first entity with an actually semi-complicated movement script. (Spawner doesn't count)
    Tries to keep distance except for dashes.  Dashes quickly.
    """

    dashing = images.FENCER_DASHING
    imgs = [images.FENCER_1, images.FENCER_2, images.FENCER_3]
    frame_change_frequency = 5
    cost = 10

    def __init__(self, pos: tuple[int, int], difficulty: int):
        super().__init__(images.FENCER_1.img, 0, pos)
        self.max_health = 4
        self.health = 4
        self.cooldown = 0
        self.cooldown_length = max(180 - difficulty, 30)
        self.frame = 0

    def tick(self) -> bool:
        dist = abs(self.y - game_states.DISTANCE)
        self.rotation = 180 * (self.y < game_states.DISTANCE)
        if self.glide_speed > 0:
            self.glide_tick()
            if abs(self.x) < 40 and abs(self.y - game_states.DISTANCE) < 56:
                game_structures.deal_damage(2, self)
                game_states.DISTANCE = self.y + 56 * ((self.y < game_states.DISTANCE) * 2 - 1)
                self.start_glide(25, 10, 15, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
                glide_player(1, 20, 10, (self.y < game_states.DISTANCE) * 2 - 1)
                game_structures.begin_shake(10, (20, 20), (13, -9))
            if self.cooldown > 0:
                self.cooldown -= 1
            return self.health > 0
        if self.cooldown > 0:
            self.cooldown -= 1
            if dist < 400:
                self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
            elif dist > 450:
                self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
            self.frame = (self.frame + self.glide_direction) % (3 * self.frame_change_frequency)
            self.img = self.imgs[self.frame // self.frame_change_frequency]
        else:
            if dist < 100:
                self.start_glide(20, 24, 20, (self.y > game_states.DISTANCE) * 2 - 1)
                self.cooldown = self.cooldown_length
                self.img = self.dashing.img
            elif dist < 300:
                self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
            elif dist < 450 and game_states.CAMERA_BOTTOM + 100 < self.y < game_states.CAMERA_BOTTOM + game_states.HEIGHT - 100:
                self.start_glide(20, 24, 20, (self.y < game_states.DISTANCE) * 2 - 1)
                self.cooldown = self.cooldown_length
                self.img = self.dashing.img
            else:
                self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
        if abs(self.x) < 40 and abs(self.y - game_states.DISTANCE) < 56:
            game_structures.deal_damage(1, self)
            game_states.DISTANCE = self.y + 56 * ((self.y < game_states.DISTANCE) * 2 - 1)
            self.start_glide(25, 10, 15, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
            glide_player(1, 20, 10, (self.y < game_states.DISTANCE) * 2 - 1)
            game_structures.begin_shake(10, (20, 20), (13, -9))
        return self.health > 0

    def hit(self, damage: int, source):
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(25, 10, 15, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(25, 10, 15, ((self.y - source.pos[0]) > 0) * 2 - 1)

    @classmethod
    def make(cls, determiner: int, area):
        return cls((0, area.random.randint(area.length // 3, 2 * area.length // 3)), area.difficulty)


class Projectile(Entity):

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int], health: int = 1, speed: int = 1,
                 destruct_on_collision: bool = True, damage: int = 1, expiry: int = None):
        super().__init__(img, rotation, pos)
        self.max_health = health
        self.health = health
        self.move = (round(speed * math.sin(rotation)), -round(speed * math.cos(rotation)))
        self.destruct_on_collision = destruct_on_collision
        self.damage = damage
        self.expiration_date = expiry

    def tick(self) -> bool:
        self.freeze_y(False)
        self.x += self.move[0]
        self.y += self.move[1]
        if self.expiration_date == 0:
            return False
        if self.expiration_date is not None:
            self.expiration_date -= 1
        if self.y < game_states.BOTTOM:
            return False
        if self.y > game_states.LAST_AREA_END + 1000:
            return False
        rect = self.rect
        if rect.right > -32 and rect.left < 32 and rect.bottom < game_states.DISTANCE + 32 and rect.top > game_states.DISTANCE - 32:
            game_structures.deal_damage(self.damage, self)
            glide_player(self.damage * 2, 10, 1, (self.y < game_states.DISTANCE) * 2 - 1)
            if self.destruct_on_collision:
                return False
        self.freeze_y(True)
        return self.health > 0


class Archer(Glides):
    """
    first long ranger
    """

    cost = 6

    imgs = [images.ARCHER_DRAWN, images.ARCHER_DRAWING, images.ARCHER_RELAXED]

    def __init__(self, pos: tuple[int, int], difficulty: int, area):
        super().__init__(images.ARCHER_RELAXED.img, 0, pos)
        self.max_health = 4
        self.health = 4
        self.area = area
        self.cooldown_length = max(240 - difficulty * 6, 60)
        self.cooldown = self.cooldown_length

    def tick(self) -> bool:
        if self.glide_speed != 0:
            self.glide_tick()
            return self.health > 0
        self.rotation = 180 * (self.y < game_states.DISTANCE)
        dist = abs(self.y - game_states.DISTANCE)
        if self.cooldown == 0:
            if dist < 900:
                self.cooldown = self.cooldown_length
                self.area.entity_list.append(Projectile(images.ARROW.img, self.rotation, (self.x + self.area.random.randint(-1, 1) * 16, self.y), speed=5))
        elif abs(self.y - game_states.CAMERA_BOTTOM - game_states.HEIGHT // 2) < game_states.HEIGHT // 2:
            self.cooldown -= 1
            self.img = self.imgs[3 * self.cooldown // self.cooldown_length]
        if dist < 150:
            self.start_glide(20, 10, 2, (self.y > game_states.DISTANCE) * 2 - 1)
        if dist < 400:
            self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
        elif dist > 450:
            self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
        return self.health > 0

    def transfer(self, area):
        self.area = area

    def first_seen(self):
        for i in range(1, 3):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img

    @classmethod
    def make(cls, determiner: int, area):
        return cls((0, area.random.randint(area.length // 3, 2 * area.length // 3)), area.difficulty, area)


class Knight(Glides):
    """
    first enemy with a defensive stance
    """

    cost = 20

    imgs = []
    frame_change_frequency = 10

    top = images.KNIGHT_TOP
    stabbing = images.KNIGHT_STABBING
    shielding = images.KNIGHT_SHIELDING

    def __init__(self, rotation: int, pos: tuple[int, int], hands):
        super().__init__(self.top.img, rotation, pos)
        self.hands = hands
        for i in range(len(hands)):
            if self.hands[i] is None:
                continue
            self.hands[i].pos = (self, i)
        self.frame = 0
        self.max_health = 20
        self.health = 20
        self.step = None

    def draw(self):
        canvas = pygame.Surface((64, 64), flags=pygame.SRCALPHA)
        if self.step is not None:
            canvas.blit(
                self.step,
                (0, 0)
            )
        for hand in self.hands:
            if hand is None:
                continue
            hand.draw(hand)
            if not items.in_use(hand):
                continue
            hand_drawing = None
            match hand.type:
                case items.ItemTypes.SimpleStab:
                    hand_drawing = self.stabbing.img
                case items.ItemTypes.SimpleShield:
                    hand_drawing = self.shielding.img
            if hand_drawing is None:
                continue
            canvas.blit(
                pygame.transform.flip(
                    hand_drawing,
                    hand.pos[1] == 0,
                    False
                ),
                (0, 0)
            )
        canvas.blit(
            images.KNIGHT_TOP.img,
            (0, 0)
        )
        self.img = canvas
        super().draw()

    def tick(self) -> bool:
        if self.glide_speed > 0:
            self.glide_tick()
            return self.health > 0
        self.rotation = 180 * (self.y < game_states.DISTANCE)
        dist = abs(self.y - game_states.DISTANCE)
        desired_dist = 300
        trigerable = None
        for hand in self.hands:
            if hand is None:
                continue
            if hand.pos[0] is not self:
                hand.pos = (self, hand.pos[1])
            hand.tick(hand)
            if items.action_available(hand):
                new_dist = items.find_range(hand)
                if new_dist < desired_dist:
                    trigerable = hand
                    desired_dist = new_dist
        if trigerable is not None:
            if dist < desired_dist + 32:
                trigerable.action(trigerable)
                # print(self is trigerable.pos[0], self.pos == trigerable.pos[0].pos)
        if dist < desired_dist - 100:  # back up
            self.frame = (self.frame - 1) % (self.frame_change_frequency * 6)
            self.step = self.imgs[self.frame // self.frame_change_frequency]
            self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
        elif (dist > desired_dist + 100) or (trigerable is not None and dist > desired_dist):  # go towards
            self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
            self.frame = (self.frame + 1) % (self.frame_change_frequency * 6)
            self.step = self.imgs[self.frame // self.frame_change_frequency]
        else:
            self.frame = 0
            self.step = None
        return self.health > 0

    def hit(self, damage: int, source):
        if isinstance(source, items.Item):
            if not items.from_player(source):
                return
            for hand in self.hands:
                if hand is None:
                    continue
                if hand.type is items.ItemTypes.SimpleShield:
                    if hand.datapack[0]:
                        if isinstance(source.pos, int):
                            if (self.y > game_states.DISTANCE) != (self.rotation < 90 or self.rotation > 270):
                                return
                        else:
                            if (self.y > source.pos[1]) != (self.rotation < 90 or self.rotation > 270):
                                return
        elif isinstance(source, Entity):
            if source.allied_with_player == self.allied_with_player:
                return
            for hand in self.hands:
                if hand is None:
                    continue
                if hand.type is items.ItemTypes.SimpleShield:
                    if hand.datapack[0]:
                        if (self.y > source.y) != (self.rotation < 90 or self.rotation > 270):
                            return
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(12, 15, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(12, 15, 1, ((self.y - source.pos[0]) > 0) * 2 - 1)

    def first_seen(self):
        self.stabbing.img
        self.shielding.img
        self.__class__.imgs = [
            images.KNIGHT_STEP_1.img,
            images.KNIGHT_STEP_2.img,
            images.KNIGHT_STEP_1.img,
            pygame.transform.flip(images.KNIGHT_STEP_1.img, True, False),
            pygame.transform.flip(images.KNIGHT_STEP_2.img, True, False),
            pygame.transform.flip(images.KNIGHT_STEP_1.img, True, False),
        ]

    def enter(self):
        super().enter()
        for i in range(len(self.hands)):
            if self.hands[i] is None:
                continue
            self.hands[i].pos = (self, i)

    @classmethod
    def make(cls, determiner: int, area):
        making = cls(0, (0, 200), [items.random_simple_stab(1, area.random), None])
        # making.enter()
        # print("Used make method for knight")
        return making


class Lazer(Entity):
    """
    a lazer that can hurt the player.  Stationary.
    Superclass, can be subclassed to add/replace ends, ends should be registered pre super call
    """

    def __init__(self, y: int, charge_time: int, duration: int, area, repeats: int | None = 1, damage: int = 1):
        super().__init__(images.EMPTY, 0, (0, y))
        if not hasattr(self, "ends"):
            self.ends = [
                ComponentEntity(images.LAZER_END.img, self, 0, (-game_states.WIDTH // 2 + 100, y)),
                ComponentEntity(images.LAZER_END.img, self, 180, (game_states.WIDTH // 2 - 100, y))
            ]
        area.entity_list.extend(self.ends)
        self.charge_time = charge_time
        self.cooldown = 0
        self.firing = False
        self.duration = duration
        self.repeats = repeats
        self.hit = False
        self.damage = damage

    def tick(self):
        for end in self.ends:
            if not end.alive:
                for kill_end in self.ends:
                    kill_end.alive = False
                return False
        self.cooldown += 1
        if self.firing:
            if not self.hit:
                end2 = self.ends[-1]
                for i in range(len(self.ends)):
                    end1 = end2
                    end2 = self.ends[i]
                    intercept = end2.y - end2.x * (end1.y - end2.y) / (end1.x - end2.x)  # hit left side
                    if abs(intercept - game_states.DISTANCE) < 32:
                        game_structures.begin_shake(12, (8, 8), (-2, 3))
                        self.hit = True
                        break
                if self.hit:
                    game_structures.deal_damage(self.damage, end2)
            if self.cooldown >= self.duration:
                if self.repeats is not None and self.repeats <= 0:
                    for kill_end in self.ends:
                        kill_end.alive = False
                    return False
                self.cooldown = 0
                self.hit = False
                self.firing = False
        else:
            if self.cooldown >= self.charge_time:
                self.repeats -= 1
                self.cooldown = 0
                self.firing = True
        return True

    def draw(self):
        if self.firing:
            positions = [end.screen_pos for end in self.ends]
            # print(positions)
            pygame.draw.lines(
                game_structures.SCREEN,
                (255, 255, 255),
                True,
                positions,
                12
            )
            end2 = self.ends[-1]
            for i in range(len(self.ends)):
                end1 = end2
                end2 = self.ends[i]
                intercept = end2.y - end2.x * (end1.y - end2.y) / (end1.x - end2.x)  # hit left side
                pygame.draw.circle(
                    game_structures.SCREEN,
                    (255, 255, 255),
                    game_structures.to_screen_pos((0, intercept)),
                    25
                )

    def transfer(self, area):
        self.health = 0
        for end in self.ends:
            end.alive = False


class TrackingLazer(Lazer):
    """
    lazer subclass that chases the player while not firing
    """

    def __init__(self, y: int, charge_time: int, duration: int, area, repeats: int | None = 1, damage: int = 1):
        super().__init__(y, charge_time, duration, area, repeats, damage)
        self.velocity = 0

    def tick(self):
        if not self.firing:
            self.velocity += (self.y + self.velocity * 10 < game_states.DISTANCE) * 2 - 1
            self.y += self.velocity
            for end in self.ends:
                end.y += self.velocity
        return super().tick()

    @classmethod
    def make(cls, determiner: int, area):
        return cls(area.start_coordinate + area.random.randint(0, 1) * area.length, 120, 60, area, 1, 1)


class ComponentEntity(Entity):
    """
    Any entity that is only a component of another, larger body.  Like lazer ends.
    All work should be done in the 'brains' entity
    """

    def __init__(self, img: pygame.Surface, parent: Entity, rotation: int, pos: tuple[int, int]):
        self.parent = parent
        super().__init__(img, rotation, pos)
        self.alive = True

    def tick(self):
        return self.alive


class Fish(Glides):
    """
    fish entity that leaps from the void
    """

    def __init__(self, area):
        super().__init__(images.EMPTY, 0, (30000, area.start_coordinate))
        self.max_health = 4
        self.state = 3
        self.health = 4
        self.random = random.Random(area.random.randint(0, 2 ** 32 - 1))
        self.speed = min(area.difficulty // 4, 12)
        self.wait = 0
        self.target_flight = 0
        self.direction = 0
        self.already_hit = False
        self.frame_change_ticks = 12 // round(math.sqrt(self.speed))

    def tick(self):
        self.glide_tick()
        self.wait -= 1
        match self.state:
            case 0:  # underwater
                if self.wait <= 0:
                    self.direction = self.random.randint(0, 1) * 2 - 1
                    self.rotation = 90 - 90 * self.direction
                    self.target_flight = 15 * self.random.randint(3, 5) // round(math.sqrt(self.speed))
                    self.state = 1
                    if self.random.randint(0, 1):  # go on the player
                        self.y = game_states.DISTANCE
                        self.x = 0
                    else:
                        self.y = game_states.DISTANCE + self.random.randint(-400, 400)
                        self.x = (self.random.randint(0, 1) * 2 - 1) * (100 + self.target_flight * self.speed // 2 + self.random.randint(0, 400))
                    self.x -= self.direction * (self.target_flight * self.speed // 2 + 20)
                    self.wait = 5 * self.frame_change_ticks
            case 1:  # surfacing
                if self.wait <= 0:
                    self.img = images.FISH.img
                    self.x += self.direction * 20
                    self.wait = self.target_flight
                    # print(self.target_flight)
                    self.already_hit = False
                    self.state = 2
                else:
                    self.img = images.FISH_RIPPLES[4 - self.wait // self.frame_change_ticks].img
            case 2:  # flying
                if self.wait <= 0:
                    self.x += self.direction * 20
                    self.state = 3
                    self.img = images.FISH_RIPPLES[4].img
                    self.rotation += 180
                    self.wait = 5 * self.frame_change_ticks
                else:
                    self.x += self.speed * self.direction
                    if not self.already_hit and abs(self.x) < 64 and abs(self.y - game_states.DISTANCE) < 48:
                        self.already_hit = True
                        self.wait //= 2
                        game_structures.deal_damage(1, self)
                        glide_player(5, 2, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
                        game_structures.begin_shake(6, (10, 10), (-5, 7))
            case 3:  # diving
                if self.wait <= 0:
                    self.state = 0
                    self.wait = 3 * 60 + 60 * self.random.randint(0, 3)
                    self.img = images.EMPTY
                    self.x = 30000  # go offscreen, shoo
                else:
                    self.img = images.FISH_RIPPLES[self.wait // self.frame_change_ticks].img
        return self.health > 0

    def hit(self, damage, source):
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(damage, 20, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(damage, 20, 1, ((self.y - source.pos[1]) > 0) * 2 - 1)


class Spawner(Entity):
    """
    superclass for any entity that spawns others.  Also probably its own entity?
    """

    frame_change_frequency = 9

    imgs = [images.SPAWNER_1, images.SPAWNER_2, images.SPAWNER_3, images.SPAWNER_4]

    allowable = ((Slime, 0), (Crawler, 6), (Fencer, 13), (Archer, 16), (Knight, 25))

    cost = 5

    @property
    def spawning(self):
        return self.__spawning

    def __init__(self, pos: tuple[int, int], limit: int | None, area, delay: int, entity: EntityType, deposit: tuple[int | None, int | None], speed: int):
        super().__init__(self.imgs[0].img if isinstance(self.imgs[0], images.Image) else self.imgs[0], 0, pos)
        self.max_health = 3
        self.health = 3
        self.max_health = 3
        self.area = area
        self.limit = limit
        self.__check: int = 0
        if limit is None:
            self.__list = None
        else:
            self.__list: list = [None for i in range(limit)]
        # print(limit, self.__list, delay)
        self.delay = delay
        self.timer = -1
        self.entity = entity
        self.__spawning: SpawnerHolder | None = None
        self.__stored_tick_method = None
        self.__destination = deposit
        self.__speed = speed
        self.switch_ticks = max(speed, 1)
        self.frame = 0

    def management_tick(self):
        if self.__spawning is not None:
            if self.__destination[0] is None:
                x_dist = 0
            else:
                x_dist = self.__destination[0] - self.__spawning.x
            if self.__destination[1] is None:
                y_dist = 0
            else:
                y_dist = self.__destination[1] - self.__spawning.y
            dist = abs(x_dist) + abs(y_dist)
            if dist < self.__speed // 2 + 1:
                self.__spawning.pos = (
                    self.__spawning.x if self.__destination[0] is None else self.__destination[0],
                    self.__spawning.y if self.__destination[1] is None else self.__destination[1]
                )
                if self.__list is not None:
                    self.__list[self.__check] = self.__spawning
                    self.__spawning.index = self.__check
                else:
                    self.__spawning.index = None
                # while not self.__spawning.deployed:
                self.__spawning.deployed = True
                self.__spawning = None
                return
            self.__spawning.x += self.__speed * round(x_dist / dist)
            self.__spawning.y += self.__speed * round(y_dist / dist)
            return
        if self.timer == -1:
            if self.__list is None:
                self.timer = 0
                return
            self.__check = (self.__check + 1) % len(self.__list)
            if self.__list[self.__check] is None:
                # print("found")
                self.timer = 0
            elif not self.__list[self.__check].alive:
                self.__list[self.__check] = None
                self.timer = 0
            return
        if self.timer >= self.delay:
            # print("spawning")
            self.timer = -1
            self.__spawning = SpawnerHolder(self.entity.make(self.area.random.randint(0, 2 ** 16 - 1), self.area),
                                            self, self.__check, self.__destination)
            self.__spawning.enter()
            self.area.entity_list.append(self.__spawning)
            self.__spawning.pos = self.pos
            # print(self.__spawning.tick())
            return
        self.timer += 1

    def draw(self):
        super().draw()
        # game_structures.SCREEN.blit(
        #     game_structures.FONTS[20].render(
        #         str(self.__list),
        #         False,
        #         (0, 0, 0)
        #     ),
        #     self.screen_pos
        # )

    def lose(self, index):
        """
        signal to the spawner to lose track of an object
        :param index:
        :return:
        """
        if index is None:
            return
        if index == -1:
            self.__spawning = None
        else:
            # print("losing", index, "out of", len(self.__list))
            self.__list[index] = None

    def tick(self):
        self.management_tick()
        self.frame = (self.frame + 1) % (4 * self.frame_change_frequency * self.switch_ticks)
        self.img = self.imgs[self.frame // (self.frame_change_frequency * self.switch_ticks)]
        return self.health > 0

    def transfer(self, area):
        if self.__spawning is not None:
            if self.__spawning.y < self.area.end_coordinate:
                self.__spawning = None
        if self.__list is not None:
            for i in range(len(self.__list)):
                if self.__list[i] is None:
                    continue
                if self.__list[i].y < self.area.end_coordinate:
                    self.__list[i] = None
        self.area = area

    @classmethod
    def make(cls, determiner: int, area):
        index = 0
        while index < len(cls.allowable) - 1:
            if area.difficulty < cls.allowable[index][1] or not cls.allowable[index][0].seen:
                index -= 1
                break
            if area.random.randint(0, 1):
                break
            index += 1
        if area.difficulty < cls.allowable[index][1] or not cls.allowable[index][0].seen:
            index -= 1
        entity = cls.allowable[index][0]
        if area.random.randint(0, area.difficulty) > 20 + area.difficulty // 2 + entity.cost ** 2:
            limit = None
            delay = area.random.randint(12, 17) * 100
        else:
            lower = math.floor(area.difficulty / entity.cost / 20)
            limit = area.random.randint(
                max(1, lower),
                max(1, lower * 2)
            )
            delay = area.random.randint(5, 8) * 20
        y = area.random.randint(area.length // 3, area.length - 100)
        return cls((area.random.randint(100, game_states.WIDTH // 2) * (area.random.randint(0, 1) * 2 - 1), y), limit,
                   area, delay, entity, (0, None), area.difficulty // 10 + 1)

    def first_seen(self):
        for i in range(1, 4):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img


class SpawnerHolder(Entity):
    """
    helper entity class that takes in an entity and wraps it so that the spawner can keep track.
    Most data should just be passing onto the held entity
    """

    is_holder = True

    @property
    def img(self):
        return self.holding.img

    @img.setter
    def img(self, val):
        self.img = val

    @property
    def health(self):
        return self.holding.health

    @health.setter
    def health(self, val):
        self.holding.health = val

    @property
    def pos(self):
        return self.holding.pos

    @pos.setter
    def pos(self, val):
        self.last_moved = 0
        self.holding.pos = val

    @property
    def x(self):
        return self.holding.x

    @x.setter
    def x(self, val):
        self.last_moved = 0
        self.holding.x = val

    @property
    def y(self):
        return self.holding.y

    @y.setter
    def y(self, val):
        self.last_moved = 0
        self.holding.y = val

    def freeze_x(self, val: bool = None):
        return self.holding.freeze_x(val)

    def freeze_y(self, val: bool = None):
        return self.holding.freeze_y(val)

    @property
    def rotation(self):
        return self.holding.rotation

    @rotation.setter
    def rotation(self, val):
        self.holding.rotation = val

    __id = 0

    def __init__(self, holding: Entity, holder: Spawner, index, destiny = (None, None)):
        self.last_moved = 0
        self.holding: Entity = holding
        self.holder: Spawner = holder
        self.index = index
        self.deployed = False
        self.alive = True
        self.id = SpawnerHolder.__id
        self.destiny = destiny
        SpawnerHolder.__id += 1
        super().__init__(holding.img, holding.rotation, holding.pos)

    def hit(self, damage: int, source):
        # print(f"{self.pos}, {self.health}, {self.deployed}")
        self.holding.hit(damage, source)

    def tick(self) -> bool:
        self.last_moved += 1
        if self.deployed:
            res = self.holding.tick()
            if not res:
                self.alive = False
                # print("Dying", self.index)
                self.holder.lose(self.index)
            return res
        if self.holder.spawning is not self:
            if self.holder.spawning is None:
                self.deployed = True
            elif self.holder.spawning.id != self.id:
                self.deployed = True
        if self.destiny[0] is None:
            x_dist = 0
        else:
            x_dist = self.destiny[0] - self.x
        if self.destiny[1] is None:
            y_dist = 0
        else:
            y_dist = self.destiny[1] - self.y
        dist = abs(x_dist) + abs(y_dist)
        if dist < 5:
            self.deployed = True
        if self.health <= 0:
            self.alive = False
            self.holder.lose(-1)
            return False
        return True

    def draw(self):
        self.holding.draw()

    def enter(self):
        self.holding.enter()


class Bomb(Glides):

    def __init__(self, pos, rotation, img, speed, taper, glide_duration, delay, size, damage, from_player=False):
        super().__init__(img, rotation, pos)
        self.life = delay
        self.size = size
        self.damage = damage
        self.flash_delay = 0
        self.allied_with_player = from_player
        self.start_glide(speed, glide_duration, taper, -math.cos(math.radians(rotation)))
        # print(self.glide_direction, self.glide_speed, self.glide_duration)

    def tick(self):
        self.glide_tick()
        # print(self.y)
        self.life -= 1
        if self.life <= 0:
            # print("exploding")
            colliding = pygame.Rect(
                self.x - self.size // 2, self.y - self.size // 2,
                self.size, self.size
            )
            if self.allied_with_player:
                for entity in game_structures.all_entities():
                    if colliding.colliderect(entity.rect):
                        entity.health -= self.damage
            if colliding.colliderect(pygame.Rect(-32, game_states.DISTANCE - 32, 64, 64)):
                game_structures.deal_damage(self.damage, self)
                glide_player(self.damage, 20, 1, (self.y < game_states.DISTANCE) * 2 - 1)

            # make the particles
            area = game_structures.AREA_QUEUE[0]
            # print("particles")
            for i in range(self.damage * self.size ** 2 // (64 ** 2) // 2 // 4 + 1):
                area.particle_list.add(Particle(
                    images.EXPLOSION_PARTICLES,
                    12,
                    36,
                    (
                        area.random.randint(self.x - self.size // 2 + 32, self.x + self.size // 2 - 32),
                        area.random.randint(self.y - self.size // 2 + 32, self.y + self.size // 2 - 32)
                    ),
                    rotation=90 * area.random.randint(0, 3)
                ))
        if self.flashing <= 0:
            self.flash_delay -= 1
            if self.flash_delay <= 0:
                self.flash_delay = self.life // 6 + 8
                self.flashing = 8
        return self.life > 0

    @staticmethod
    def find_range(img, speed, taper, glide_duration, delay, size, damage, from_player=False):
        """
        finds the range of the bomb.  More or less correct.
        """
        if delay <= glide_duration:
            return speed * delay
        if delay <= glide_duration + speed // taper:
            remainder = delay - glide_duration
        else:
            remainder = speed // taper
        return speed * glide_duration + remainder * (2 * speed - taper * remainder) // 2


class DelayedDeploy(Entity):

    def __init__(self, delay, area, entity: type(Entity), args):
        super().__init__(images.EMPTY, 0, (3000, area.start_coordinate))
        self.delay = delay
        self.area = area
        self.entity = entity
        self.args = args

    def tick(self):
        self.delay -= 1
        if self.delay <= 0:
            self.area.entity_list.append(self.entity(*self.args))
            # print("delayed deploy initiated")
        return self.delay > 0


class Particle(Entity):
    """
    a basic particle.  Inherits Entity for draw assistance.
    """

    __id = 0

    def __init__(self, imgs: list[images.Image] | list[pygame.Surface], tick_rate: int, lifespan: int, pos: tuple[int, int], momentum: tuple[int, int] = (0, 0), rotation: int = 0):
        self.imgs: list[pygame.Surface] = imgs
        if isinstance(self.imgs[0], images.Image):
            for i in range(len(self.imgs)):
                self.imgs[i] = self.imgs[i].img
        super().__init__(self.imgs[0], rotation, pos)
        self.ticks_per_frame_change = tick_rate
        self.frame_loop = len(self.imgs) * tick_rate
        self.frame = 0
        self.momentum = momentum
        self.lifespan = lifespan
        self.__id = Particle.__id
        Particle.__id += 1

    def tick(self):
        self.lifespan -= 1
        self.frame = (self.frame + 1) % self.frame_loop
        self.img = self.imgs[self.frame // self.ticks_per_frame_change]
        self.x += self.momentum[0]
        self.y += self.momentum[1]
        return self.lifespan > 0

    def __eq__(self, other):
        if self is other:
            return True

    def __hash__(self):
        return self.__id


if __name__ == "__main__":
    import game_areas
    import utility
    import main
    import ingame

    game_states.PLACE = game_structures.PLACES.in_game

    game_structures.CUSTOM_EVENT_CATCHERS.append(ingame.event_catcher)
    game_states.PLACE = game_structures.PLACES.in_game

    game_states.DISTANCE = 100
    game_states.BOTTOM = 0
    game_states.RECORD_DISTANCE = 0
    game_states.LAST_AREA_END = 0
    # player state management
    game_states.HEALTH = 5
    game_states.LAST_DIRECTION = 1
    game_states.GLIDE_SPEED = 0
    game_states.GLIDE_DIRECTION = 0
    game_states.GLIDE_DURATION = 0
    game_states.TAPER_AMOUNT = 0
    # screen shake management
    game_states.X_DISPLACEMENT = 0
    game_states.Y_DISPLACEMENT = 0
    game_states.SHAKE_DURATION = 0
    game_states.X_LIMIT = 0
    game_states.Y_LIMIT = 0
    game_states.X_CHANGE = 0
    game_states.Y_CHANGE = 0
    # screen
    game_states.CAMERA_BOTTOM = 0
    # area management
    game_states.AREAS_PASSED = 0
    game_states.LAST_AREA = 0
    game_states.AREA_QUEUE_MAX_LENGTH = 3

    game_structures.HANDS = [None, None]

    # game_areas.add_game_area().join()
    # game_structures.AREA_QUEUE[0].length += 20000
    # game_states.LAST_AREA_END = game_structures.AREA_QUEUE[0].end_coordinate
    area = game_areas.GameArea(10000, 20)
    area.difficulty = 60
    # area.entity_list.append(Knight.make(5672979812, area))
    # area.entity_list.append(Fish(area))
    # area.entity_list.append(ingame.entities.ItemEntity(items.simple_bomb(
    #     (0, 4 * 128),
    #     15,
    #     1,
    #     20,
    #     240,
    #     600,
    #     4
    # )))
    for i in range(9):
        pos = (-200, i * 256)
        area.entity_list.append(Spawner(
            pos,
            1,
            area,
            0,
            make_item_duplicator(items.random_simple_bomb(area.random, pos)),
            (0, None),
            2
        ))

    area.finalize()
    # area.enter()
    game_states.LAST_AREA_END = area.end_coordinate
    game_structures.AREA_QUEUE.append(area)
    game_areas.add_game_area()
    game_areas.add_game_area()

    while game_states.RUNNING:
        game_structures.SCREEN.fill(main.backdrop)
        game_states.PLACE()
        utility.tick()