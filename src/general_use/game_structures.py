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

a module containing classes for various game structures
"""
from dataclasses import dataclass
from typing import Union, Callable

from pygame.font import Font, SysFont
from pygame.transform import scale
import pygame.mixer
from pygame.event import custom_type
from collections import deque
from threading import Lock

from general_use import utility
from gtts import gTTS
from io import BytesIO
from data import images, game_states

import math


def recursive_subclasses(cls: type) -> list[type]:
    lst: list[type] = cls.__subclasses__()
    i: int = 0
    while i < len(lst):
        lst.extend(lst[i].__subclasses__())
        i += 1
    return lst


SCREEN: pygame.Surface = None
TRUE_SCREEN: pygame.Surface = None
TRUE_HEIGHT: int = 0
TRUE_WIDTH: int = 0


class Place:

    def __init__(
            self,
            tick: Callable,
            enter: Callable = utility.passing,
            end: Callable = utility.passing,
            catcher: Callable = utility.make_simple_always(False),
            crash_on: Callable = utility.make_simple_always(False),
            exit_on: Callable = utility.passing,
    ):
        self.tick = tick
        self.enter = enter
        self.end = end
        self.catcher = catcher
        self.crash = crash_on
        self.exit = exit_on

    def start(self, *args, **kwargs):
        switch_to_place(self, *args, **kwargs)


def switch_to_place(place: Place, *args, **kwargs):
    if not isinstance(place, Place):
        return switch_to_place(place.value, *args, **kwargs)
    if game_states.PLACE:
        game_states.PLACE.end(*args, **kwargs)
    game_states.PLACE = place
    game_states.PLACE.enter(*args, **kwargs)
    BUTTONS.convert()


def display_screen():
    if TRUE_HEIGHT > 0:
        pygame.transform.scale(SCREEN, (TRUE_WIDTH, TRUE_HEIGHT), TRUE_SCREEN)
    pygame.display.flip()


__minimum_height = 2 * 864


def determine_screen():
    global TRUE_HEIGHT, TRUE_WIDTH, TRUE_SCREEN, SCREEN
    # print(game_states.HEIGHT, __minimum_height)
    if game_states.HEIGHT < __minimum_height:
        TRUE_SCREEN = SCREEN
        # print("resize")
        TRUE_HEIGHT = game_states.HEIGHT
        TRUE_WIDTH = game_states.WIDTH
        game_states.WIDTH = round(game_states.WIDTH * __minimum_height / game_states.HEIGHT)  # scale width appropriately
        game_states.HEIGHT = __minimum_height
        SCREEN = pygame.Surface((game_states.WIDTH, game_states.HEIGHT), pygame.SRCALPHA)


def to_screen_x(x: int = 0) -> int:
    return x + game_states.WIDTH // 2 + game_states.X_DISPLACEMENT


def to_screen_y(y: int = 0) -> int:
    return game_states.HEIGHT + game_states.CAMERA_BOTTOM - y - game_states.Y_DISPLACEMENT


def to_screen_pos(pos: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    return to_screen_x(pos[0]), to_screen_y(pos[1])


def begin_shake(duration: int, maximum: tuple[int, int], change_per_tick: tuple[int, int]) -> None:
    game_states.SHAKE_DURATION = duration
    game_states.X_LIMIT, game_states.Y_LIMIT = maximum
    game_states.X_CHANGE, game_states.Y_CHANGE = change_per_tick


# def deal_damage(damage: int, source):
#     if game_states.INVULNERABLE:
#         return False
#     if hasattr(source, "in_knockback"):
#         if source.in_knockback:
#             return False
#     if game_states.INVULNERABILITY_LEFT == 0:
#         for hand in HANDS:
#             if hand is None:
#                 continue
#             if hand.type is items.ItemTypes.SimpleShield:
#                 if hand.data_pack[0]:
#                     if isinstance(source, entities.Entity):
#                         if (source.y > game_states.DISTANCE) != (game_states.LAST_DIRECTION == -1):
#                             return False
#                         continue
#                     if isinstance(source.pos, int):
#                         continue
#                     elif isinstance(source.pos[0], entities.Entity):
#                         if (source.pos[0].y > game_states.DISTANCE) != (game_states.LAST_DIRECTION == -1):
#                             return False
#                         continue
#         game_states.HEALTH = max(game_states.HEALTH - damage, 0)
#         game_states.TIME_SINCE_LAST_INTERACTION = 0
#         game_states.INVULNERABILITY_LEFT = damage * 15 + 5
#         return True
#         # print(source, source.pos, source.img, source.tick, source.draw)


# SCREEN = pygame.display.set_mode((500, 200))
CLOCK = pygame.time.Clock()


HANDS = [None, None]


class FontHolder:
    """
    class to hold required fonts dynamically
    """

    def __init__(self, name: str = None, fonttype=None, _scale: float = 1) -> None:
        self.fonts = dict()
        self.font_name = name
        self.font_type = fonttype
        self.scale = _scale

    def new_sysfonts(self, name) -> None:
        """
        change font in the holder
        :param name: name of new font
        :return: None
        """
        self.font_name = name
        self.font_type = SysFont
        self.fonts.clear()

    def new_fonts(self, path) -> None:
        """
        change font in holder
        :param path:
        :return:
        """
        self.font_name = path
        self.font_type = Font
        self.fonts.clear()

    def __getitem__(self, key: Union[int, float]) -> Font:
        """
        gets item from holder
        :param key: size to look for
        :return: Font object
        """
        key = int(key * self.scale)
        if key not in self.fonts.keys():
            self.fonts[key] = self.font_type(self.font_name, key)
        return self.fonts[key]


FONTS = FontHolder(name="resources/fonts/Old-English-Gothic-Pixel.ttf", fonttype=Font, _scale=0.5)
# FONTS = FontHolder(name="resources/fonts/OldEnglishGothicPixelRegular-gx1jp.otf", fonttype=Font)
TUTORIAL_FONTS = FontHolder(name="resources/fonts/PixgamerRegular-OVD6A.ttf", fonttype=Font)


def get_special_click(indicator: str | int):
    if not isinstance(indicator, str):
        return indicator
    else:
        return getattr(ingame.Inputs, indicator)


from general_use.buttons import *


BUTTONS = ButtonHolder()


VOICE_END_EVENT = custom_type()
VOICE_CHANNEL: pygame.mixer.Channel = None

SpeakNode = None


@dataclass()
class SpeakNode:
    """
    holds a text message to speak
    """
    text: str
    next: Union[None, SpeakNode] = None


class QueueSpeech:
    """
    holds information for queued sounds for alerts
    """

    def __init__(self, speach: Callable):
        self.front = None
        self.back = None
        self.speach = speach
        self.speaking = False
        VOICE_CHANNEL.set_endevent(VOICE_END_EVENT)
        # print("New Queuespeach instantiated")

    def add(self, text: str) -> None:
        """
        adds text to queue
        :param text:
        :return:
        """
        new = SpeakNode(text)
        if self.back is not None:
            self.back.next = new
        self.back = new

        # print(cls.front)
        if self.front is None:
            # print(f"saying {text}")
            self.front = self.back
            # print(cls.front)
            self.speak()

    def speak(self) -> None:
        """
        speaks
        :return:
        """
        # print("Speaking")
        self.speach(self.front.text)

    def next_speach(self) -> None:
        """
        goes to the next_
        :return:
        """
        # print("Next")
        if self.front is None:
            return
        self.front = self.front.next
        if self.front is None:
            self.back = None
        else:
            self.speak()


ALERTS = None


@dataclass()
class Alert:
    """"
    holds a single alert instance
    """


@dataclass()
class Alert:
    """
    holds a single alert instance
    """
    img: Surface
    last_tick: int
    height: int
    above: Union[Alert, None]
    y: int


class AlertHolder:
    """
    holds alerts for the game
    """

    def __init__(
            self,
            width: int,
            size: int,
            max_alerts: int,
            speed: int,
            speak: Callable,
            draw: Callable,
            border_buffer: int,
            lifespan: int
    ):
        self.text_size = size
        self.front_alert = None
        self.back_alert = None
        self.width = width
        self.max_alerts = max_alerts
        self.on_tick = 0
        self.decay = lifespan
        self.speed = speed
        self.speak = QueueSpeech(speak)
        self.draw = draw
        self.border_buffer = border_buffer

    def remove_last_alert(self) -> None:
        """
        removes the last/front alert from the queue
        :return:
        """
        self.front_alert = self.front_alert.above
        if self.front_alert is None:
            self.back_alert = None

    def add_alert(self, text: str, img: Surface = None) -> None:
        """
        adds an alert to the list
        :param text: text for the alert
        :param img: image that goes with display
        :return: None
        """
        if img is None:
            width = 0
            height = 0
        else:
            width, height = img.get_size()
            width += self.border_buffer
        self.speak.add(text)
        text_img = self.draw(
            text,
            TUTORIAL_FONTS[self.text_size],
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            max_line_pixels=self.width - width - self.border_buffer * 2,
            max_width=self.width - width - self.border_buffer * 2,
            text_align=0.5,
            max_lines=2,
            enforce_width=self.width - width - self.border_buffer * 2
        )
        height = max(height, text_img.get_height()) + self.border_buffer * 2
        surface = Surface((self.width, height))
        surface.fill((255, 255, 255))
        if img is not None:
            surface.blit(
                img,
                (self.border_buffer, self.border_buffer)
            )
        surface.blit(
            text_img,
            (self.border_buffer + width, self.border_buffer)
        )
        rect(
            surface,
            (0, 0, 0),
            Rect(
                (-1, -1),
                (self.width + 1, height + 1)
            ),
            round(self.border_buffer / 2)
        )
        alert = Alert(
            surface,
            self.on_tick + self.decay,
            height,
            None,
            -1 * height
        )
        if self.back_alert is not None:
            self.back_alert.y = 0
            self.back_alert.above = alert
        self.back_alert = alert
        if self.front_alert is None:
            self.front_alert = alert

    def tick(self) -> Union[Surface, None]:
        """
        ticks the alert system
        :return:
        """
        if self.front_alert is None:
            self.on_tick = 0
            return None
        self.on_tick += 1
        draw_queue = []
        boop = self.front_alert
        if self.on_tick >= boop.last_tick:
            boop.y -= self.speed
            if boop.y + boop.height < 0:
                self.remove_last_alert()
                boop = boop.above
                if boop is None:
                    self.on_tick = 0
                    return None
        i = 0
        while True:
            i += 1
            draw_queue.append((boop.img, boop.height, boop.y))
            if boop.above is None or i >= self.max_alerts:
                break
            else:
                boop = boop.above
        if not draw_queue:
            return None
        if self.on_tick < boop.last_tick:
            boop.y += self.speed
            if boop.y > 0:
                boop.y = 0
        height = 0
        for img, img_height, y in draw_queue:
            height += y + img_height
        surface = Surface((self.width, height))
        height = 0
        for img, img_height, y in reversed(draw_queue):
            height += y
            surface.blit(
                img,
                (0, height)
            )
            height += img_height
        return surface

    def catch_event(self, event) -> bool:
        if event.type == VOICE_END_EVENT:
            self.speak.next_speach()
            return True
        return False


@utility.make_async
def speak(text: str) -> None:
    """
    wrapper to make asynchronous speach work
    :param text: text to read
    :return: none
    """
    if game_states.DO_TTS:
        mp3_fp = BytesIO()
        try:
            tts = gTTS(text)
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            VOICE_CHANNEL.play(pygame.mixer.Sound(file=mp3_fp))
        except:
            return


@dataclass()
class ControlOption:
    """
    a control option for the control menu
    """
    name: str
    value: Any
    typ: str
    button_index: int = None
    args: Union[list[Any], None] = None
    dependent: Union[tuple[int, Any], None] = None


@dataclass()
class TypingData:
    """
    holds information about current typing target
    """
    typing: bool = False
    button_target: Button = None
    text: str = ""
    instance: int = 0


TYPING = TypingData()


def start_typing(start_text: str = "", button: Button = None) -> TypingData:
    """
    begins typing, output in cls.text
    :param start_text: what starting text is
    :param button: what button editing
    :return: typing instance
    """
    global TYPING
    TYPING = TypingData(
        typing=True,
        text=start_text,
        button_target=button,
        instance=TYPING.instance + 1
    )
    if button is not None:
        button.typing_instance = TYPING.instance
    return TYPING


def end_typing() -> str:
    """
    ends typing
    :return: string typed
    """
    global TYPING
    TYPING = TypingData(
        typing=False,
        text=TYPING.text
    )
    return TYPING.text


def get_first_match(substring: str, strings: list[str]) -> Union[str, None]:
    """
    finds first string in a list with a matching substring
    :param substring: searching for
    :param strings: searching through
    :return: first instance
    """
    if "\n" in substring:
        substring = substring[:substring.index("\n")]
    for i, string in enumerate(strings):
        if substring in string:
            return string
    return None


def init() -> None:
    global VOICE_CHANNEL, ALERTS, PLACES

    from general_use import utility
    from run_game import ingame
    from screens import main_screen
    from screens import end_screens

    VOICE_CHANNEL = utility.make_reserved_audio_channel()
    tutorials.TUTORIAL_VOICE_CHANNEL = utility.make_reserved_audio_channel()
    ALERTS = AlertHolder(
        width=game_states.WIDTH // 2,
        size=60,
        max_alerts=5,
        speed=10,
        speak=speak,
        draw=ButtonHolder.draw_text,
        border_buffer=20,
        lifespan=300
    )

    CUSTOM_EVENT_CATCHERS.append(ALERTS.catch_event)

    class PLACES(enum.Enum):
        in_game = ingame.screen
        dead = end_screens.dead_screen
        won = end_screens.won_screen
        lost = end_screens.lost_screen
        main = main_screen.main_screen_place


class Body:
    """
    a supercontainer for Rects.  Allows for rotation.
    """

    @property
    def rotation(self):
        return self.__rotation

    @rotation.setter
    def rotation(self, val: int):
        if val != self.__rotation:
            self.__rotation = val % 360
            self._rotated_img = None
            self.__flashing_img = None

    @property
    def img(self):
        if self._rotated_img is None and self.__original_img is not None:
            self._rotated_img = pygame.transform.rotate(self.__original_img, self.__rotation)
        return self._rotated_img

    @img.setter
    def img(self, val: Surface):
        if isinstance(val, images.Image):
            val = val.img
        self.__radius = Body.__calc_radius(val.get_width(), val.get_height())
        self.__original_img = val
        self._rotated_img = None
        self.__flashing_img = None

    @property
    def flashing_img(self):
        if self.__flashing_img is None:
            img = pygame.Surface(self.img.get_rect().size, flags=pygame.SRCALPHA)
            img.blit(self.img, (0, 0))
            img.fill((255, 255, 255), special_flags=pygame.BLEND_ADD)
            img.blit(self.img, (0, 0), None, pygame.BLEND_RGB_SUB)
            self.__flashing_img = img
        return self.__flashing_img

    @utility.memoize(guarantee_natural=True)
    @staticmethod
    def __calc_radius(w: int, h: int) -> int:
        return math.isqrt(w ** 2 + h ** 2) // 2

    def radius(self) -> int:
        return self.__radius

    @property
    def width(self):
        return self.__original_img.get_width()

    @property
    def height(self):
        return self.__original_img.get_height()

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, val: tuple[int, int]):
        self.x = val[0]
        self.y = val[1]

    @property
    def screen_pos(self):
        return to_screen_pos(self.pos)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val: int):
        if not self.__x_frozen:
            self._x = val

    def freeze_x(self, val: bool = None):
        if val is not None:
            self.__x_frozen = val
        return self.__x_frozen

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val: int):
        if not self.__y_frozen:
            self._y = val

    def freeze_y(self, val: bool = None):
        if val is not None:
            self.__y_frozen = val
        return self.__y_frozen

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int] | None):
        self.__original_img = img
        self.__flashing_img = None
        self.__radius = Body.__calc_radius(img.get_width(), img.get_height())
        self._rotated_img = None
        self.__rotation = 0
        self.rotation = rotation
        self.__x_frozen = False
        self.__y_frozen = False
        if pos is not None:
            self.x = pos[0]
            self.y = pos[1]

    @property
    def rect(self):
        if self.__original_img is None:
            return None
        if self._rotated_img is None:
            self._rotated_img = pygame.transform.rotate(self.__original_img, self.rotation)
        return self._rotated_img.get_rect(center=self.pos)

    def __corners_helper(self, x_width_offset, x_height_offset, y_width_offset, y_height_offset, width_factor, height_factor):
        """
        a helper to find a corner
        :return: corner
        """
        return (
            self.x + x_width_offset * width_factor + x_height_offset * height_factor,
            self.y + y_height_offset * height_factor - y_width_offset * width_factor
        )

    @property
    def corners(self) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
        theta = math.radians(-self.rotation)
        # affecting _
        x_width_offset = (self.width * math.cos(theta)) // 2
        x_height_offset = (self.height * math.sin(theta)) // 2
        y_width_offset = (self.width * math.sin(theta)) // 2
        y_height_offset = (self.height * math.cos(theta)) // 2
        # noinspection PyTypeChecker
        return tuple(
            self.__corners_helper(x_width_offset, x_height_offset, y_width_offset, y_height_offset,
                2 - 2 * abs(i - 1.5), abs(4 - 2 * abs(i - 0.5)) - 2)
            for i in range(4)
        )

    def collide(self, other):
        """
        tests if two objects collide.  The other object should be a Body, or subclass.
        :param other: needs to have a rect value that is a pygame Rect
        :return:
        """
        if not self.rect.colliderect(other.rect):
            return False
        this_corners = self.corners
        other_corners = other.corners
        if self.sides_intersect(this_corners, other_corners):
            return True
        # if self.point_inside_points(this_corners[0], other_corners):
        #     return True
        # if self.point_inside_points(other_corners[0], this_corners):
        #     return True
        return False

    def colliderect(self, other: pygame.Rect):
        """
        check if a body collides with a rect from pygame
        :param other:
        :return:
        """
        if not self.rect.colliderect(other):
            return False
        this_corners = self.corners
        other_corners = (other.topleft, other.topright, other.bottomright, other.bottomleft)
        if self.sides_intersect(this_corners, other_corners):
            return True
        if other.collidepoint(this_corners[0][0], this_corners[0][1]):
            return True
        return self.point_inside_points(other_corners[0], this_corners)

    @staticmethod
    def __counter_clockwise(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    @staticmethod
    def intersect(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], d: tuple[int, int]):
        """
        checks if line segment AB intersects CD
        :return:
        """
        return Body.__counter_clockwise(a, c, d) != Body.__counter_clockwise(b, c, d) and Body.__counter_clockwise(a, b, c) != Body.__counter_clockwise(a, b, d)

    @staticmethod
    def sides_intersect(
            this_points: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]],
            other_points: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]
    ) -> bool:
        for other_i in range(4):
            for this_i in range(4):
                if Body.intersect(
                        other_points[other_i - 1], other_points[other_i],
                        this_points[this_i], this_points[this_i - 1]
                ):
                    return True
        return False

    @staticmethod
    def point_inside_points(
            point: tuple[int, int],
            points: tuple[tuple[int, int], tuple[int, int], tuple[int, int],
                          tuple[int, int]]
    ) -> bool:
        """
        checks if a point is within a polygon defined by other points
        :param point:
        :param points:
        """
        passed_through = 0
        x = point[0]
        y = point[1]
        for i in range(len(points)):
            point_1 = points[i]
            point_2 = points[i - 1]
            if abs(point_1[0] - point_2[0]) // 2 > abs(x - (point_1[0] + point_2[0]) // 2):
                if point_1[1] + (x - point_1[0]) * (point_2[1] - point_1[1]) / (point_2[0] - point_1[0]) > y:
                    passed_through += 1
        return bool(passed_through % 2)


CUSTOM_EVENT_CATCHERS: list[Callable] = []
PLACES = None
AREA_QUEUE = deque()
NEW_AREAS = deque()


def initialized_areas():
    """
    gets a list of areas that have been intialized
    :return:
    """
    res = []
    for area in AREA_QUEUE:
        if not area.initialized:
            return res
        res.append(area)
    return res


def get_last_initialized():
    """
    gets the last initialized area.
    :return:
    """
    res = None
    for area in AREA_QUEUE:
        if not area.initialized:
            return res
        res = area


from run_game import ingame, items, entities, tutorials

PLAYER_ENTITY: entities.PlayerEntity = entities.PlayerEntity()

if __name__ == "__main__":

    SCREEN = utility.game_structures.SCREEN

    body_img = pygame.Surface((200, 400), pygame.SRCALPHA)
    body_img.fill((0, 0, 0))
    body = entities.Entity(body_img, 0, (0, game_states.HEIGHT // 2))

    cursor_img = pygame.Surface((50, 50))
    cursor_img.fill((128, 128, 128))
    cursor = entities.Entity(cursor_img, 0, (0, 0))


    def click_catcher(event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            body.rotation += 30


    utility.game_structures.CUSTOM_EVENT_CATCHERS.append(click_catcher)


    def to_screen_points(points: tuple[tuple[int, int], ...]):
        return tuple(to_screen_pos(point) for point in points)


    while game_states.RUNNING:
        SCREEN.fill((255, 255, 255))
        cursor.pos = (2 * pygame.mouse.get_pos()[0] - game_states.WIDTH // 2, game_states.HEIGHT - 2 * pygame.mouse.get_pos()[1])
        body.draw()
        cursor.draw()
        pygame.draw.polygon(
            SCREEN,
            (0, 255, 0),
            to_screen_points(body.corners),
            3
        )
        pygame.draw.circle(
            SCREEN,
            (0, 255, 0),
            to_screen_pos(body.corners[0]),
            15,
            3
        )
        pygame.draw.polygon(
            SCREEN,
            (0, 255, 0),
            to_screen_points(cursor.corners),
            3
        )
        pygame.draw.circle(
            SCREEN,
            (0, 255, 0),
            to_screen_pos(cursor.corners[0]),
            15,
            3
        )
        if body.collide(cursor):
            pygame.draw.rect(
                SCREEN,
                (0, 255, 0),
                pygame.Rect(
                    0,
                    0,
                    50,
                    50
                )
            )
        utility.tick()
