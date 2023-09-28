"""
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