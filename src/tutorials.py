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

handles the tutorial
"""

import game_states
import game_structures
import utility
from collections import deque
from dataclasses import dataclass
import pygame


@dataclass
class TutorialText:
    """
    text for the tutorial
    """
    text: str
    font: pygame.font.Font
    sound: pygame.mixer.Sound


TUTORIAL_VOICE_CHANNEL = utility.make_reserved_audio_channel()


TUTORIAL_TEXTS: deque[TutorialText] = deque()


typing = False


display = None


def tick():
    """
    tutorial tick.
    :return:
    """
    pass