"""
handles getting images only when required
"""

import pygame


class Image:

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


WALL_FULL = Image("resources/obstacle/wall_full.png")
WALL_HALF = Image("resources/obstacle/wall_half.png")
WALL_FRAGILE = Image("resources/obstacle/wall_fragile.png")


SIMPLE_SWORD = Image("resources/items/simple_sword.png")


if __name__ == "__main__":
    img = name = val = None
    for name, val in globals().items():
        if isinstance(val, Image):
            try:
                img = val.img
                print(f"Image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
            except Exception:
                print(f"Loading image {name} failed.")