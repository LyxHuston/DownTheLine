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

entities file, but only for bosses
"""
import dataclasses
import functools
import math
import random

from run_game import entities, gameboard
from data import images, game_states
import pygame
from general_use import game_structures
from collections import deque
from typing import Self, Callable
from screens.custom_runs import FieldOptions


class Boss(entities.Entity):
    """
    a boss superclass.  Just has a 'player entered' and alive property
    """

    alive = True

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.hit_track = []  # used to check if multiple body parts are being hit by the same thing in the same tick
        self.state = 0  # 0 if not crossed middle, 1 if crossed middle
        self.target: entities.Entity | None = None

    def player_entered(self):
        pass

    def hit(self, damage: int, source) -> bool:
        if source not in self.hit_track:
            self.health -= damage
            self.hit_track.append(source)
            return True
        return False

    def tick(self):
        self.hit_track.clear()

    def cross_boundary(self):
        """called when the player has crossed the halfway point into a boss area"""
        self.state = 1
        self.target = self.closest_enemy()


class BodyPart(entities.Entity):
    """
    a body part of a boss
    """

    collide_priority: int = 3
    immune_collide_below: int = 4

    def damage_player(self):
        game_structures.begin_shake(120, (200, 200), (21, 59))
        self.boss.damage_player()

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int], boss, damage: int = 5,
                 collides: bool = True):
        super().__init__(img, rotation, pos)
        self.boss: Boss = boss
        self.collides: bool = collides
        self.damage: int = damage

    @property
    def alive(self) -> bool:
        return self.boss.alive

    @alive.setter
    def alive(self, val):
        self.boss.alive = val

    def tick(self):
        if not self.boss.alive:
            return
        if not self.collides:
            return
        for en in self.colliding(lambda other: other.allied_with_player is not self.allied_with_player):
            en.hit(self.damage, self)

    def hit(self, damage: int, source):
        self.boss.hit(damage, source)

    def draw(self):
        """
        draws boss body part, flashing based on if the boss is damaged.  Doesn't shake
        """
        if self.img is None:
            return
        if self.boss.flashing > 0:
            img = pygame.Surface(self.img.get_rect().size, flags=pygame.SRCALPHA)
            img.blit(self.img, (0, 0))
            img.fill((255, 255, 255), special_flags=pygame.BLEND_ADD)
            img.blit(self.img, (0, 0), None, pygame.BLEND_RGB_SUB)
        else:
            img = self.img
        game_structures.SCREEN.blit(
            img,
            (
                game_structures.to_screen_x(self.x) - img.get_width() // 2,
                game_structures.to_screen_y(self.y) - img.get_height() // 2
            )
        )
        return self.pos


class Serpent(Boss):
    """
    a serpent that coils around the track
    """

    @dataclasses.dataclass
    class PathItem:
        rotation: int
        position: tuple[int, int]

    @dataclasses.dataclass
    class PathTracker:
        body_part: BodyPart
        path_parts: deque

    @dataclasses.dataclass
    class MovementOption:
        turn: Callable[[], None]
        finish_check: Callable[[], bool]

    @dataclasses.dataclass
    class MovementMakerEntry:
        make: Callable[[], tuple[Callable[[], None], Callable[[], bool]]]
        weight: int

    fields = (
        FieldOptions.Area.value()
        ,
    )

    def __init__(self, area, size: int):
        super().__init__(images.EMPTY, 0, (0, 0))
        self.parts: tuple[Serpent.PathTracker] | None = None
        self.health = 50
        self.area_length: int = area.length
        self.area_start = 0
        self.movement: Serpent.MovementOption = Serpent.MovementOption(lambda: None, lambda: True)
        self.area_end = 0
        self.random = random.Random(area.get_next_seed())
        self.size = size
        self.speed = 12 + 5 * self.size
        self.body_part_sep = self.size + 1
        self.body_length = 30 + 5 * self.size
        self.imgs = tuple(pygame.transform.scale_by(img.img, self.size) for img in images.SERPENT_BODY)

        self.movement_options: dict[bool, tuple[Serpent.MovementMakerEntry]] = {
            True: (
                Serpent.MovementMakerEntry(
                    self.make_spiral_movement,
                    5
                ),
                Serpent.MovementMakerEntry(
                    self.make_goto_movement,
                    1
                )
            ),
            False: (
                Serpent.MovementMakerEntry(
                    self.make_spiral_movement,
                    2
                ),
            )
        }

    @classmethod
    def make(cls, area) -> Self:
        return cls(area, area.random.randint(2, 3))

    def turn_towards(self, angle):
        diff: int = angle - self.rotation
        if abs(diff) > 180:
            diff = 360 - diff
        if abs(diff) > 5:
            self.rotation += math.copysign(3, diff)
        elif abs(diff) > 1:
            self.rotation += diff // 2

    def make_spiral_movement(self) -> tuple[Callable[[], None], Callable[[], bool]]:
        direction = self.random.choice((-1, 1))
        tightness = self.random.randint(2, 5)
        change = self.random.randint(-2, 2) / 20
        duration = 60 * self.random.randint(1, 5)
        if change > 0:
            duration = min(duration, int((8 - tightness) / change))

        def turn():
            nonlocal change, duration, tightness
            duration -= 1
            if duration % self.size == 0:
                self.rotation += direction * int(tightness)
                tightness += change

        return turn, lambda: duration <= 0

    def make_goto_movement(self) -> tuple[Callable[[], None], Callable[[], bool]]:
        destination = (
            self.random.choice((-1, 1)) * self.random.randint(game_states.WIDTH // 4, game_states.WIDTH // 2),
            self.random.randint(
                max(self.area_start + self.area_length // 4, self.y - self.area_length // 8),
                min(self.area_end - self.area_length // 4, self.y + self.area_length // 8)
            )
        )

        def turn():
            to_angle = math.degrees(math.atan2(destination[0] - self.x, self.y - destination[1])) % 360
            diff: int = to_angle - self.rotation
            if abs(diff) > 180:
                diff = 360 - diff
            if abs(diff) > 3:
                self.rotation += math.copysign(2, diff)
            elif abs(diff) > 1:
                self.rotation += diff // 2

        return turn, lambda: (self.x - destination[0]) ** 2 + (self.y - destination[1]) < 4 * self.speed ** 2

    def get_next_movement(self) -> MovementOption:
        out_y = not self.area_start < self.y < self.area_end  # keep it in the area
        out_x = abs(self.x) > game_states.WIDTH // 2  # keep it on the screen
        if out_y or out_x:  # return

            if out_y:
                ideal_angle = 180 if self.y < self.area_start else 360
                # angle away from track, more so if closer
                adjust = 5 * round(math.sin(1/(self.x ** 2 + 3)) / math.sin(1 / 3))
                # modify so it angles correctly based on position
                adjust *= -1 if self.x < 0 else 1
                adjust *= -1 if self.y < self.area_start else 1
                ideal_angle += adjust
                ideal_angle %= 360

                def finish_check():
                    return self.area_start + self.area_length // 4 < self.y < self.area_end - self.area_length // 4

            else:
                ideal_angle = 90 if self.x < 0 else 270

                def finish_check():
                    return abs(self.x) < game_states.WIDTH // 3

            turn = functools.partial(self.turn_towards, ideal_angle)

        else:

            options: tuple[Serpent.MovementMakerEntry] = self.movement_options[self.target is None]

            tot = sum(op.weight for op in options)

            select = self.random.randint(1, tot)

            i = -1
            while select > 0:
                i += 1
                select -= options[i].weight

            turn, finish_check = options[i].make()

        return Serpent.MovementOption(turn, finish_check)

    def next_path_item(self) -> PathItem:
        if self.movement.finish_check():
            self.movement = self.get_next_movement()
        self.movement.turn()
        rads = math.radians(self.rotation)
        self.x += round(self.speed * math.sin(rads))
        self.y -= round(self.speed * math.cos(rads))
        return Serpent.PathItem(
            self.rotation,
            self.pos
        )

    def tick(self):
        if not self.state:
            return
        if self.target is None or not self.target.alive:
            self.target = self.closest_enemy(self.area_length)
        last: Serpent.PathItem = self.next_path_item()
        part: Serpent.PathTracker
        for part in self.parts:
            part.path_parts.append(last)
            part.body_part.pos = last.position
            part.body_part.rotation = last.rotation + 180
            last = part.path_parts.popleft()

    def get_image_from_index(self, i: int) -> pygame.Surface:
        # equation: https://www.desmos.com/calculator/j0qun80i6c idk how long that will be valid
        # constants that let it expand if necessary
        l = len(images.SERPENT_BODY)  # length of the images options.  Range of graph.
        m = self.body_length  # number of body parts.  Domain of graph.
        # constants that affect the shape of the graph
        c = 1/3  # center of main body hump
        d = 3  # dampener for the hump
        bfl = 1/4  # body flattening constant
        nfl = 1/4  # neck flattening constant

        f_1 = math.sin(1 / (bfl * (i - c * m) ** 2 + d)) / math.sin(1/d)  # calculate main body hump
        f_1 *= i * (m - i) / ((m / 2) ** 2)  # make sure it's 0 at the edges

        f_2 = 1 / (1 + i / (nfl * m)) - i / m * 1 / (1 + 1 / nfl)  # calculate neck width

        # join f_1 and f_2 smoothly.  Basically has each of them be a percent of height remaining
        final = 1 - (1 - f_1) * (1 - f_2)

        index = round((l - 1) * final)

        return self.imgs[index]

    def final_load(self) -> None:
        super().final_load()
        self.area_start = self.y
        self.area_end = self.area_start + self.area_length
        self.y += self.area_length + 90
        self.parts = (
            Serpent.PathTracker(
                BodyPart(pygame.transform.scale_by(images.SERPENT_HEAD.img, self.size), 0, self.pos, self),
                deque(Serpent.PathItem(0, self.pos) for _ in range(self.size * 2 + self.body_part_sep))
            ),
            *(Serpent.PathTracker(
                BodyPart(self.get_image_from_index(i), 0, (self.x, self.y + i * 100), self),
                deque(Serpent.PathItem(0, (self.x, self.y + i * 100)) for _ in range(self.body_part_sep))
            ) for i in range(self.body_length))
        )
        parts: tuple[BodyPart] = tuple(part.body_part for part in self.parts)
        part: BodyPart
        for part in parts:
            part.final_load()
        gameboard.NEW_ENTITIES.extend(parts)


boss_types = game_structures.recursive_subclasses(Boss)
