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
on: TutorialText = None
current_text: str = None

typing = False
typing_delay = 1
typing_cooldown = 0


up_duration = 120
up_current = 0


display: [pygame.Surface] = None


def tick():
    """
    tutorial tick.
    :return:
    """
    global display, typing, typing_cooldown, current_text, up_current, on
    if display is not None:
        game_structures.SCREEN.blit(display, (0, game_states.HEIGHT - display.get_height))
        pygame.draw.line(game_structures.SCREEN, (255, 255, 255), (0, game_states.HEIGHT - display.get_height),
                         (game_states.WIDTH, game_states.HEIGHT - display.get_height), 10)
    if typing:
        if typing_cooldown >= typing_delay:
            current_text = on.text[0:len(current_text)]
            display = game_structures.BUTTONS.draw_text(
                current_text,
                on.font,
                (0, 0, 0),
                (255, 255, 255),
                max_line_pixels=game_states.WIDTH
            )
            if len(current_text) == len(on.text):
                typing = False
                up_current = 0
        else:
            typing_cooldown += 1
    else:
        if up_current >= up_duration:
            display = None
            if len(TUTORIAL_TEXTS) > 0:
                on = TUTORIAL_TEXTS.pop()
                typing = True
        else:
            up_current += 1
