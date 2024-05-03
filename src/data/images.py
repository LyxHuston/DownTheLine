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

    root: str = "./resources/"
    suffix: str = ".png"

    @property
    def img(self) -> pygame.Surface:
        """
        the image stored in the image class
        :return:
        """
        if self.__img is None:
            try:
                self.__img = pygame.image.load(self.root + self.path + self.suffix)
            except Exception:
                return EMPTY
        return self.__img

    @property
    def outlined_img(self) -> pygame.Surface:
        if self.__outlined_img is None:
            buffer: int = 2
            scale: int = 4
            width: int = self.img.get_width() // scale
            height: int = self.img.get_height() // scale
            outlining: pygame.Surface = pygame.Surface((
                self.img.get_width() + 2 * scale * buffer, self.img.get_height() + 2 * scale * buffer
            ), pygame.SRCALPHA)
            outlining.blit(self.img, (buffer * scale, buffer * scale))
            coord: int
            for coord in range((width + buffer) * (height + buffer)):
                x: int = (coord % (width + buffer) + 1) * scale
                y: int = (coord // (width + buffer) + 1) * scale
                offset_x: int
                offset_y: int
                if outlining.get_at((x, y)).a == 0:
                    if any(
                            outlining.get_at((x + offset_x * scale, y + offset_y * scale)).r == 255
                            for offset_x, offset_y in
                            ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))
                    ):
                        for offset_x, offset_y in [(i % 4, i // 4) for i in range(16)]:
                            outlining.set_at((x + offset_x, y + offset_y), (0, 0, 0, 255))
            self.__outlined_img = outlining
        return self.__outlined_img

    def __init__(self, path: str):
        self.path: str = path
        self.__img: pygame.Surface | None = None
        self.__outlined_img: pygame.Surface | None = None


# there is no case where a player image is not required on startup of the game, so it is not registered here
# same with dash icon


# entities
WALL_FULL: Image = Image("entities/obstacle/wall_full")
WALL_HALF: Image = Image("entities/obstacle/wall_half")
WALL_FRAGILE: Image = Image("entities/obstacle/wall_fragile")

SLIME_1: Image = Image("entities/slime/slime_1")
SLIME_2: Image = Image("entities/slime/slime_2")
SLIME_3: Image = Image("entities/slime/slime_3")
SLIME_4: Image = Image("entities/slime/slime_4")
SLIME_ALERT: Image = Image("entities/slime/slime_alert")

CRAWLER_1: Image = Image("entities/crawler/crawler_extended")
CRAWLER_2: Image = Image("entities/crawler/crawler_retracting")
CRAWLER_3: Image = Image("entities/crawler/crawler_mid_step")

SPAWNER_1: Image = Image("entities/spawner/spawner_1")
SPAWNER_2: Image = Image("entities/spawner/spawner_2")
SPAWNER_3: Image = Image("entities/spawner/spawner_3")
SPAWNER_4: Image = Image("entities/spawner/spawner_4")

FENCER_1: Image = Image("entities/fencer/fencer_1")
FENCER_2: Image = Image("entities/fencer/fencer_2")
FENCER_3: Image = Image("entities/fencer/fencer_3")
FENCER_DASHING: Image = Image("entities/fencer/fencer_dashing")

ARCHER_RELAXED: Image = Image("entities/archer/archer_relaxed")
ARCHER_DRAWING: Image = Image("entities/archer/archer_drawing")
ARCHER_DRAWN: Image = Image("entities/archer/archer_drawn")

KNIGHT_TOP: Image = Image("entities/knight/knight_top")
KNIGHT_STEP_1: Image = Image("entities/knight/knight_step_cycle_1")
KNIGHT_STEP_2: Image = Image("entities/knight/knight_step_cycle_2")
KNIGHT_STABBING: Image = Image("entities/knight/knight_stabbing")
KNIGHT_SHIELDING: Image = Image("entities/knight/knight_shielding")

ARROW: Image = Image("entities/projectiles/arrow")

LAZER_END: Image = Image("entities/lazer/lazer_end")

FISH_RIPPLES: list[Image] = [
    Image("entities/fish/fish_ripple_1"),
    Image("entities/fish/fish_ripple_2"),
    Image("entities/fish/fish_ripple_3"),
    Image("entities/fish/fish_ripple_4"),
    Image("entities/fish/fish_ripple_5")]
FISH: Image = Image("entities/fish/fish_flight")

TARGET: Image = Image("entities/target/target")

#bosses
SERPENT_HEAD: Image = Image("entities/serpent/serpent_head")
SERPENT_BODY: list[Image] = [
    Image("entities/serpent/serpent_body_1"),
    Image("entities/serpent/serpent_body_2"),
    Image("entities/serpent/serpent_body_3"),
    Image("entities/serpent/serpent_body_4")]

# items
SIMPLE_SWORD: Image = Image("items/simple_sword")
SIMPLE_SPEAR: Image = Image("items/simple_spear")
SIMPLE_SHIELD: Image = Image("items/simple_shield")
HATCHET: Image = Image("items/hatchet")
HATCHET_THROWN: list[Image] = [
    Image("entities/hatchet/hatchet_1"),
    Image("entities/hatchet/hatchet_2"),
    Image("entities/hatchet/hatchet_3")
]
HATCHET_BURIED: Image = Image("entities/hatchet/hatchet_buried")
# SPIKY_SHIELD = Image("./resources/items/spiky_shield.png")
SIMPLE_BOMB: Image = Image("items/simple_bomb")
BATON: Image = Image("items/baton")

# icons
LOCKED_ICON: Image = Image("items/icons/locked")
SIMPLE_STAB_ICON: Image = Image("items/icons/simple_stab")
SIMPLE_SHIELD_ICON: Image = Image("items/icons/simple_shield")
SIMPLE_THROWABLE_ICON: Image = Image("items/icons/simple_throwable")

# particles
VOID_PARTICLES: list[Image] = [
    Image("particles/basic_void/basic_void_1"),
    Image("particles/basic_void/basic_void_2"),
    Image("particles/basic_void/basic_void_3"),
    Image("particles/basic_void/basic_void_4")]

EXPLOSION_PARTICLES: list[Image] = [
    Image("particles/explosion/explosion_1"),
    Image("particles/explosion/explosion_2"),
    Image("particles/explosion/explosion_3")]

STEAM_PARTICLES: list[Image] = [
    Image("particles/steam/steam_1"),
    Image("particles/steam/steam_2"),
    Image("particles/steam/steam_3")]

PICKUP_SPARKLE_PARTICLES: list[Image] = [
    Image("particles/pickup_sparkle/sparkle_1"),
    Image("particles/pickup_sparkle/sparkle_2")
]

last_dash_particle = Image("particles/dash_ripples/ripple_4")
DASH_PARTICLES: list[Image] = [
    Image("particles/dash_ripples/ripple_1"),
    Image("particles/dash_ripples/ripple_2"),
    Image("particles/dash_ripples/ripple_3"),
    last_dash_particle,
    last_dash_particle
]
del last_dash_particle
# empty
EMPTY: pygame.Surface = pygame.Surface((0, 0))


def test_image(name: str, image: Image):
    img: pygame.Surface

    try:
        img = image.img
        print(f"Image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
        try:
            img = image.outlined_img
            print(f"Outlined image {name} loaded.  {img.get_pitch() * img.get_height()} bytes.")
        except Exception:
            print(f"Loading outlined image {name} failed.")
    except Exception:
        print(f"Loading image {name} failed.")


def test_images():

    for name, val in globals().items():
        if isinstance(val, Image):
            test_image(name, val)
        elif isinstance(val, list):
            i: int = 0
            for nest_val in val:
                test_image(name + f"_{i}", nest_val)
                i += 1


if __name__ == "__main__":
    test_images()
