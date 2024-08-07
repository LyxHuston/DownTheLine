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

handle button system
"""

import enum
from abc import ABC, abstractmethod
from typing import Union, Callable, Any


import pygame
from pygame import Rect, Surface, SRCALPHA
from pygame.transform import scale
from pygame.draw import rect

import data
from general_use import utility, game_structures


default_text_color = (255, 255, 255)
default_background = (0, 0, 0)


class BaseButton(ABC):

    def __init__(self, _rect: pygame.rect.Rect, visible_check: Callable[[], bool]):
        self.rect = _rect
        self.visible = visible_check

    @abstractmethod
    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draw onto a surface
        :return:
        """

    @abstractmethod
    def do_click(self, mouse_pos: tuple[int, int], click_type) -> bool:
        """
        checks if mouse is on the button, and if so, recursively
        :return: whether or not to stop the check
        """

    @abstractmethod
    def do_key(self, click_type) -> bool:
        """
        checks if the holder is keyed, and if so, checks children
        :return: whether or not to stop the check
        """

    def special_key_click(self, key) -> None:
        """
        just runs it down all buttons if a key input triggered a special trigger
        :param key: what key to check for special presses
        :return:
        """

    @abstractmethod
    def iter_key(self) -> int:
        """
        if keyed, change to not keyed and return
        :return:
        0 = continue
        1 = stop and push to next
        2 = stop without pushing
        """

    @property
    @abstractmethod
    def keyed(self) -> bool:
        """
        if has been selected by special keyed button selection
        :return:
        """

    @abstractmethod
    def set_keyed(self, value: bool = True) -> bool:
        """
        checks if possible to key, and does so if possible
        :return: if it could set to key
        """

    @abstractmethod
    def get_hover_keyed_text(self) -> Union[str, None]:
        """
        gets hover keyed text
        :return:
        """

    @abstractmethod
    def convert(self):
        """
        converts background/image to proper format, and any contained buttons.
        :return:
        """

    fonts = game_structures.FONTS

    @staticmethod
    def draw_text(
            text: str,
            font: int | pygame.font.Font,
            background_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = default_background,
            outline_color: tuple[int, int, int] = default_text_color,
            max_line_pixels: int = 0,
            max_line_words: int = 0,
            max_width: int = 0,
            preserve_words: bool = True,
            text_align: float = 0,
            max_lines: int = 0,
            enforce_width: int = 0
    ) -> Surface:
        """
        draws text
        :param text: string
        :param font: font size
        :param background_color: background color for the text
        :param outline_color: color used for text and border
        :param max_line_pixels: maximum number of pixels in a line, 0 for disabled
        :param max_line_words: maximum number of words in a line, 0 for disabled
        :param max_width: maximum pixels in line, scales down to match
        :param preserve_words: whether or not to preserve words when considering max line pixels
        :param text_align: left (0) to right (1) alignment of text
        :param max_lines: maximum lines in the text display
        :param enforce_width: enforce a width for the display
        :return: drawn text
        """
        lines: list[tuple[str, int]] = [("", 0)]
        word = ""
        current_word_length = 0
        words = 0

        def clear_word():
            nonlocal word, current_word_length
            word = ""
            current_word_length = 0

        def add_new_line(start: str = ""):
            nonlocal words, word, current_word_length
            if start:
                words = 1
                clear_word()
            else:
                words = 0
            words = int(bool(start))  # start with 0 if empty string, start with 1 if non-empty
            if len(lines) == max_lines:
                return True
            lines.append((start, current_word_length))  # guaranteed for start == word

        def add_word_to_last_line(check_newline: bool = True):
            nonlocal word, words, current_word_length
            if lines[-1][0]:  # if there is something in line, add a space and the word
                _new_line = lines[-1][0] + " " + word
                _length = lines[-1][1] + space_size + current_word_length
                if word and _length > max_line_pixels > 0:  # only check if it goes over if word is not empty
                    return add_new_line(word)  # nothing to do after adding
            elif word:  # if there was not something in line, the new line is the word
                _new_line = word
                _length = current_word_length
            else:
                return False

            lines[-1] = (_new_line, _length)

            if word:  # only increment words counter if word actually had something
                words += 1
                clear_word()
                if check_newline and words == max_line_words:
                    return add_new_line()
            return False

        if isinstance(font, int):
            draw_font = ButtonHolder.fonts[font]
        else:
            draw_font = font
        space_size = draw_font.size(" ")[0]

        def get_increase_size(add_char: str) -> int:
            if word:
                return draw_font.size(add_char)[0]
            else:
                return draw_font.size(word[-1] + add_char)[0] - draw_font.size(add_char)[0]

        i: int = 0
        while i < len(text):
            char = text[i]
            i += 1

            if char == "\n":
                if add_word_to_last_line(False):  # add word, don't check if it reaches max word count
                    break
                if add_new_line():
                    break
                continue

            if char == " ":  # check words, not length.  Ok, yes, it also checks length
                if add_word_to_last_line():
                    break
                continue

            if max_line_pixels > 0 and not preserve_words:
                new_line = (lines[-1] + " " + word).lstrip(" ")
                length = draw_font.size(new_line + char)[0]
                if length > max_line_pixels:
                    lines[-1] = new_line
                    if add_new_line():
                        break
            word += char
            current_word_length += get_increase_size(char)

        add_word_to_last_line()  # make sure to get the last word out

        if i < len(text):  # if it for some reason quit early (aka there is trailing text)
            backstep = -1
            while draw_font.size(lines[-1][:backstep] + "...")[0] > max_line_pixels > 0:
                backstep -= 1
                if -1 * backstep >= len(lines[-1]):
                    break
            lines[-1] = lines[-1][:backstep] + "..."

        if enforce_width != 0:
            max_length = enforce_width
        elif not lines:
            max_length = 0
        else:
            max_length = max(_length for line, _length in lines)
        if max_length > max_width > 0:
            draw_font = ButtonHolder.fonts[int(font * max_width / max_length)]
        linesize = draw_font.get_linesize()
        text_surface = Surface((max_length, linesize * len(lines)), SRCALPHA)
        if background_color is not None:
            text_surface.fill(background_color)
        for i in range(len(lines)):
            drawn = draw_font.render(lines[i][0], True, outline_color, None)
            text_surface.blit(
                drawn,
                (text_align * (max_length - drawn.get_width()), i * linesize)
            )
        text_surface.convert()
        return text_surface


class Button(BaseButton):
    """
    dataclass containing information for a button
    """

    DEFAULT = object()

    class ClickTypes(enum.Enum):
        down = 0
        up = 1
        hold = 2

    class SpecialArguments(enum.Enum):
        mouse_pos = "mouse_pos"

    def get_hover_keyed_text(self) -> Union[str, None]:
        """
        if keyed, return text, else None
        :return:
        """
        if self.keyed:
            return self.text
        return None

    @property
    def keyed(self):
        """
        if has been selected by special keyed button selection
        :return:
        """
        return self._keyed

    @keyed.setter
    def keyed(self, value):
        self._keyed = value

    def set_keyed(self, value: bool = True) -> bool:
        """
        sets the button as keyed
        :return:
        """
        if not self.visible():
            return False
        self.keyed = value
        return True

    def __init__(self, img: Surface, text: str, _rect: Rect, down_click: Union[None, Callable] = None,
                 up_click: Union[None, Callable] = None, hold_click: Union[None, Callable] = None,
                 fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = None,
                 outline_color: Union[tuple[int, int, int], None] = None,
                 inflate_center: tuple[float, float] = (0.5, 0.5), outline_width: int = 1,
                 down_arguments: Union[None, dict[str, Any]] = None, up_arguments: Union[None, dict[str, Any]] = None,
                 hold_arguments: Union[None, dict[str, Any]] = None, scale_factor: float = 1.25, special_press: tuple =
                 (), typing_instance: int = None, visible_check: Callable[[], bool] = utility.passing):
        """
        initialize a button
        :param down_click:
        :param img:
        :param text:
        :param _rect:
        :param fill_color:
        :param outline_color:
        :param inflate_center:
        :param outline_width:
        :param down_arguments:
        :param scale_factor:
        :param special_press:
        :param typing_instance:
        """
        super().__init__(_rect, visible_check)
        self.clicks = [down_click, up_click, hold_click]
        self.arguments: list[Union[None, dict[str, Any]]] = [down_arguments, up_arguments, hold_arguments]
        self.img: Surface = img
        self.text: str = text
        self.fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = fill_color
        self.outline_color: Union[tuple[int, int, int], None] = outline_color
        self.inflate_center: tuple[float, float] = inflate_center
        self.outline_width: int = outline_width
        self.scale_factor: float = scale_factor
        self.special_press: tuple = special_press
        self.typing_instance: int = typing_instance
        self.keyed = False

    @staticmethod
    def make_img_button(
            click: Union[None, callable],
            img: Surface,
            center: tuple[int, int],
            button_name: Union[str, None],
            inflate_center: tuple[float, float] = (0.5, 0.5),
            arguments: Union[None, dict[str, Any]] = None,
            scale_factor: float = 1.25,
            special_press: tuple = ()
    ):
        """
        creates a button with a given img provided as a surface
        :param click: click action
        :param img: image of button
        :param center: center of button
        :param button_name: text of the button
        :param inflate_center: where to inflate the button from
        :param arguments: click arguments
        :param scale_factor: how much the button inflates when moused over
        :param special_press: what controls can be used to press it
        :return: a formed button
        """
        return Button(img, button_name, Rect(center, (0, 0)) if img is None else img.get_rect(center=center), click,
                      inflate_center=inflate_center, outline_width=0, down_arguments=arguments, scale_factor=scale_factor,
                      special_press=special_press)

    @staticmethod
    def make_text_button(text: str, font: int, center: tuple[int, int], down_click: Union[Callable, None] = None,
                         up_click: Union[Callable, None] = None, hold_click: Union[Callable, None] = None,
                         background_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] =
                         default_background, outline_color: tuple[int, int, int] = default_text_color,
                         border_width: int = 0, max_line_pixels: int = 0, max_line_words: int = 0, max_width: int = 0,
                         preserve_words: bool = True, text_align: float = 0, x_align: float = 0.5, y_align: float = 0.5,
                         arguments: dict[str, Any] = None, special_press: Union[tuple[str], str] = (),
                         override_text: str = None, max_lines: int = 0, enforce_width: int = 0,
                         visible_check: Callable[[], bool] = utility.passing):
        """
        creates a button object
        :param text: string
        :param font: size of the font object
        :param down_click: function called when the button is clicked
        :param center: coordinate centers of the button
        :param background_color: background color for the text
        :param outline_color: color used for text and border
        :param border_width: width of border for button
        :param max_line_pixels: maximum number of pixels in a line, 0 for disabled
        :param max_line_words: maximum number of words in a line, 0 for disabled
        :param max_width: maximum width of object.  Scales to be inside of it, if not already.  0 for disabled.
        :param preserve_words: whether or not to preserve words when considering max line pixels
        :param text_align: left (0) to right (1) alignment of text
        :param x_align: where the x value of 'center' is relative to the button, left (0), right (1).  Default center
        :param y_align: where the y value of 'center' is relative to the button, top (0), bottom (1).  Default center
        :param arguments: arguments to be used in the click action
        :param special_press: special keys that press button
        :param override_text: overrides text for tts
        :param max_lines: maximum number of lines for the button
        :param enforce_width: enforces if lines can go over this width
        :return: a constructed button to be added to the list
        """
        text_surface = ButtonHolder.draw_text(
            text,
            font,
            background_color,
            outline_color,
            max_line_pixels,
            max_line_words,
            max_width,
            preserve_words,
            text_align,
            max_lines=max_lines,
            enforce_width=enforce_width,
        )
        x, y = text_surface.get_size()
        if isinstance(special_press, str) or isinstance(special_press, int):
            special = game_structures.get_special_click(special_press)
        else:
            special = tuple([game_structures.get_special_click(name) for name in special_press])
        if text == "<":
            text = "Left"
        elif text == ">":
            text = "Right"
        if override_text is None:
            override_text = text
        return Button(text_surface, override_text, pygame.Rect(center[0] - x_align * x, center[1] - y_align * y, x, y),
                      down_click=down_click, up_click=up_click, hold_click=hold_click, fill_color=background_color
                      , outline_color=outline_color, inflate_center=(x_align, y_align), outline_width=border_width,
                      down_arguments=arguments, special_press=special, visible_check=visible_check)

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draw onto a surface
        :return:
        """
        if self.img is None:
            return
        if self.rect is None:
            return
        if not self.visible():
            return
        if any(click is not None for click in self.clicks) and (self.rect.collidepoint(mouse_pos) or self.keyed):
            # mouse is over or keyed clicker is on

            # gets coordinates of button parts for scaling
            x, y = self.rect.topleft
            centerx, centery = self.rect.center
            width, height = centerx - x, centery - y
            new_centerx = centerx + width * (self.inflate_center[0] - 0.5) * -0.5
            new_centery = centery + height * (self.inflate_center[1] - 0.5) * -0.5

            new = scale(
                self.img,
                (width * 2 * self.scale_factor, height * 2 * self.scale_factor)
            )

            onto.blit(
                new,
                (new_centerx - width * self.scale_factor, new_centery - height * self.scale_factor)
            )
            if self.outline_width > 0:
                rect(
                    onto,
                    self.outline_color,
                    new.get_rect(center=(new_centerx, new_centery)).inflate(
                        1.75 * self.outline_width,
                        1.75 * self.outline_width
                    ),
                    width=self.outline_width
                )
        else:
            # not over
            onto.blit(self.img, self.rect)
            if self.outline_width > 0:
                rect(
                    onto,
                    self.outline_color,
                    self.rect.inflate(2 * self.outline_width, 2 * self.outline_width),
                    width=self.outline_width
                )

    def run_click(self, click_type, mouse_pos=None) -> bool:
        """
        runs click event
        :return: if event occurred
        """
        click = self.clicks[click_type.value]
        if click is None:
            return False
        if not self.visible():
            return False
        arguments = self.arguments[click_type.value]
        if arguments is None:
            click()
        else:
            if Button.SpecialArguments.mouse_pos.value in arguments:
                arguments[Button.SpecialArguments.mouse_pos.value] = mouse_pos
            click(**arguments)
        return True

    def do_click(self, mouse_pos: tuple[int, int], click_type) -> bool:
        """
        checks if mouse is on the button when mouse button is pressed, and if so, recursively
        :return:
        """
        if self.rect is None:
            return False
        if not self.visible():
            return False
        if self.rect.collidepoint(mouse_pos):
            return self.run_click(click_type, mouse_pos)
        return False

    def do_key(self, click_type) -> bool:
        """
        checks if button is keyed, and if so, does click
        :return:
        """
        if self.keyed:
            self.run_click(click_type)
        return self.keyed

    def special_key_click(self, key) -> bool:
        """
        ahhhh
        :return:
        """
        if not self.visible():
            return False
        if isinstance(self.special_press, int):
            special_pressed = key == self.special_press
        else:
            special_pressed = key in self.special_press
        if special_pressed:
            self.run_click(Button.ClickTypes.down)
        return special_pressed

    def iter_key(self) -> int:
        """
        iterates which button is currently keyed
        :return:
        0 = continue
        1 = stop and push to next
        2 = stop without pushing
        """
        if not self.visible():
            self.keyed = False
            return 0
        if self.keyed:
            self.keyed = False
            return 1
        return 0

    def rewrite_button(
            self,
            new_text: str,
            font: int,
            center: tuple[int, int],
            instance: int = None,
            others: list[tuple[BaseButton, float, float, int, int]] = (),
            max_line_pixels: int = 0,
            max_width: int = 0,
            y_align: float = 0.5,
            x_align: float = 0.5,
            override_button_name: str = None
    ) -> None:
        """
        change text of target button to new string.  Also moves buttons around
        as described
        :param new_text: new text to change it to
        :param font: font size of it
        :param center: center of the button to orient around
        :param instance: typing instance
        :param others: a list of other buttons to update positions of, with information
        button object: button to reposition
        float: offset x by width
        float: offset y by height
        integer: static x offset
        integer: static y offset
        :param max_line_pixels: maximum pixels in a line
        :param max_width: maximum width of the button
        :param y_align: designate where to orient y from
        :param x_align: designate where to orient x from
        :param override_button_name: override the button name if any
        :return: None
        """
        if instance is not None and self.typing_instance != instance:
            return
        new_img = Button.draw_text(new_text, font, max_line_pixels=max_line_pixels, preserve_words=True,
                                   background_color=self.fill_color, outline_color=self.outline_color)
        width = new_img.get_width()
        if width > max_width > 0:
            new_img = Button.draw_text(
                new_text,
                round(font * max_width / width),
                max_line_pixels=round(max_line_pixels * max_width / width),
                preserve_words=True
            )
            width = new_img.get_width()
        height = new_img.get_height()
        self.img = new_img
        if override_button_name is None:
            override_button_name = new_text
        self.text = override_button_name
        self.rect = new_img.get_rect(topleft=(
            center[0] - x_align * new_img.get_width(),
            center[1] - y_align * new_img.get_height()
        ))
        for other_obj, offset_width, offset_height, offset_x, offset_y in others:
            if other_obj is None:
                continue
            other_obj.rect.center = (
                center[0] + offset_width * width + offset_x,
                center[1] + offset_height * height + offset_y
            )

    @utility.make_async
    def write_button_text(
            self,
            font: int,
            max_characters: int = 0,
            min_characters: int = 0,
            others: list[tuple[Union[BaseButton], float, float, int, int]] = (),
            max_line_pixels: int = 0,
            max_width: int = 0,
            prepend: str = "",
            append: str = "",
            start_text: str = None,
            callback: Callable = None,
            y_align: int = 0.5,
            x_align: int = 0.5,
            search_against: list[str] = ()
    ) -> str:
        """
        edits a button's text.
        :param font: font size of it
        :param max_characters: max characters in a line (0 if no max)
        :param min_characters: minimum characters in a line
        :param others: a list of other buttons to update positions of, with information
        integer: button index
        float: offset x by width
        float: offset y by height
        integer: static x offset
        integer: static y offset
        :param max_line_pixels: maximum pixels in a line
        :param max_width: maximum width of the button
        :param prepend: prepend string
        :param append: append string
        :param start_text: if None, uses button name as start
        :param callback: function called when the function completes
        :param y_align: designate where to orient x from
        :param x_align: designate where to orient y from
        :param search_against: list to search for matches in
        :return: None
        """

        if self.typing_instance is not None:
            return

        if start_text is None:
            start_text = self.text
        current = start_text

        x = self.rect.left + x_align * self.rect.width
        y = self.rect.top + y_align * self.rect.height

        instance = game_structures.start_typing(current, self)

        def determine_string(finished: bool = False) -> str:
            if finished:
                if search_against == ():
                    return prepend + current + append
                if current == "":
                    return prepend + "<search>" + append
                match = game_structures.get_first_match(instance.text, search_against)
                if match is None:
                    game_structures.speak("No match found")
                    return prepend + "<no match found>" + append
                return prepend + match + append
            if search_against == ():
                return prepend + current + "_" + append
            if current == "":
                return prepend + "<search>" + append
            match = game_structures.get_first_match(instance.text, search_against)
            if match is None:
                game_structures.speak("No match found")
                return prepend + "<no match found>" + append
            return prepend + match + "_" + append

        self.rewrite_button(determine_string(), font, (x, y), instance.instance, others,
                            max_line_pixels, max_width, y_align, x_align, start_text)

        try:
            while game_structures.TYPING.instance == instance.instance and data.game_states.RUNNING:
                if instance.text != current:
                    if len(instance.text) > max_characters > 0:
                        current = instance.text[0:max_characters]
                        if "\n" in instance.text[max_characters:]:
                            game_structures.end_typing()
                            break
                        instance.text = current
                    current = instance.text
                    if min_characters <= len(current):
                        if len(current) > 0 and current[-1] == "\n":
                            current = current[:-1]
                            game_structures.end_typing()
                            break
                    if "\n" in current:
                        instance.text = current[:current.index("\n")]
                        current = instance.text
                        game_structures.end_typing()
                        break
                    self.rewrite_button(determine_string(), font, (x, y), instance.instance,
                                        others, max_line_pixels, max_width, y_align, x_align, start_text)
        finally:
            if "\n" in current:
                current = current[:current.index("\n")]
            if len(current) > max_characters > 0 or min_characters > len(current):
                result = start_text
            else:
                result = current
            if search_against != ():
                result = game_structures.get_first_match(result, search_against)
                if result is None:
                    result = search_against[0]
            current = result
            if self.typing_instance == instance.instance:
                self.rewrite_button(determine_string(finished=True), font, (x, y), instance.instance,
                                    others,
                                    max_line_pixels, max_width, y_align, x_align)
                self.typing_instance = None
            if callback is not None:
                callback(result)
            return result

    def convert(self):
        if self.img is not None:
            self.img.convert()

    def __repr__(self):
        return f"{self.__class__.__name__}[rect:{self.rect}, text:{self.text}]"


class DrawButton(Button):

    def __init__(self, text: str,
                 draw_func: Callable[[pygame.Surface, bool, tuple[int, int]], pygame.Rect | None] |
                 Callable[[pygame.Surface, bool, tuple[int, int], Any, ...], pygame.Rect | None],
                 _rect: pygame.Rect, colors: tuple | list | None = None,
                 data_pack: Any = None, down_click: Union[None, Callable] = None,
                 up_click: Union[None, Callable] = None, hold_click: Union[None, Callable] = None,
                 down_arguments: Union[None, dict[str, Any]] = None, up_arguments: Union[None, dict[str, Any]] = None,
                 hold_arguments: Union[None, dict[str, Any]] = None, special_press: tuple = (),
                 visible_check: Callable[[], bool] = utility.passing):
        """
        initialize a button
        :param down_click:
        :param text
        :param down_arguments:
        :param special_press:
        """
        self.draw_func = draw_func
        self.args = tuple(filter(lambda x: x is not None, [colors, data_pack]))

        super().__init__(
            img=None,
            text=text,
            _rect=_rect,
            down_click=down_click,
            up_click=up_click,
            hold_click=hold_click,
            down_arguments=down_arguments,
            up_arguments=up_arguments,
            hold_arguments=hold_arguments,
            special_press=special_press,
            visible_check=visible_check
        )

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draw onto a surface
        :return:
        """
        if not self.visible():
            return
        over = any(
            click is not None for click in self.clicks
        ) and (
            self.keyed or (self.rect is not None and self.rect.collidepoint(mouse_pos))
        )
        new_rect = self.draw_func(onto, over, self.rect.topleft, *self.args)
        if new_rect is not None:
            self.img = onto.subsurface(new_rect)
            self.rect = new_rect


class ButtonHolder(BaseButton):
    """
    holds a list of buttons or button holders
    """

    def get_hover_keyed_text(self) -> Union[str, None]:
        """
        if hover key is inside here, check for text to get it
        :return:
        """
        if self.keyed:
            for button in self.list:
                if button is None:
                    continue
                res = button.get_hover_keyed_text()
                if res is not None:
                    return res
        return None

    @property
    def keyed(self):
        """
        if has been selected by special keyed button selection
        :return:
        """
        return self._keyed

    def set_keyed(self, value: bool = True) -> bool:
        """
        checks if can set as keyed based on children
        :return:
        """
        if not self.visible():
            return False
        if not self.list:
            return False
        for button in self.list:
            if button.set_keyed(value):
                self.keyed = value
                return value
        return False

    def __init__(self, init_list: list[BaseButton] = None, background: Surface = None, _rect: Rect = None,
                 fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = None,
                 outline_color: Union[tuple[int, int, int], None] = None, outline_width: int = 0,
                 visible_check: Callable[[], bool] = utility.passing):
        """
        initializes
        """
        self.list = init_list
        if init_list is None:
            self.list = list()
        self.background = background
        if _rect is None and self.background is not None:
            _rect = self.background.get_rect()
        super().__init__(_rect, visible_check)
        if fill_color is None:
            fill_color = (0, 0, 0, 0)
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.keyed = False

    def convert(self):
        if self.background is not None:
            self.background.convert()
        for button in self.list:
            button.convert()

    def adjust_mouse_pos(self, mouse_pos: tuple[int, int]) -> tuple[int, int]:
        """
        adjust mouse position passed based on the holder's rect
        :param mouse_pos:
        :return:
        """
        if self.rect is not None:
            return mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y
        return mouse_pos

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draws onto a surface
        :param onto:
        :param mouse_pos:
        :return:
        """
        if not self.visible():
            return
        mouse_pos = self.adjust_mouse_pos(mouse_pos)
        if self.background is None:
            if self.rect is not None:
                onto = onto.subsurface(onto.get_rect().clip(self.rect))
            for button in self.list:
                if button is None:
                    continue
                button.render_onto(onto, mouse_pos)
        else:
            self.background.fill(self.fill_color)
            for button in self.list:
                if button is None:
                    continue
                button.render_onto(self.background, mouse_pos)
            onto.blit(self.background, self.rect)
            if self.outline_width > 0:
                rect(
                    onto,
                    self.outline_color,
                    self.rect.inflate(2 * self.outline_width, 2 * self.outline_width),
                    width=self.outline_width
                )

    def fit_size(self, margin: int = 0):
        self.fit_y(margin)
        self.fit_x(margin)

    def fit_y(self, margin: int = 0):
        buttons: list[game_structures.BaseButton] = list(filter(
            lambda b: b is not None and b.rect is not None, self.list
        ))
        if buttons:
            min_y: int = min(buttons, key=lambda button: button.rect.top).rect.top
            for button in buttons:
                button.rect.top += margin - min_y
            self.rect.top += min_y - margin
            max_y: int = max(buttons, key=lambda button: button.rect.bottom).rect.bottom + margin
        else:
            max_y: int = margin * 2
        self.rect.height = max_y

    def fit_x(self, margin: int = 0):
        buttons = list(filter(
            lambda b: b is not None and b.rect is not None, self.list
        ))
        if buttons:
            min_x = min(buttons, key=lambda button: button.rect.left).rect.left
            for button in buttons:
                button.rect.left += margin - min_x
            self.rect.left += min_x - margin
            max_x = max(buttons, key=lambda button: button.rect.right).rect.right + margin
        else:
            max_x = margin * 2
        self.rect.width = max_x

    def do_click(self, mouse_pos: tuple[int, int], click_type) -> bool:
        """
        checks if mouse is on the button when mouse button is pressed, and if so, recursively
        :return:
        """
        if not self.visible():
            return False
        if self.rect is not None and not self.rect.collidepoint(mouse_pos):
            return False
        mouse_pos = self.adjust_mouse_pos(mouse_pos)
        for button in self.list:
            if button is None:
                continue
            if button.do_click(mouse_pos, click_type):
                return True
        return False

    def do_key(self, click_type) -> bool:
        """
        presses special action key for keyed action selection (not special key press)
        :return:
        """
        if not self.visible():
            return False
        if not self.keyed:
            return False
        for button in self.list:
            if button is None:
                continue
            if button.do_key(click_type):
                return True
        return True

    def special_key_click(self, key) -> bool:
        """
        passes key press down the line
        :param key:
        :return:
        """
        if not self.visible():
            return False
        res = False
        for button in self.list:
            if button is None:
                continue
            res = res or button.special_key_click(key)
        return res

    def iter_key(self) -> int:
        """
        if keyed, push what
        :return:
        0 = continue
        1 = stop and push to next
        2 = stop without pushing
        """
        if not self.keyed:
            return 0
        res = 0
        if self.visible():
            for button in self.list:
                if button is None:
                    continue
                if res == 0:
                    res = button.iter_key()
                if res == 1:
                    if button.set_keyed():
                        return 2
                if res == 2:
                    return 2
            return res
        else:
            for button in self.list:
                if button is None:
                    continue
                if button.keyed:
                    button.set_keyed(False)
                return 0
            return 0

    @keyed.setter
    def keyed(self, value):
        self._keyed = value

    def add_button(self, button: BaseButton):
        """
        adds a button to the list
        :param button:
        :return:
        """
        self.list.append(button)

    def __getitem__(self, index):
        return self.list[index]

    def __setitem__(self, index, value):
        if isinstance(self.list[index], ButtonHolder):
            keyed = self.list[index].keyed
        else:
            keyed = False
        self.list[index] = value
        if keyed:
            self.list[index].set_keyed()

    def __setslice__(self, i, j, sequence):
        self.list[i:j] = sequence

    def __delitem__(self, index):
        del self.list[index]

    def __delslice__(self, i, j):
        del self.list[i:j]

    def clear(self):
        """
        clears list
        :return:
        """
        self.list.clear()

    def remove(self, value):
        """
        remove a value from the list
        :param value: button
        :return:
        """
        self.list.remove(value)

    def __len__(self):
        return len(self.list)

    def __contains__(self, item):
        for button in self.list:
            if button is item:
                return True
            if button is None:
                continue
            if isinstance(item, self.__class__) and item in button:
                return True
        return False

    def __iter__(self):
        return self.list.__iter__()

    def __repr__(self):
        return f"{self.__class__.__name__}[rect:{self.rect}, list:{self.list}]"


class ScrollableButtonHolder(ButtonHolder):
    """
    holds a list of buttons or button holders
    """

    def __init__(
            self,
            window_rect: Rect,
            background: Surface = None,
            scrollable_x: bool = True,
            scrollable_y: bool = True,
            start_x: int = 0,
            start_y: int = 0,
            step: int = 1,
            init_list: list[BaseButton] = None,
            fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = default_background,
            outline_color: Union[tuple[int, int, int], None] = default_text_color,
            outline_width: int = 0,
            visible_check: Callable[[], bool] = utility.passing
    ):
        """
        initializes
        """

        self.scrollable = [scrollable_x, scrollable_y]

        def make_scroll_button(button: Button, direction: int) -> Button:
            """
            makes a button a scroll button
            :param button: the button to modify
            :param direction: 0 = x, 1 = y
            :return: modified button object
            """

            visible_cache = [0, 0]

            def determine_pos_and_dimensions() -> tuple[int, int, int, int]:
                length = visible_cache[0] ** 2 // visible_cache[1]
                pos: list[int] = [self.rect.width - 20, self.rect.height - 20]
                dimensions: list[int] = [20, 20]
                dimensions[direction] = length
                pos[direction] = ((self.rect.size[direction]) * self.clip_rect.topleft[direction]) / self.base_rect.size[
                    direction]
                return pos[0], pos[1], dimensions[0], dimensions[1]

            def scroll_visible():
                if not (self.scrollable[direction] and self.clip_rect.size[direction] < self.base_rect.size[direction]):
                    return False
                visible_cache[0] = self.clip_rect.size[direction]
                visible_cache[1] = self.base_rect.size[direction]
                button.rect = pygame.rect.Rect(*determine_pos_and_dimensions())
                button.img = pygame.surface.Surface(button.rect.size)
                return True

            def change_pos(mouse_pos: tuple[int, int]):
                pos = list(self.clip_rect.topleft)
                new_pos = (mouse_pos[direction] - button.rect.size[direction] // 2) * self.base_rect.size[direction] // (self.rect.size[direction])
                pos[direction] = min(max(new_pos, 0), self.base_rect.size[direction] - self.rect.size[direction])
                self.clip_rect.topleft = tuple(pos)

            holding = False

            def do_click(mouse_pos: tuple[int, int], click_type) -> bool:
                """
                specialized check for scroll wheel to check if the mouse is in channel for the window
                :return:
                """
                nonlocal holding
                if button.rect is None:
                    return False
                if not scroll_visible():
                    return False
                if click_type == Button.ClickTypes.down:
                    holding = 0 < self.rect.size[1 - direction] - mouse_pos[1 - direction] < 30
                elif click_type == Button.ClickTypes.up:
                    holding = False
                if holding:
                    return button.run_click(Button.ClickTypes.hold, mouse_pos)
                return False
            button.visible = scroll_visible

            button.do_click = do_click

            button.clicks = [
                utility.passing,
                utility.passing,
                change_pos
            ]

            button.arguments = [
                None,
                None,
                {Button.SpecialArguments.mouse_pos.value: None}
            ]

            return button

        self.scrolls = [
            make_scroll_button(Button(
                pygame.Surface((0, 0)),
                "scroll horizontal",
                pygame.Rect(0, 0, 0, 0),
                fill_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                outline_width=5,
                scale_factor=1
            ), 0),
            make_scroll_button(Button(
                pygame.Surface((0, 0)),
                "scroll vertical",
                pygame.Rect(0, 0, 0, 0),
                fill_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                outline_width=5,
                scale_factor=1
            ), 1)
        ]

        if background is None:
            background = pygame.Surface((0, 0))

        super().__init__(init_list, background, window_rect, fill_color, outline_color, outline_width,
                         visible_check=visible_check)

        self.base_rect = self.background.get_rect()

        self.clip_rect = self.rect.copy()

        self.fit_size()

        self.step = step

        self.x = start_x
        self.y = start_y

    def change_window(self, pos: tuple[int, int] = None, size: tuple[int, int] = None):
        if pos is not None:
            self.rect.topleft = pos
        if size is not None:
            self.rect.size = size
            self.clip_rect.size = size
            self.clip_rect.bottomright = (
                min(self.clip_rect.right, self.rect.width),
                min(self.clip_rect.bottom, self.rect.height)
            )

    def convert(self):
        super().convert()
        for s in self.scrolls:
            s.convert()

    @property
    def x(self):
        return self.clip_rect.x

    @x.setter
    def x(self, value):
        self.clip_rect.x = max(min(value, self.base_rect.width - self.rect.width), 0)

    @property
    def y(self):
        return self.clip_rect.y

    @y.setter
    def y(self, value):
        self.clip_rect.y = max(min(value, self.base_rect.height - self.rect.height), 0)

    def fit_size(self, margin: int = 0):
        self.fit_y(margin)
        self.fit_x(margin)

    def change_background_size(self, size: tuple[int, int]):
        self.background = pygame.Surface(
            size,
            self.background.get_flags(),
            masks=self.background.get_masks()
        )
        self.base_rect.size = self.background.get_size()
        self.clip_rect.bottomright = (
            min(self.clip_rect.right, size[0]),
            min(self.clip_rect.bottom, size[1])
        )

    def fit_y(self, margin: int = 0):
        buttons: list[game_structures.BaseButton] = list(filter(lambda b: b is not None, self.list))
        if buttons:
            min_y: int = min(buttons, key=lambda button: button.rect.top).rect.top
            for button in buttons:
                button.rect.top -= min_y
                button.rect.top += margin
            max_y: int = max(max(buttons, key=lambda button: button.rect.bottom).rect.bottom + margin, self.clip_rect.height)
        else:
            max_y: int = self.clip_rect.height
        self.change_background_size((self.background.get_width(), max_y))

    def fit_x(self, margin: int = 0):
        buttons = list(filter(lambda b: b is not None, self.list))
        if buttons:
            min_x = min(buttons, key=lambda button: button.rect.left).rect.left
            for button in buttons:
                button.rect.left -= min_x
                button.rect.left += margin
            max_x = max(max(buttons, key=lambda button: button.rect.right).rect.right + margin, self.clip_rect.width)
        else:
            max_x = self.clip_rect.width
        self.change_background_size((max_x, self.background.get_height()))

    def adjust_mouse_pos(self, mouse_pos: tuple[int, int]) -> tuple[int, int]:
        """
        adjust mouse position passed based on the holder's rect
        :param mouse_pos:
        :return:
        """
        return mouse_pos[0] - self.rect.x + self.x, mouse_pos[1] - self.rect.y + self.y

    def do_click(self, mouse_pos: tuple[int, int], click_type) -> bool:
        """
        checks if mouse is on the button when mouse button is pressed, and if so, recursively
        :return:
        """
        if not self.visible():
            return False
        clip_mouse_pos = (mouse_pos[0] - self.rect.left, mouse_pos[1] - self.rect.top)
        for scroll in self.scrolls:
            if scroll.do_click(clip_mouse_pos, click_type):
                return True
        interior_mouse_pos = self.adjust_mouse_pos(mouse_pos)
        if self.rect is not None and not self.rect.collidepoint(mouse_pos):
            return False
        for button in self.list:
            if button is None or not (button.rect is not None and button.rect.colliderect(self.clip_rect)):
                continue
            if button.do_click(interior_mouse_pos, click_type):
                return True
        return False

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draws onto a surface
        :param onto:
        :param mouse_pos:
        :return:
        """
        if not self.visible():
            return
        inside_mouse_pos = self.adjust_mouse_pos(mouse_pos)
        on_mouse_pos = (mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y)
        self.background.fill(self.fill_color, self.clip_rect)
        for button in self.list:
            if button is None or not button.rect.colliderect(self.clip_rect):
                continue
            button.render_onto(self.background, inside_mouse_pos)
        window = self.background.subsurface(self.clip_rect)
        for scroll in self.scrolls:
            scroll.render_onto(window, on_mouse_pos)
        onto.blit(window, self.rect)
        if self.outline_width > 0:
            rect(
                onto,
                self.outline_color,
                self.rect.inflate(2 * self.outline_width, 2 * self.outline_width),
                width=self.outline_width
            )

    def __repr__(self):
        return f"{self.__class__.__name__}[rect: {self.rect}, clip: {self.clip_rect}, list: {self.list}]"


class ListHolder(ScrollableButtonHolder):
    """
    a ScrollableButtonHolder, except it also enforces an x position, spacing between elements, and window size.
    requires all buttons to have a rect
    """

    def __init__(
            self,
            window_rect: Rect,
            x_pos: int,
            y_separation: int,
            min_window_length: int,
            max_window_length: int,
            start_x: int = 0,
            start_y: int = 0,
            step: int = 1,
            init_list: list[BaseButton] = None,
            fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = default_background,
            outline_color: Union[tuple[int, int, int], None] = default_text_color,
            outline_width: int = 0,
            visible_check: Callable[[], bool] = utility.passing
    ):
        """
        initializes
        """
        self.__x_pos = x_pos
        self.__y_sep = y_separation
        self.__snap_window_length = lambda y: min(max(y, min_window_length), max_window_length)
        self.__last_y = 0
        super().__init__(
            window_rect,
            None,
            False,
            True,
            start_x,
            start_y,
            step,
            init_list,
            fill_color,
            outline_color,
            outline_width,
            visible_check
        )
        self.fix_list()

    def fix_list(self):
        y: int = self.__y_sep
        i: int = 0
        while i < len(self.list):
            button = self.list[i]
            i += 1
            if not button.visible():
                continue
            button.rect.topleft = (self.__x_pos, y)
            y = button.rect.bottom + self.__y_sep
        if y != self.__last_y:
            self.__last_y = y
            snapped = self.__snap_window_length(y)
            if snapped > y:
                y = snapped
            self.rect.height = self.clip_rect.height = snapped
            self.change_background_size((self.rect.width, y))

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        self.fix_list()
        super().render_onto(onto, mouse_pos)


class HorizontalListHolder(ScrollableButtonHolder):
    """
    a ScrollableButtonHolder, except it also enforces an x position, spacing between elements, and window size.
    requires all buttons to have a rect
    """

    def __init__(
            self,
            window_rect: Rect,
            y_pos: int,
            x_separation: int,
            min_window_length: int,
            max_window_length: int,
            start_x: int = 0,
            start_y: int = 0,
            step: int = 1,
            init_list: list[BaseButton] = None,
            fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = default_background,
            outline_color: Union[tuple[int, int, int], None] = default_text_color,
            outline_width: int = 0,
            visible_check: Callable[[], bool] = utility.passing
    ):
        """
        initializes
        """
        self.__y_pos = y_pos
        self.__x_sep = x_separation
        self.__snap_window_length = lambda x: min(max(x, min_window_length), max_window_length)
        self.__last_x = 0
        super().__init__(
            window_rect,
            None,
            True,
            False,
            start_x,
            start_y,
            step,
            init_list,
            fill_color,
            outline_color,
            outline_width,
            visible_check
        )
        self.fix_list()

    def fix_list(self):
        x: int = self.__x_sep
        i: int = 0
        while i < len(self.list):
            button = self.list[i]
            i += 1
            if not button.visible():
                continue
            button.rect.topleft = (x, self.__y_pos)
            x = button.rect.right + self.__x_sep
        if x != self.__last_x:
            self.__last_x = x
            snapped = self.__snap_window_length(x)
            if snapped > x:
                x = snapped
            self.rect.width = self.clip_rect.width = snapped
            self.change_background_size((x, self.rect.height))

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        self.fix_list()
        super().render_onto(onto, mouse_pos)


class SwitchHolder(ButtonHolder):
    """
    a button holder that has multiple sets of buttons to switch between
    """

    @property
    def view(self):
        return self.__view

    @view.setter
    def view(self, val: int):
        if val < 0:
            val = len(self._views) + val
        self._views[self.__view] = self.list
        self.__view = val
        self.list = self._views[val]

    def add_view(self, val: list[BaseButton] = None):
        if val is None:
            val = []
        self._views.append(val)

    def __init__(self, start_view: int, init_lists: list[list[BaseButton]] = None, background: Surface = None, _rect: Rect = None,
                 fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = None,
                 outline_color: Union[tuple[int, int, int], None] = None, outline_width: int = 0,
                 visible_check: Callable[[], bool] = utility.passing):
        if init_lists is None:
            init_lists = [[]]
        self._views = init_lists
        self.__view = start_view
        super().__init__(self._views[self.__view], background, _rect, fill_color, outline_color, outline_width, visible_check)


class PassThroughSwitchHolder(BaseButton):
    """
    a button holder that has multiple buttons to switch between.  Like SwitchHolder but only one button per view, which allows for some
    """

    def do_key(self, click_type) -> bool:
        return self.on.do_key(click_type)

    def iter_key(self) -> int:
        return self.on.iter_key()

    @property
    def keyed(self) -> bool:
        return self.on.keyed

    def set_keyed(self, value: bool = True) -> bool:
        return self.on.set_keyed()

    def get_hover_keyed_text(self) -> Union[str, None]:
        return self.on.get_hover_keyed_text()

    def convert(self):
        for button in self._views:
            button.convert()

    def do_click(self, mouse_pos: tuple[int, int], click_type) -> bool:
        return self.visible() and self.on.do_click(mouse_pos, click_type)

    @property
    def view(self):
        return self.__view

    @view.setter
    def view(self, val: int):
        if val < 0:
            val = len(self._views) + val
        self._views[self.__view] = self.on
        self.__view = val
        self.on = self._views[val]

    def add_view(self, val: BaseButton = None):
        if val is None:
            val = []
        self._views.append(val)

    def __init__(self, start_view: int, init_list: list[BaseButton],
                 visible_check: Callable[[], bool] = utility.passing):
        self._views = init_list
        self.on = init_list[start_view]
        self.__view = start_view
        super().__init__(self.on.rect, visible_check)

    @property
    def rect(self):
        return self.on.rect

    @rect.setter
    def rect(self, val: pygame.rect.Rect):
        self.on.rect = val

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        if self.visible():
            self.on.render_onto(onto, mouse_pos)
