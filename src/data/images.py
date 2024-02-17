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

    def __init__(self, path: str):
        self.path: str = path
        self.__img: pygame.Surface | None = None


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
# SPIKY_SHIELD = Image("./resources/items/spiky_shield.png")
SIMPLE_BOMB: Image = Image("items/simple_bomb")
BATON: Image = Image("items/baton")

# icons
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

DASH_PARTICLES: list[Image] = [
    Image("particles/dash_ripples/ripple_1"),
    Image("particles/dash_ripples/ripple_2"),
    Image("particles/dash_ripples/ripple_3"),
    Image("particles/dash_ripples/ripple_4")
]

# empty
EMPTY: pygame.Surface = pygame.Surface((0, 0))


def test_images():

    import copy

    for name, val in copy.copy(globals()).items():
        if isinstance(val, Image):
            try:
                img: pygame.Surface = val.img
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