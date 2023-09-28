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

handles getting images only when required
"""

import pygame


class Image:
    """
    an image class to consolidate references.
    """

    @property
    def img(self) -> pygame.Surface:
        """
        the image stored in the image class
        :return:
        """
        if self.__img is None:
            self.__img = pygame.image.load(self.path)
        return self.__img

    def __init__(self, path: str):
        self.path = path
        self.__img = None


# there is no case where a player image is not required on startup of the game, so it is not registered here
# same with dash icon


# entities
WALL_FULL = Image("resources/entities/obstacle/wall_full.png")
WALL_HALF = Image("resources/entities/obstacle/wall_half.png")
WALL_FRAGILE = Image("resources/entities/obstacle/wall_fragile.png")

SLIME_1 = Image("resources/entities/slime/slime_1.png")
SLIME_2 = Image("resources/entities/slime/slime_2.png")
SLIME_3 = Image("resources/entities/slime/slime_3.png")
SLIME_4 = Image("resources/entities/slime/slime_4.png")
SLIME_ALERT = Image("resources/entities/slime/slime_alert.png")

CRAWLER_1 = Image("resources/entities/crawler/crawler_extended.png")
CRAWLER_2 = Image("resources/entities/crawler/crawler_retracting.png")
CRAWLER_3 = Image("resources/entities/crawler/crawler_mid_step.png")

SPAWNER_1 = Image("resources/entities/spawner/spawner_1.png")
SPAWNER_2 = Image("resources/entities/spawner/spawner_2.png")
SPAWNER_3 = Image("resources/entities/spawner/spawner_3.png")
SPAWNER_4 = Image("resources/entities/spawner/spawner_4.png")

FENCER_1 = Image("resources/entities/fencer/fencer_1.png")
FENCER_2 = Image("resources/entities/fencer/fencer_2.png")
FENCER_3 = Image("resources/entities/fencer/fencer_3.png")
FENCER_DASHING = Image("resources/entities/fencer/fencer_dashing.png")

ARCHER_RELAXED = Image("resources/entities/archer/archer_relaxed.png")
ARCHER_DRAWING = Image("resources/entities/archer/archer_drawing.png")
ARCHER_DRAWN = Image("resources/entities/archer/archer_drawn.png")

KNIGHT_TOP = Image("resources/entities/knight/knight_top.png")
KNIGHT_STEP_1 = Image("resources/entities/knight/knight_step_cycle_1.png")
KNIGHT_STEP_2 = Image("resources/entities/knight/knight_step_cycle_2.png")
KNIGHT_STABBING = Image("resources/entities/knight/knight_stabbing.png")
KNIGHT_SHIELDING = Image("resources/entities/knight/knight_shielding.png")

ARROW = Image("resources/entities/projectiles/arrow.png")

# items
SIMPLE_SWORD = Image("resources/items/simple_sword.png")
SIMPLE_SPEAR = Image("resources/items/simple_spear.png")
SIMPLE_SHIELD = Image("resources/items/simple_shield.png")
SPIKY_SHIELD = Image("resources/items/spiky_shield.png")


# icons
SIMPLE_STAB_ICON = Image("resources/items/icons/simple_stab.png")
SIMPLE_SHIELD_ICON = Image("resources/items/icons/simple_shield.png")

# particles
VOID_PARTICLES = [Image("resources/particles/basic_void/basic_void_1.png"),
                  Image("resources/particles/basic_void/basic_void_2.png"),
                  Image("resources/particles/basic_void/basic_void_3.png"),
                  Image("resources/particles/basic_void/basic_void_4.png")]

if __name__ == "__main__":
    img = name = val = None
    for name, val in globals().items():
        if isinstance(val, Image):
            try:
                img = val.img
                print(f"Image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
            except Exception:
                print(f"Loading image {name} failed.")
        elif isinstance(val, list):
            for nest_val in val:
                if isinstance(val, Image):
                    try:
                        img = val.img
                        print(f"Image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
                    except Exception:
                        print(f"Loading image {name} failed.")