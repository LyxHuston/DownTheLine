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

from run_game import entities
import pygame
from general_use import game_structures


class Boss(entities.Entity):
    """
    a boss superclass.  Just has a 'player entered' and alive property
    """

    alive = True

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.hit_track = []  # used to check if multiple body parts are being hit by the same thing in the same tick

    def player_entered(self):
        pass

    def hit(self, damage: int, source):
        if source not in self.hit_track:
            self.health -= damage
            self.hit_track.append(source)

    def tick(self) -> bool:
        self.hit_track.clear()
        return self.health > 0


class BodyPart(entities.Entity):
    """
    a body part of a boss
    """

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int], boss, damage: int = 5,
                 collides: bool = True):
        super().__init__(img, rotation, pos)
        self.boss = boss
        self.collides = collides
        self.damage = damage

    def tick(self) -> bool:
        if not self.boss.alive:
            return False
        if not self.collides:
            return True
        if self.rect.colliderect():
            if game_structures.deal_damage(self.damage, self):
                game_structures.begin_shake(120, (200, 200), (21, 59))
        return self.boss.alive

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