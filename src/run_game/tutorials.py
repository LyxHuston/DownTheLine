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

from data import game_states, switches
from general_use import game_structures
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
LOG: deque[TutorialText | None] = deque()
on: TutorialText | None = None
current_text: str = ""

typing = False
typing_delay = 1
typing_cooldown = 1


auto_progress = False
up_duration = 120
up_current = 0


display: pygame.Surface | None = None
display_height = 0

WAIT_TIMES: dict[str, int | float] = {".": 12, ",": 8}

switch_ratio: float = 2/3


def next_pressed():
    global typing, current_text
    if on is None:
        return
    if typing:
        stop_typing()
        current_text = on.text
        update_display()
    else:
        next_text()


def next_text():
    global on, current_text, typing, display
    if len(TUTORIAL_TEXTS) > 0:
        on = TUTORIAL_TEXTS.popleft()
        game_structures.speak(on.text)
        current_text = on.text[0]
        typing = True
        update_display()
    else:
        clear_display()


def stop_typing():
    global typing, up_current
    typing = False
    up_current = 0


def update_display():
    global display, display_height
    display = game_structures.BUTTONS.draw_text(
        current_text,
        on.font,
        (0, 0, 0, 255),
        (255, 255, 255),
        max_line_pixels=game_states.WIDTH,
        enforce_width=game_states.WIDTH
    )
    display_height = display.get_height()


def clear_display():
    global display, display_height, current_text
    display = None
    display_height = 0
    current_text = ""


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
    tt = TutorialText(text, font, sound)
    TUTORIAL_TEXTS.append(tt)
    LOG.append(tt)


def add_texts(texts: list[tuple[str, pygame.font.Font, [pygame.mixer.Sound]]]):
    if LOG:
        LOG.append(None)
    for text in texts:
        add_text(*text)


def tick(do_tick):
    """
    tutorial tick.
    :return:
    """
    global display, typing, typing_cooldown, current_text, up_current, on, display_height
    if display is not None:
        # if switches.TUTORIAL_TEXT_POSITION:
        #     if game_states.DISTANCE - game_states.CAMERA_BOTTOM < (1 - switch_ratio) * game_states.HEIGHT:
        #         switches.TUTORIAL_TEXT_POSITION = False
        # else:
        #     if game_states.DISTANCE - game_states.CAMERA_BOTTOM > switch_ratio * game_states.HEIGHT:
        #         switches.TUTORIAL_TEXT_POSITION = True
        # below is identical
        if (
            (game_states.DISTANCE - game_states.CAMERA_BOTTOM - game_states.HEIGHT / 2) * (switches.TUTORIAL_TEXT_POSITION * -2 + 1)
            >
            game_states.HEIGHT * (switch_ratio - 0.5)
        ):
            switches.TUTORIAL_TEXT_POSITION = not switches.TUTORIAL_TEXT_POSITION

        game_structures.SCREEN.blit(
            display,
            (0, (game_states.HEIGHT - display_height) * switches.TUTORIAL_TEXT_POSITION)
        )
        line_y: int = game_states.HEIGHT - display_height if switches.TUTORIAL_TEXT_POSITION else display_height
        pygame.draw.line(
            game_structures.SCREEN,
            (255, 255, 255),
            (0, line_y),
            (game_states.WIDTH, line_y),
            10
        )
    if not do_tick:
        return
    if typing:
        if typing_cooldown <= 0:
            current_text = on.text[0:len(current_text) + 1]
            while current_text[-1] == " ":
                current_text = on.text[0:len(current_text) + 1]
            typing_cooldown = WAIT_TIMES.get(current_text[-1], 1) * typing_delay
            update_display()
            if len(current_text) == len(on.text):
                stop_typing()
        else:
            typing_cooldown -= 1
    else:
        if on is None and len(TUTORIAL_TEXTS) > 0:
            next_text()
            return
        if up_current >= up_duration:
            if auto_progress:
                next_text()
            elif current_text and not current_text.endswith("(press ENTER)"):
                current_text += "  (press ENTER)"
                update_display()
        else:
            up_current += 1
