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

describing most non-player entities.  Items and ability drops are not considered
entities
"""
import weakref

import pygame

from run_game import abilities, ingame, gameboard
from data import game_states, images
from general_use import game_structures, utility
import random
import math
from typing import Type, Iterable, Self, Callable, Literal


def glide_player(speed: int, duration: int, taper: int, direction: int):
    game_states.GLIDE_SPEED = speed
    game_states.GLIDE_DURATION = duration
    game_states.TAPER_AMOUNT = taper
    game_states.GLIDE_DIRECTION = direction


class Entity(game_structures.Body):
    """
    base entity class that describes a few things most entities need to do
    """

    biggest_radius: int = 0

    __instances: list | set | None = None
    __add_instance: Callable[[Self], None] | None = None
    seen: bool = False
    first_occurs: int = 0
    tutorial_given: bool = False
    tutorial_text: str = ""

    is_item_entity: bool = False
    is_holder: bool = False

    allied_with_player: bool = False

    track_instances: bool = False

    cost: int = 2

    has_camera_mass: bool = True

    @property
    def alive(self) -> bool:
        return self.health > 0

    @alive.setter
    def alive(self, val: bool):
        if val:
            if not self.alive:
                self.health = 1
        else:
            self.health = 0

    def die(self):
        self.cleanup()

    def despawn(self):
        self.cleanup()

    cleanup_already_called: bool = False

    def cleanup(self):
        if self.track_instances:
            if not self.cleanup_already_called:
                self.__instances.remove(self)
                self.cleanup_already_called = True
            else:
                print("Redundant cleanup!")

    @property
    def health(self) -> int:
        return self.__health

    @health.setter
    def health(self, val):
        if val < self.__health:
            self.flashing = max(3 * (self.__health - val) + 25, self.flashing)
            self.__shake_limit = 2 * (self.__health - val)
            self.__x_shake_momentum = round((self.__health - val) ** 1.5 // 2)
            self.__y_shake_momentum = round(3 * (self.__health - val) ** 1.5 // 4)
            # print(self.y, game_states.DISTANCE, self.tick, val, self.tick())
        elif val > self.max_health:
            val = self.max_health
        self.__health = val

    @property
    def in_knockback(self) -> bool:
        return self.flashing > 0

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int] | None):
        super().__init__(img, rotation, pos)
        self.index = 0
        self.__offset = 0
        self.__health: int = 0
        self.max_health: int = 0
        self.flashing: int = 0
        self.__x_shake_momentum: int = 0
        self.__x_shake: int = 0
        self.__y_shake_momentum: int = 0
        self.__y_shake: int = 0
        self.__shake_limit: int = 0

    def __init_subclass__(cls, track_instances=False):
        if track_instances:
            cls.track_instances = True
            cls.__instances = list()
            cls.__add_instance = cls.__instances.append
        super().__init_subclass__()

    @classmethod
    def instances(cls) -> list[Self]:
        if not cls.track_instances:
            return []
        return list(cls.__instances)

    @classmethod
    def instance_count(cls) -> int:
        if not cls.track_instances:
            return 0
        return len(cls.__instances)

    @classmethod
    def clear_instances(cls):
        if cls.track_instances:
            cls.__instances.clear()

    @classmethod
    def clean(cls):
        cls.seen = False
        cls.tutorial_given = False
        cls.first_occurs = 0
        cls.clear_instances()

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
            if not ingame.paused:
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

    def tick(self):
        """
        runs a tick of the entity
        :return: nothing.  Used to return if the entity should be deleted, no longer does.  Some artefacts may remain
        """
        pass

    def final_load(self) -> None:
        """
        called when an area initializes.  In most cases, starts AI/movement
        :return:
        """
        if self.track_instances:
            self.__add_instance(self)
        if not type(self).seen:
            type(self).seen = True
            self.first_seen()

    @classmethod
    def make(cls, determiner: int, area) -> Self:
        """
        makes an entity in the given area of the specific entity
        :param determiner:
        :param area:
        :return:
        """
        raise NotImplementedError(f"Attempted to use make method from generic Entity superclass: {cls.__name__} should implement it separately.")

    # positional utility

    def entity_in_between(self, entity_type: Type[Self], pos: int | None = None) -> bool:
        """
        checks if there's an obstacle in between this and a target location
        :param entity_type:
        :param pos:
        :return:
        """
        if pos is None:
            pos = game_states.DISTANCE
        return any((e.y < pos) == (e.y > self.y) for e in entity_type.instances())
        # for e in entity_type.instances():
        #     if (e.y < pos) == (e.y > self.y):
        #         return True
        # return False

    def in_view(self, margin: int = 0) -> bool:
        return self.distance_to_view_edge() > margin

    def distance_to_view_edge(self):
        return min(self.y - game_states.CAMERA_BOTTOM, game_states.CAMERA_BOTTOM + game_states.HEIGHT - self.y)

    def distance_to_player(self) -> int:
        return abs(self.y - game_states.DISTANCE)

    def recenter_order(self):
        self.__offset = 0

    def next_entity_inorder(
            self, limit: int = None, accept_func: Callable[[Self], bool] = utility.make_simple_always(True)
    ) -> Self | None:
        if self.index + self.__offset < 0:
            self.__offset = self.index * -1 - 1
        while True:
            self.__offset += 1
            if self.index + self.__offset >= len(gameboard.ENTITY_BOARD):
                return None
            entity = gameboard.ENTITY_BOARD[self.index + self.__offset]
            if limit is not None and entity.y - self.y > limit:
                return None
            if accept_func(entity):
                return entity

    def prev_entity_inorder(
            self, limit: int = None, accept_func: Callable[[Self], bool] = utility.make_simple_always(True)
    ) -> Self | None:
        if self.index + self.__offset > len(gameboard.ENTITY_BOARD):
            self.__offset = len(gameboard.ENTITY_BOARD) - self.index
        while True:
            self.__offset -= 1
            if self.index + self.__offset < 0:
                return None
            entity = gameboard.ENTITY_BOARD[self.index + self.__offset]
            if limit is not None and self.y - entity.y > limit:
                return None
            if accept_func(entity):
                return entity

    def all_in_range(
            self,
            _range: int,
            accept_func: Callable[[Self], bool] = utility.make_simple_always(True)
    ) -> list[Self]:
        collect: list[Entity] = list()
        store_offset = self.__offset
        self.recenter_order()
        while True:
            check: Entity | None = self.prev_entity_inorder(limit=_range, accept_func=accept_func)
            if check is None:
                break
            collect.append(check)
        collect.reverse()
        self.recenter_order()
        while True:
            check = self.next_entity_inorder(limit=_range, accept_func=accept_func)
            if check is None:
                break
            collect.append(check)
        self.__offset = store_offset
        return collect

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.pos}>"


EntityType = Type[Entity]


invulnerable_shine_slope = 2
invulnerable_shine_speed = 16
invulnerable_shine_width = 20


def make_invulnerable_version(entity_class):
    """
    make invulnerable subclass of an entity class
    :param entity_class: an entity subclass
    :return:
    """

    class New(entity_class):
        """
        new class with frozen health
        """

        def __init__(self, *args, **kwargs):
            self.__alive = True
            self.__shine = None
            super().__init__(*args, **kwargs)

        @property
        def health(self):
            """always return 1, setter just passes to avoid errors"""
            return 1

        @health.setter
        def health(self, val: int):
            if val < 1 and self.__shine is None:
                self.__shine = (self.img.get_width() + self.img.get_height() // invulnerable_shine_slope +
                                invulnerable_shine_width)

        @property
        def alive(self) -> bool:
            return self.__alive

        @alive.setter
        def alive(self, val):
            # if not val:
                # print(f"invulnerable entity {self} killed")
            self.__alive = val

        def draw(self):
            if self.img is None:
                return
            img = self.img
            if self.__shine is not None:
                img = img.copy()
                if not ingame.paused:
                    pygame.draw.line(
                        img,
                        (255, 255, 255),
                        (self.__shine, 0),
                        (self.__shine - self.img.get_height() // invulnerable_shine_slope, self.img.get_height()),
                        invulnerable_shine_width
                    )
                    self.__shine -= invulnerable_shine_speed
                    if self.__shine < 0:
                        self.__shine = None
            game_structures.SCREEN.blit(
                img,
                (
                    game_structures.to_screen_x(self.x) - img.get_width() // 2,
                    game_structures.to_screen_y(self.y) - img.get_height() // 2
                )
            )
            return self.pos

    New.__name__ = "Invulnerable" + entity_class.__name__
    New.__qualname__ = ".".join(entity_class.__qualname__.split(".")[:-1] + [New.__name__])

    return New


InvulnerableEntity: Type[Entity] = make_invulnerable_version(Entity)


from run_game import items


class ItemEntity(InvulnerableEntity):
    """
    wrapper entity for items and abilities while on the ground to make them easier to work with
    """

    is_item_entity = True

    has_camera_mass = False

    @property
    def pos(self):
        if isinstance(self.item.pos, int):
            return 0, game_states.DISTANCE
        if isinstance(self.item.pos[0], int):
            return self.item.pos
        return self.item.pos[0].pos

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
        self.alive = False
        self.item.pos = hand
        return self.item

    def tick(self):
        if self.picked_up:
            self.alive = False
            return
        held = isinstance(self.item.pos, int)
        if not held:
            held = not isinstance(self.item.pos[0], int)
        if held:
            self.alive = False
            return
        if not self.item.tick(self.item):
            self.alive = False

    def draw(self):
        self.item.draw(self.item)


def make_item_duplicator(item: items.Item):
    """
    creates a class that just duplicates the given items
    :param item:
    :return:
    """

    action, tick, img, outline_img, pos, draw, icon, data_pack_factory, typ = items.deepcopy_datapack_factory(item)

    class ItemDuplicator(ItemEntity):

        @classmethod
        def make(cls, determiner: int, area):
            return cls(items.Item(
                action,
                tick,
                img,
                outline_img,
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
        self.glide_speed: int = 0
        self.glide_direction: int = 0
        self.taper: int = 0
        self.glide_duration: int = 0

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


InvulnerableGlides: Type[Glides] = make_invulnerable_version(Glides)


class Obstacle(Entity, track_instances=True):
    """
    harmless obstacles on path.
    """

    cost = 0
    has_camera_mass = False

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
        for entity in self.all_in_range(self.height // 2 + Entity.biggest_radius, accept_func=self.collide):
            # number arbitrarily chosen for while this is proof of concept, change limit in the future?
            if abs(entity.y - self.y) < abs(entity.x - self.x) - 48:
                entity.x = self.x + (128 + entity.rect.width // 2) * ((entity.x - self.x > 0) * 2 - 1)
            else:
                entity.y = self.y + (24 + entity.rect.height // 2) * ((entity.y - self.y > 0) * 2 - 1)
        return

    def final_load(self):
        self.freeze_y(True)
        self.freeze_x(True)
        super().final_load()

    def first_seen(self):
        self.full.img
        self.half.img
        self.fragile.img
        self.hit(0, None)


InvulnerableObstacle: Type[Obstacle] = make_invulnerable_version(Obstacle)


class Slime(Glides):
    """
    slime.  Moves up or down the path.
    """

    cost = 2

    frame_change_frequency = 16
    alert = images.SLIME_ALERT
    imgs = [images.SLIME_1, images.SLIME_2, images.SLIME_3, images.SLIME_4]
    seen = True

    def __init__(self, pos: tuple[int, int] = (0, 0), seed: int = 0, difficulty: int = 0):
        if isinstance(self.imgs[0], images.Image):
            self.imgs[0] = self.imgs[0].img
        super().__init__(self.imgs[0], 0, pos)
        self.frame = 0
        self.max_health = 7
        self.health = 7
        self.random = random.Random(seed)
        self.wait = 36
        self.max_speed = min(difficulty // 5 + 1, 6)

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
                speed = self.random.randint(1, (self.max_speed + 1) // 2)
                if speed == self.max_speed // 2 + 1:
                    speed = speed * 4 - 2
                else:
                    speed = speed * 4
                self.start_glide(
                    speed,
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
            if game_structures.deal_damage(1, self):
                glide_player(5, 2, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
                game_structures.begin_shake(6, (10, 10), (7, 5))
            self.start_glide(5, 30, 5, (self.y > game_states.DISTANCE) * 2 - 1)
            game_states.DISTANCE = self.y + 64 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
        return self.health > 0

    def first_seen(self):
        self.alert.img
        for i in range(1, 4):
            if isinstance(self.__class__.imgs[i], images.Image):
                self.__class__.imgs[i] = self.__class__.imgs[i].img

    @classmethod
    def make(cls, determiner: int, area):
        new_slime = cls((0, area.random.randint(area.length // 3, area.length)), area.difficulty)
        new_slime.random.seed(area.random.randint(0, 2 ** 32 - 1))
        return new_slime


class Crawler(Glides, track_instances=True):
    """
    crawls towards the player.  Slow, sometimes, but always a threat.
    """

    frame_change_frequency = 2

    cost = 3

    imgs = []

    tutorial_text = "Beware of the crawler.  As soon as they see you they are relentless at hunting you down."

    def __init__(self, pos: tuple[int, int], speed: int):
        super().__init__(images.CRAWLER_1.img, 0, pos)
        self.speed = speed * 2
        self.switch_ticks = max(9 // speed, 1)
        self.frame = 0
        self.max_health = 6
        self.health = 6

    def hit(self, damage: int, source):
        self.health -= damage
        if isinstance(source.pos, int):
            self.start_glide(damage, 90, 1, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
        else:
            self.start_glide(damage, 90, 1, ((self.y - source.pos[0]) > 0) * 2 - 1)

    def tick(self):
        # print(self.y, self.health)
        self.glide_tick()
        if not self.entity_in_between(Obstacle):
            if self.glide_speed == 0 or (
                    self.taper == 0 and self.glide_direction != (self.y < game_states.DISTANCE) * 2 - 1):
                self.start_glide(
                    self.speed,
                    0,
                    0,
                    (self.y < game_states.DISTANCE) * 2 - 1
                )
        if self.glide_speed > 0 and self.taper == 0:
            self.frame = (self.frame + self.glide_direction) % (len(self.imgs) * self.frame_change_frequency * self.switch_ticks)
            self.img = self.imgs[self.frame // (self.frame_change_frequency * self.switch_ticks)]
        # pygame.draw.circle(
        #     game_structures.SCREEN,
        #     (255, 255, 255),
        #     game_structures.to_screen_pos(self.pos),
        #     32,
        #     5
        # )
        if abs(self.x) < 28 and abs(self.y - game_states.DISTANCE) < 66:
            if game_structures.deal_damage(1, self):
                glide_player(round(self.speed * 1.5), 5, 10, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
                game_structures.begin_shake(6, (10, 10), (7, 5))
            self.y -= self.glide_speed * self.glide_direction
            game_states.DISTANCE = self.y + 66 * (((self.y - game_states.DISTANCE) < 0) * 2 - 1)
        collide_list: list[Entity] = self.all_in_range(self.height // 2 + Entity.biggest_radius, lambda en: not en.freeze_y() and self.collide(en))
        if self.glide_direction != 0 and collide_list:
            push_factor: float = math.inf
            new_push_factor: float
            e: Entity
            for e in collide_list:
                if self.y != e.y:
                    new_push_factor = self.y - e.y
                    if abs(new_push_factor) < abs(push_factor):
                        push_factor = new_push_factor
            if math.isfinite(push_factor):
                if abs(push_factor) > self.height // 2:
                    push_factor -= math.copysign(self.height // 2, push_factor)
                    self.y += self.height // round(2 * push_factor)
                else:
                    self.y += round(math.copysign(self.height // 2, push_factor))
        e: Entity
        for e in collide_list:
            if self.collide(e):
                e.y = self.y + (self.rect.height // 2 + e.rect.height // 2) * ((e.y - self.y > 0) * 2 - 1)
        return

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
        return cls(
            (0, area.random.randint(area.length // 3, area.length)),
            area.random.randint(1, min(max(area.difficulty // 4, 1), 5))
        )


class Fencer(Glides):
    """
    the first entity with an actually semi-complicated movement script. (Spawner doesn't count)
    Tries to keep distance except for dashes.  Dashes quickly.
    """

    dashing = images.FENCER_DASHING
    imgs = [images.FENCER_1, images.FENCER_2, images.FENCER_3]
    frame_change_frequency = 5
    cost = 10

    tutorial_text = "The fencer.  His lunge is dangerous."

    def __init__(self, pos: tuple[int, int], difficulty: int):
        super().__init__(images.FENCER_1.img, 0, pos)
        self.max_health: int = 4
        self.health: int = 4
        self.cooldown: int = 0
        self.cooldown_length: int = max(180 - difficulty, 30)
        self.frame: int = 0

    def tick(self) -> bool:
        dist = abs(self.y - game_states.DISTANCE)
        self.rotation = 180 * (self.y < game_states.DISTANCE)
        if self.glide_speed > 0:
            self.glide_tick()
            if (self.glide_duration + self.glide_speed // self.taper) % 2 == 1:
                gameboard.PARTICLE_BOARD.add(DASH_RIPPLE_PARTICLES(
                    self.pos
                ))
            if abs(self.x) < 40 and abs(self.y - game_states.DISTANCE) < 56:
                if game_structures.deal_damage(2, self):
                    glide_player(1, 20, 10, (self.y < game_states.DISTANCE) * 2 - 1)
                    game_structures.begin_shake(10, (20, 20), (13, -9))
                game_states.DISTANCE = self.y + 56 * ((self.y < game_states.DISTANCE) * 2 - 1)
                self.start_glide(25, 10, 15, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
            if self.cooldown > 0:
                self.cooldown -= 1
            return self.health > 0
        if self.entity_in_between(Obstacle) or self.entity_in_between(Crawler):
            self.cooldown = self.cooldown_length // 3
        if self.cooldown > 0:
            self.cooldown = max(0, self.cooldown - 1)
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
            elif dist < 450 and self.in_view(100):
                self.start_glide(20, 24, 20, (self.y < game_states.DISTANCE) * 2 - 1)
                self.cooldown = self.cooldown_length
                self.img = self.dashing.img
            else:
                self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
        # if abs(self.x) < 40 and abs(self.y - game_states.DISTANCE) < 56:
        #     if game_structures.deal_damage(1, self):
        #         glide_player(1, 20, 10, (self.y < game_states.DISTANCE) * 2 - 1)
        #         game_structures.begin_shake(10, (20, 20), (13, -9))
        #     game_states.DISTANCE = self.y + 56 * ((self.y < game_states.DISTANCE) * 2 - 1)
        #     self.start_glide(25, 10, 15, ((self.y - game_states.DISTANCE) > 0) * 2 - 1)
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
        # convert to radians
        self.move = (round(speed * math.sin(math.radians(rotation))), -round(speed * math.cos(math.radians(rotation))))
        self.destruct_on_collision = destruct_on_collision
        self.damage = damage
        self.expiration_date = expiry

    def tick(self):
        self.freeze_y(False)
        self.freeze_x(False)
        self.x += self.move[0]
        self.y += self.move[1]
        if self.expiration_date == 0:
            self.alive = False
            return
        if self.expiration_date is not None:
            self.expiration_date -= 1
        if self.y < game_states.BOTTOM:
            self.alive = False
            return
        if self.y > game_states.LAST_AREA_END + 1000:
            self.alive = False
            return
        rect = self.rect
        if rect.right > -32 and rect.left < 32 and rect.bottom < game_states.DISTANCE + 32 and rect.top > game_states.DISTANCE - 32:
            if game_structures.deal_damage(self.damage, self):
                glide_player(self.damage * 2, 10, 1, (self.y < game_states.DISTANCE) * 2 - 1)
            if self.destruct_on_collision:
                self.alive = False
                return
        self.freeze_y(True)
        self.freeze_x(True)


class Archer(Glides):
    """
    first long ranger
    """

    cost = 6

    imgs = [images.ARCHER_DRAWN, images.ARCHER_DRAWING, images.ARCHER_RELAXED]

    tutorial_text = "Ah, the archer.  Not much on their own, just hit down their arrows and chase them down."

    def __init__(self, pos: tuple[int, int], difficulty: int, area):
        super().__init__(images.ARCHER_RELAXED.img, 0, pos)
        self.max_health = 1
        self.health = 1
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
                gameboard.NEW_ENTITIES.append(Projectile(images.ARROW.outlined_img, self.rotation, (self.x + self.area.random.randint(-1, 1) * 16, self.y), speed=5))
        elif self.in_view():
            self.cooldown -= 1
            self.img = self.imgs[3 * self.cooldown // self.cooldown_length]
        if dist < 150:
            self.start_glide(20, 10, 2, (self.y > game_states.DISTANCE) * 2 - 1)
        if dist < 400:
            self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
        elif dist > 450:
            self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
        return self.health > 0

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

    tutorial_text = "The knights are very resilient and use weapons similar to yours.  This is the last of this sort of opponent they will send you."

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
            if hand.type == items.ItemTypes.SimpleStab:
                hand_drawing = self.stabbing.img
            elif hand.type == items.ItemTypes.SimpleShield:
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
        triggerable = None
        wall_in_between = self.entity_in_between(Obstacle)
        for hand in self.hands:
            if hand is None:
                continue
            if hand.pos[0] is not self:
                hand.pos = (self, hand.pos[1])
            hand.tick(hand)
            if not wall_in_between and items.action_available(hand):
                new_dist = items.find_range(hand)
                if new_dist < desired_dist:
                    triggerable = hand
                    desired_dist = new_dist
        if triggerable is not None:
            if dist < desired_dist + 32:
                triggerable.action(triggerable)
                # print(self is triggerable.pos[0], self.pos == triggerable.pos[0].pos)
        if dist < desired_dist - 100:  # back up
            self.frame = (self.frame - 1) % (self.frame_change_frequency * len(self.imgs))
            self.step = self.imgs[self.frame // self.frame_change_frequency]
            self.y += 5 * ((self.y > game_states.DISTANCE) * 2 - 1)
        elif (dist > desired_dist + 100) or (triggerable is not None and dist > desired_dist):  # go towards
            self.y += 5 * ((self.y < game_states.DISTANCE) * 2 - 1)
            self.frame = (self.frame + 1) % (self.frame_change_frequency * len(self.imgs))
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

    def final_load(self):
        super().final_load()
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


class Lazer(InvulnerableEntity):
    """
    a lazer that can hurt the player.  Stationary.
    Superclass, can be subclassed to add/replace ends, ends should be registered pre super call
    """

    def __init__(self, y: int, charge_time: int, duration: int, area, repeats: int | None = 1, damage: int = 1):
        # print("new lazer at:", y)
        super().__init__(images.EMPTY, 0, (0, y))
        if not hasattr(self, "ends"):
            self.ends = [
                ComponentEntity(images.LAZER_END.img, self, 90, (-game_states.WIDTH // 2 + 100, y)),
                ComponentEntity(images.LAZER_END.img, self, 270, (game_states.WIDTH // 2 - 100, y))
            ]
        if area.entity_list is None:
            gameboard.NEW_ENTITIES.extend(self.ends)
        else:
            area.entity_list.extend(self.ends)
        self.random = random.Random(area.random.randint(0, 2 ** 32 - 1))
        self.charge_time = charge_time
        self.cooldown = 0
        self.firing = False
        self.duration = duration
        self.repeats = repeats
        self.hit = False
        self.damage = damage

    def tick(self):
        for end in self.ends:  # if an end was killed, kill the whole thing
            if not end.alive:
                for kill_end in self.ends:
                    kill_end.alive = False
                self.alive = False
                return
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
                    self.alive = False
                    return
                self.cooldown = 0
                self.hit = False
                self.firing = False
        else:
            if self.cooldown % 2 == 0:
                speed = 5 * self.cooldown / self.charge_time
                spread = round(90 * (1 - (self.cooldown / self.charge_time) ** 3))
                for end in self.ends:
                    rot = end.rotation + self.random.randint(-spread, spread)
                    gameboard.PARTICLE_BOARD.add(STEAM_PARTICLES(
                        (end.x + round(10 * math.sin(math.radians(end.rotation))), end.y - round(10 * math.cos(math.radians(end.rotation)))),
                        (round(speed * math.sin(math.radians(rot))), round(speed * -1 * math.cos(math.radians(rot)))),
                        rot
                    ))
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
                intercept = round(end2.y - end2.x * (end1.y - end2.y) / (end1.x - end2.x))  # hit left side
                pygame.draw.circle(
                    game_structures.SCREEN,
                    (255, 255, 255),
                    game_structures.to_screen_pos((0, intercept)),
                    25
                )


class TrackingLazer(Lazer):
    """
    lazer subclass that chases the player while not firing
    """

    TOP = object()
    BOTTOM = object()

    def __init__(self, y: int | Literal[TOP, BOTTOM], charge_time: int, duration: int, area, repeats: int | None = 1, damage: int = 1):
        if y is TrackingLazer.BOTTOM:
            y = game_states.BOTTOM - 20
        if y is TrackingLazer.TOP:
            y = game_states.BOTTOM + game_states.HEIGHT + 20
        super().__init__(y, charge_time, duration, area, repeats, damage)
        self.velocity = 0

    def tick(self):
        if not self.firing:
            self.velocity += (self.y + self.velocity * 10 < game_states.DISTANCE) * 2 - 1
            self.y += self.velocity
            for end in self.ends:
                end.y = self.y
        super().tick()

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

    @property
    def alive(self) -> bool:
        return self.__alive

    @alive.setter
    def alive(self, val):
        self.__alive = val


class Fish(Glides, track_instances=True):
    """
    fish entity that leaps from the void
    """

    def __init__(self, area):
        super().__init__(images.EMPTY, 0, (30000, area.start_coordinate))
        # print("new fish")
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
        if self.state == 0:  # underwater
            if self.wait <= 0:
                self.direction = self.random.randint(0, 1) * 2 - 1
                self.rotation = 90 - 90 * self.direction
                self.target_flight = 15 * self.random.randint(3, 5) // round(math.sqrt(self.speed))
                self.state = 1
                if self.random.randint(0, 1 + 5 // self.instance_count()) or self.instance_count() == 1:
                    # go on the player
                    self.y = game_states.DISTANCE
                    self.x = 0
                else:
                    # be pretty... elsewhere
                    self.y = game_states.DISTANCE + self.random.randint(-400, 400)
                    self.x = (self.random.randint(0, 1) * 2 - 1) * (
                            100 + self.target_flight * self.speed // 2 + self.random.randint(0, 400))
                self.x -= self.direction * (self.target_flight * self.speed // 2 + 20)
                self.wait = 5 * self.frame_change_ticks
        elif self.state == 1:  # surfacing
            if self.wait <= 0:
                self.img = images.FISH.img
                self.x += self.direction * 20
                self.wait = self.target_flight
                # print(self.target_flight)
                self.already_hit = False
                self.state = 2
            else:
                self.img = images.FISH_RIPPLES[4 - self.wait // self.frame_change_ticks].img
        elif self.state == 2:  # flying
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
                    if game_structures.deal_damage(1, self):
                        glide_player(5, 2, 1, ((self.y - game_states.DISTANCE) < 0) * 2 - 1)
                        game_structures.begin_shake(6, (10, 10), (-5, 7))
        elif self.state == 3:  # diving
            if self.wait <= 0:
                self.state = 0
                self.wait = 3 * 60 + 60 * self.random.randint(0, 3)
                self.img = images.EMPTY
                self.x = 30000  # go offscreen, shoo
            else:
                self.img = images.FISH_RIPPLES[self.wait // self.frame_change_ticks].img # 5 total
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

    has_camera_mass = False

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
            self.__spawning.final_load()
            gameboard.NEW_ENTITIES.append(self.__spawning)
            self.__spawning.pos = self.pos
            # print(self.__spawning.tick())
            return
        self.timer += 1

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

    def despawn(self):
        if self.__spawning is not None:
            self.__spawning.alive = False

    def transfer(self, area):
        self.despawn()

    @classmethod
    def make(cls, determiner: int, area):
        index = 0
        while index < len(cls.allowable) - 1:
            if area.difficulty < cls.allowable[index][1] or not area.previously_seen(cls.allowable[index][0]):
                index -= 1
                break
            if area.random.randint(0, 1):
                break
            index += 1
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
        return cls((area.random.randint(200, game_states.WIDTH // 2) * (area.random.randint(0, 1) * 2 - 1), y), limit,
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
    def alive(self) -> bool:
        return self.holding.alive

    @alive.setter
    def alive(self, val: bool):
        self.holding.alive = val

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

    def __init__(self, holding: Entity, holder: Spawner, index, destiny=(None, None)):
        self.last_moved = 0
        self.holding: Entity = holding
        self.holder: Spawner = holder
        self.spawner_index = index
        self.deployed = False
        self.id = SpawnerHolder.__id
        self.destiny = destiny
        SpawnerHolder.__id += 1
        super().__init__(holding.img, holding.rotation, holding.pos)

    def hit(self, damage: int, source):
        # print(f"{self.pos}, {self.health}, {self.deployed}")
        self.holding.hit(damage, source)

    def tick(self):
        self.last_moved += 1
        if self.deployed:
            self.holding.tick()
            return
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
        return

    def draw(self):
        self.holding.draw()

    def final_load(self):
        self.holding.final_load()

    def die(self):
        self.holder.lose(self.spawner_index)
        self.holding.die()

    def despawn(self):
        self.holder.lose(self.spawner_index)
        self.holding.despawn()

    def cleanup(self):
        self.holder.lose(self.spawner_index)
        self.holding.cleanup()


note_speed = 15


class NoteSpawner(InvulnerableEntity):
    """
    spawns notes for minigame area
    """

    has_camera_mass = False

    @property  # Just being lazy lol
    def last_y(self):
        return self.__last_y

    @last_y.setter
    def last_y(self, val):
        self.__last_y = max(self.area.start_coordinate, min(self.area.end_coordinate, val))

    def __init__(self, area, start_track, register: Callable = None):
        super(NoteSpawner, self).__init__(images.EMPTY, 0, (0, area.length))
        self.waves = max(area.difficulty // 10, 1)
        self.area = area
        self.padding = 360 // round(math.sqrt(area.difficulty))
        self.last_y = 0
        self.random = random.Random(area.random.randint(0, 2 ** 32 - 1))
        self.start_track = start_track
        self.cooldown_track = 0
        self.last_dash_arpeggio = 0
        self.register = register

    def __add(self, e: Entity):
        gameboard.NEW_ENTITIES.append(e)
        if self.register is not None:
            self.register(e)

    def tick(self):
        if self.start_track is not None:
            if not self.start_track.alive:
                self.last_y = self.area.length // 2 + self.area.start_coordinate
                self.start_track = None
            return
        self.cooldown_track -= 1
        self.last_dash_arpeggio += 1
        if self.cooldown_track <= 0:
            choose = self.random.randint(0, 3)
            if choose == 0:  # single note
                self.__add(Note(self.last_y))
                self.cooldown_track = 60 + 30 * self.random.randint(0, 2)
                self.last_y += self.random.randint(-2, 2) * 5 * self.cooldown_track
            elif choose == 1:  # arpeggio
                direction = self.random.randint(0, 1) * 2 - 1
                offscreen = 0
                spacing = 9
                for i in range(45 // spacing):
                    self.last_y += direction * 10 * spacing
                    self.__add(Note(self.last_y, offscreen=offscreen))
                    offscreen += note_speed * spacing
                self.cooldown_track = 45
            else:
                if choose == 2 and self.last_dash_arpeggio > abilities.dash_cooldown + 10:  # dash arpeggio
                    self.last_dash_arpeggio = 0
                    direction = self.random.randint(0, 1) * 2 - 1
                    offscreen = 0
                    spacing = 10
                    for i in range(20 // spacing):
                        self.last_y += direction * 25 * spacing
                        self.__add(Note(self.last_y, offscreen=offscreen))
                        offscreen += note_speed * spacing
                    self.cooldown_track = 40
                else:  # switch arpeggio
                    direction = self.random.randint(0, 1) * 2 - 1
                    offscreen = 0
                    spacing = 15
                    for i in range(45 // spacing):
                        if self.random.random() < 0.125:
                            direction *= -1
                            self.last_y += direction * 64 * spacing
                        self.last_y += direction * 10 * spacing
                        self.__add(Note(self.last_y, offscreen=offscreen))
                        offscreen += note_speed * spacing
                    self.cooldown_track = 45
            self.cooldown_track *= 2
            self.cooldown_track += 30
            self.waves -= 1
            self.last_y = min(self.area.end_coordinate - 128, max(self.area.start_coordinate + 128, self.last_y))
        if self.waves <= 0:
            self.alive = False
        return


class Note(InvulnerableEntity):

    def __init__(self, y, loop: bool = False, offscreen: int = 0):
        super(Note, self).__init__(images.TARGET.img, 0, (game_states.WIDTH // 2 + 32 + offscreen, y))
        self.freeze_y(True)
        self.alive = True
        self.loop = loop

    def hit(self, damage: int, source):
        if damage == 0:
            self.alive = False

    def tick(self):
        self.freeze_x(False)
        self.x -= note_speed
        if self.x < -game_states.WIDTH // 2 - 32:
            if self.loop:
                self.x = game_states.WIDTH // 2 + 32
            else:
                game_structures.deal_damage(1, self)
                game_structures.begin_shake(60, (20, 20), (5, 3))
                self.alive = False
        self.freeze_x(True)
        return self.alive


class Bomb(InvulnerableGlides):

    def __init__(self, pos, rotation, img, speed, taper, glide_duration, delay, size, damage, from_player=False):
        super().__init__(img, rotation, pos)
        self.life = delay
        self.size = size
        self.damage = damage
        self.flash_delay = 0
        self.allied_with_player = from_player
        self.start_glide(speed, glide_duration, taper, int(-math.cos(math.radians(rotation))))
        # print(self.glide_direction, self.glide_speed, self.glide_duration)

    def tick(self):
        self.glide_tick()
        # print(self.y)
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            # print("exploding")
            colliding = pygame.Rect(
                self.x - self.size // 2, self.y - self.size // 2,
                self.size, self.size
            )
            if self.allied_with_player:
                for entity in self.all_in_range(500 + self.size):
                    if colliding.colliderect(entity.rect):
                        game_states.TIME_SINCE_LAST_INTERACTION = 0
                        entity.hit(self.damage, self)
            if colliding.colliderect(pygame.Rect(-32, game_states.DISTANCE - 32, 64, 64)):
                if game_structures.deal_damage(self.damage, self):
                    glide_player(self.damage, 20, 1, (self.y < game_states.DISTANCE) * 2 - 1)

            # make the particles
            area = game_structures.AREA_QUEUE[0]
            # print("particles")
            for i in range(self.damage * self.size ** 2 // (64 ** 2) // 2 // 4 + 1):
                area.particle_list.add(EXPLOSION_PARTICLES(
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


class DelayedDeploy(InvulnerableEntity):

    has_camera_mass = False

    def __init__(self, delay, area, entity: type(Entity), args, tracker: Callable = None):
        super().__init__(images.EMPTY, 0, (3000, area.start_coordinate))
        # print("delayed deploy made")
        self.delay = delay
        self.entity = entity
        self.args = args
        self.tracker = tracker

    def tick(self):
        self.delay -= 1
        if self.delay <= 0:
            e = self.entity(*self.args)
            gameboard.NEW_ENTITIES.append(e)
            if self.tracker is not None:
                self.tracker(e)
            self.alive = False


class MassDelayedDeploy(InvulnerableEntity):

    has_camera_mass = False

    def __init__(self, delay, area, entities: list[tuple[Type[Entity], Iterable]],
                 tracker: Callable = None, deployed: Callable = None):
        super().__init__(images.EMPTY, 0, (3000, area.start_coordinate))
        self.delay = delay
        self.entities = entities
        self.tracker = tracker
        self.deploy_call = deployed

    def tick(self):
        self.delay -= 1
        if self.delay <= 0:
            es = [entity(*args) for entity, args in self.entities]
            gameboard.NEW_ENTITIES.extend(es)
            if self.tracker is not None:
                for e in es:
                    self.tracker(e)
            self.alive = False
            if self.deploy_call is not None:
                self.deploy_call()


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

    def reset_id_check(self):
        if self.__id == 10000:
            Particle.__id = 0

    def __eq__(self, other):
        if self is other:
            return True

    def __hash__(self):
        return self.__id

    @property
    def img(self):
        return self._rotated_img

    @img.setter
    def img(self, val: pygame.Surface):
        if isinstance(val, images.Image):
            val = val.img
        self._rotated_img = pygame.transform.rotate(val, self.rotation)


def particle_with_settings(imgs: list[pygame.Surface] | list[images.Image], tick_rate: int, lifespan: int):
    return lambda pos, momentum = (0, 0), rotation = 0: Particle(imgs, tick_rate, lifespan, pos, momentum, rotation)


DASH_RIPPLE_PARTICLES = particle_with_settings(list(images.DASH_PARTICLES), 4, 20)
STEAM_PARTICLES = particle_with_settings(list(images.STEAM_PARTICLES), 4, 12)
EXPLOSION_PARTICLES = particle_with_settings(list(images.EXPLOSION_PARTICLES), 12, 36)
PICKUP_SPARKLES = particle_with_settings(list(images.PICKUP_SPARKLE_PARTICLES), 16, 32)


class AreaEdge(InvulnerableEntity):
    """
    a type of entity that marks one end of an area
    """

    has_camera_mass = False

    def __init__(self, area):
        super().__init__(images.EMPTY, 0, None)
        self.area = area
        self.x = 0

    def draw(self):
        pass

    def final_load(self) -> None:
        super().final_load()


class AreaStopper(AreaEdge):
    """
    marks the end of an area for area culling purposes
    """
    @property
    def y(self):
        return self.area.end_coordinate

    @y.setter
    def y(self, val):
        pass


class AreaStarter(AreaEdge):
    """
    marks the beginning of an area for when the area needs to keep track of what entities are in it
    """
    @property
    def y(self):
        return self.area.start_coordinate

    @y.setter
    def y(self, val):
        pass
