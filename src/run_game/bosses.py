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
import math

from run_game import entities, gameboard
from data import images
import pygame
from general_use import game_structures
from collections import deque
from typing import Self
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

    body_length = 20
    body_part_sep = 5
    speed = 5

    @dataclasses.dataclass
    class PathItem:
        rotation: int
        position: tuple[int, int]

    @dataclasses.dataclass
    class PathTracker:
        body_part: BodyPart
        path_parts: deque

    fields = (
        FieldOptions.Area.value()
        ,
    )

    def __init__(self, area):
        super().__init__(images.EMPTY, 0, (0, 0))
        self.parts: tuple[Serpent.PathTracker] | None = None
        self.health = 50
        self.area_length: int = area.length
        self.area_start = 0
        self.area_end = 0


    @classmethod
    def make(cls, area) -> Self:
        return cls(area)

    def next_path_item(self) -> PathItem:
        return Serpent.PathItem(
            self.rotation,
            self.pos
        )

    def tick(self):
        if not self.state:
            return
        if not self.target.alive:
            self.target = self.closest_enemy(self.area_length)
        last: Serpent.PathItem = self.next_path_item()
        part: Serpent.PathTracker
        for part in self.parts:
            part.path_parts.append(last)
            last = part.path_parts.popleft()
            part.body_part.pos = last.position
            part.body_part.rotation = last.rotation

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

        return images.SERPENT_BODY[index].img

    def final_load(self) -> None:
        super().final_load()
        self.area_start = self.y
        self.area_end = self.area_start + self.area_length
        self.y += self.area_length * 2
        self.parts = (
            Serpent.PathTracker(
                BodyPart(images.SERPENT_HEAD.img, 0, (0, 0), self),
                deque()
            ),
            *(Serpent.PathTracker(
                BodyPart(self.get_image_from_index(i), 0, (0, 0), self),
                deque()
            ) for i in range(self.body_length))
        )
        parts: tuple[BodyPart] = tuple(part.body_part for part in self.parts)
        part: BodyPart
        for part in parts:
            part.final_load()
        gameboard.NEW_ENTITIES.extend(parts)


boss_types = game_structures.recursive_subclasses(Boss)
