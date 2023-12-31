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
    sound: pygame.mixer.Sound = None


TUTORIAL_VOICE_CHANNEL = None


TUTORIAL_TEXTS: deque[TutorialText] = deque()
on: TutorialText = None
current_text: str = ""

typing = False
typing_delay = 1
typing_cooldown = 1


up_duration = 120
up_current = 0


display: [pygame.Surface] = None


def clear_tutorial_text():
    """
    clears the tutorial texts to let users print atop them
    :return:
    """
    global display, on, typing
    TUTORIAL_TEXTS.clear()
    display = None
    typing = False
    on = None


def add_text(text: str, font: pygame.font.Font, sound: pygame.mixer.Sound = None):
    TUTORIAL_TEXTS.append(TutorialText(text, font, sound))


def tick():
    """
    tutorial tick.
    :return:
    """
    global display, typing, typing_cooldown, current_text, up_current, on
    if display is not None:
        game_structures.SCREEN.blit(display, (0, game_states.HEIGHT - display.get_height()))
        pygame.draw.line(game_structures.SCREEN, (255, 255, 255), (0, game_states.HEIGHT - display.get_height()),
                         (game_states.WIDTH, game_states.HEIGHT - display.get_height()), 10)
    if typing:
        if typing_cooldown <= 0:
            current_text = on.text[0:len(current_text) + 1]
            display = game_structures.BUTTONS.draw_text(
                current_text,
                on.font,
                (0, 0, 0, 255),
                (255, 255, 255),
                max_line_pixels=game_states.WIDTH,
                enforce_width=game_states.WIDTH
            )
            match current_text[-1]:
                case ".":
                    typing_cooldown = 3 * typing_delay
                case _:
                    typing_cooldown = typing_delay
            if len(current_text) == len(on.text):
                typing = False
                up_current = 0
        else:
            typing_cooldown -= 1
    else:
        if up_current >= up_duration:
            if len(TUTORIAL_TEXTS) > 0:
                on = TUTORIAL_TEXTS.popleft()
                game_structures.speak(on.text)
                current_text = ""
                typing = True
            else:
                display = None
        else:
            up_current += 1
