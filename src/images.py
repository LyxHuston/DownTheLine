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
    def img(self):
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


# items
SIMPLE_SWORD = Image("resources/items/simple_sword.png")
SIMPLE_SPEAR = Image("resources/items/simple_spear.png")

SIMPLE_STAB_ICON = Image("resources/items/icons/simple_stab.png")


if __name__ == "__main__":
    img = name = val = None
    for name, val in globals().items():
        if isinstance(val, Image):
            try:
                img = val.img
                print(f"Image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
            except Exception:
                print(f"Loading image {name} failed.")