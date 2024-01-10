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


from abc import ABC, abstractmethod
from typing import Union, Callable, Any


import pygame
from pygame import Rect, Surface, SRCALPHA
from pygame.transform import scale
from pygame.draw import rect

import utility
import game_structures


class ButtonHolderTemplate(ABC):
    """
    buttonholder abstract class
    """

    @abstractmethod
    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draw onto a surface
        :return:
        """

    @abstractmethod
    def do_click(self, mouse_pos: tuple[int, int]) -> bool:
        """
        checks if mouse is on the button, and if so, recursively
        :return: whether or not to stop the check
        """

    @abstractmethod
    def do_key(self) -> bool:
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
    def set_keyed(self) -> bool:
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

    fonts = game_structures.FONTS

    @staticmethod
    def draw_text(
            text: str,
            font: int | pygame.font.Font,
            background_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = (255, 255, 255, 255),
            outline_color: tuple[int, int, int] = (0, 0, 0),
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
        lines = [""]
        word = ""
        words = 0
        if isinstance(font, int):
            draw_font = ButtonHolder.fonts[font]
        else:
            draw_font = font
        for char in text + " ":
            if char == "\n":
                if word != "":
                    if lines[-1] == "":
                        lines[-1] = word
                    else:
                        lines[-1] += " " + word
                    word = ""
                if len(lines) == max_lines:
                    if draw_font.size(lines[-1] + "...")[0] > max_line_pixels:
                        backstep = -1
                        while draw_font.size(lines[-1][:backstep] + "...")[0] > max_line_pixels:
                            backstep -= 1
                            if backstep >= len(lines[-1]):
                                break
                        lines[-1] = lines[-1][:backstep] + "..."
                    else:
                        lines[-1] += "..."
                    break
                else:
                    lines.append("")
                words = 0
            elif char == " ":
                if lines[-1] == "":
                    lines[-1] = word
                elif preserve_words and max_line_pixels > 0:
                    if lines[-1] == "":
                        length = draw_font.size(word)
                    else:
                        length = draw_font.size(lines[-1] + " " + word)[0]
                    if length > max_line_pixels:
                        if len(lines) == max_lines:
                            if draw_font.size(lines[-1] + "...")[0] > max_line_pixels:
                                backstep = -1
                                while draw_font.size(lines[-1][:backstep] + "...")[0] > max_line_pixels:
                                    backstep -= 1
                                    if backstep >= len(lines[-1]):
                                        break
                                lines[-1] = lines[-1][:backstep] + "..."
                            else:
                                lines[-1] += "..."
                            break
                        else:
                            lines.append(word)
                        words = 0
                    else:
                        if lines[-1] == "":
                            lines[-1] = word
                        else:
                            lines[-1] += " " + word
                else:
                    if lines[-1] == "":
                        lines[-1] = word
                    else:
                        lines[-1] += " " + word
                word = ""
                words += 1
                if words >= max_line_words > 0:
                    words = 0
                    if len(lines) == max_lines:
                        if draw_font.size(lines[-1] + "...")[0] > max_line_pixels:
                            backstep = -1
                            while draw_font.size(lines[-1][:backstep] + "...")[0] > max_line_pixels:
                                backstep -= 1
                                if backstep >= len(lines[-1]):
                                    break
                            lines[-1] = lines[-1][:backstep] + "..."
                        else:
                            lines[-1] += "..."
                        break
                    else:
                        lines.append("")
            else:
                if max_line_pixels > 0:
                    if lines[-1] == "":
                        length = draw_font.size(word + char)[0]
                    else:
                        length = draw_font.size(lines[-1] + " " + word + char)[0]
                    if length > max_line_pixels:
                        if len(lines) == max_lines:
                            if lines[-1] == "":
                                lines[-1] = word
                            else:
                                lines[-1] += " " + word
                            if draw_font.size(lines[-1] + "...")[0] > max_line_pixels:
                                backstep = -1
                                while draw_font.size(lines[-1][:backstep] + "...")[0] > max_line_pixels:
                                    backstep -= 1
                                    if backstep >= len(lines[-1]):
                                        break
                                lines[-1] = lines[-1][:backstep] + "..."
                            else:
                                lines[-1] += "..."
                            break
                        else:
                            if not preserve_words:
                                lines[-1] += word
                                word = ""
                            lines.append("")
                        words = 0
                word += char
        if max_width > 0:
            max_length = 0
            for line in lines:
                max_length = max(max_length, draw_font.size(line)[0])
            if max_length > max_width:
                draw_font = ButtonHolder.fonts[font * max_width / max_length]
        if enforce_width == 0:
            max_length = 0
            for i in range(len(lines)):
                lines[i] = draw_font.render(lines[i], True, outline_color, None)
                max_length = max(max_length, lines[i].get_width())
        else:
            max_length = enforce_width
            for i in range(len(lines)):
                lines[i] = draw_font.render(lines[i], True, outline_color, None)
        linesize = draw_font.get_linesize()
        text_surface = Surface((max_length, linesize * len(lines)), SRCALPHA)
        if background_color is not None:
            text_surface.fill(background_color)
        for i in range(len(lines)):
            text_surface.blit(lines[i], (text_align * (max_length - lines[i].get_width()), i * linesize))
        return text_surface


Button = object()


class Button(ButtonHolderTemplate):
    """
    dataclass containing information for a button
    """

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

    def set_keyed(self) -> bool:
        """
        sets the button as keyed
        :return:
        """
        self.keyed = True
        return True

    def __init__(
            self,
            click: Union[None, Callable],
            img: Surface,
            text: str,
            _rect: Rect,
            fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = None,
            outline_color: Union[tuple[int, int, int], None] = None,
            inflate_center: tuple[float, float] = (0.5, 0.5),
            outline_width: int = 1,
            arguments: Union[None, dict[str, Any]] = None,
            scale_factor: float = 1.25,
            special_press: tuple = (),
            typing_instance: int = None
    ):
        """
        initialize a button
        :param click:
        :param img:
        :param text:
        :param _rect:
        :param fill_color:
        :param outline_color:
        :param inflate_center:
        :param outline_width:
        :param arguments:
        :param scale_factor:
        :param special_press:
        :param typing_instance:
        """
        self.click: Union[None, Callable] = click
        self.img: Surface = img
        self.text: str = text
        self.rect: Rect = _rect
        self.fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = fill_color
        self.outline_color: Union[tuple[int, int, int], None] = outline_color
        self.inflate_center: tuple[float, float] = inflate_center
        self.outline_width: int = outline_width
        self.arguments: Union[None, dict[str, Any]] = arguments
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
        return Button(
            click,
            img,
            button_name,
            Rect(center, (0, 0)) if img is None else img.get_rect(center=center),
            inflate_center=inflate_center,
            arguments=arguments,
            scale_factor=scale_factor,
            special_press=special_press,
            outline_width=0
        )

    @staticmethod
    def make_text_button(
            text: str,
            font: int,
            click: Union[Callable, None],
            center: tuple[int, int],
            background_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = (255, 255, 255, 255),
            outline_color: tuple[int, int, int] = (0, 0, 0),
            border_width: int = 0,
            max_line_pixels: int = 0,
            max_line_words: int = 0,
            max_width: int = 0,
            preserve_words: bool = True,
            text_align: float = 0,
            x_align: float = 0.5,
            y_align: float = 0.5,
            arguments: dict[str, Any] = None,
            special_press: Union[tuple[str], str] = (),
            override_text: str = None,
            max_lines: int = 0,
            enforce_width: int = 0
    ) -> Button:
        """
        creates a button object
        :param text: string
        :param font: size of the font object
        :param click: function called when the button is clicked
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
        return Button(
            click,
            text_surface,
            override_text,
            pygame.Rect(center[0] - x_align * x, center[1] - y_align * y, x, y),
            background_color,
            outline_color,
            (x_align, y_align),
            border_width,
            arguments=arguments,
            special_press=special
        )

    def render_onto(self, onto: Surface, mouse_pos: tuple[int, int]) -> None:
        """
        draw onto a surface
        :return:
        """
        if self.img is None:
            return
        if self.rect is None:
            return
        if self.click is not None and (self.rect.collidepoint(mouse_pos) or self.keyed):
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

    def run_click(self) -> bool:
        """
        runs click event
        :return: if event occurred
        """
        if self.click is None:
            return False
        if self.arguments is None:
            self.click()
        else:
            self.click(**self.arguments)
        return True

    def do_click(self, mouse_pos: tuple[int, int]) -> bool:
        """
        checks if mouse is on the button when mouse button is pressed, and if so, recursively
        :return:
        """
        if self.rect is None:
            return False
        if self.rect.collidepoint(mouse_pos):
            return self.run_click()
        return False

    def do_key(self) -> bool:
        """
        checks if button is keyed, and if so, does click
        :return:
        """
        if self.keyed:
            self.run_click()
        return self.keyed

    def special_key_click(self, key) -> bool:
        """
        ahhhh
        :return:
        """
        if isinstance(self.special_press, int):
            special_pressed = key == self.special_press
        else:
            special_pressed = key in self.special_press
        if special_pressed:
            self.run_click()
        return special_pressed

    def iter_key(self) -> int:
        """
        iterates which button is currently keyed
        :return:
        0 = continue
        1 = stop and push to next
        2 = stop without pushing
        """
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
            others: list[tuple[ButtonHolderTemplate, float, float, int, int]] = (),
            max_line_pixels: int = 0,
            max_width: int = 0,
            y_align: int = 0.5,
            x_align: int = 0.5,
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
        :param y_align: designate where to orient x from
        :param x_align: designate where to orient y from
        :param override_button_name: override the button name if any
        :return: None
        """
        if instance is not None and self.typing_instance != instance:
            return
        new_img = Button.draw_text(new_text, font, max_line_pixels=max_line_pixels, preserve_words=True)
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
            others: list[tuple[Union[ButtonHolderTemplate], float, float, int, int]] = (),
            max_line_pixels: int = 0,
            max_width: int = 0,
            prepend: str = "",
            append: str = "",
            start_text: str = None,
            callback: Callable = None,
            y_align: int = 0.5,
            x_align: int = 0.5,
            search_against: list[str] = ()
    ) -> None:
        """
        edits a button's text, given an index.  Wrapper for interior async function
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
            while game_structures.TYPING.instance == instance.instance and game_structures.game_states.RUNNING:
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


class ButtonHolder(ButtonHolderTemplate):
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

    def set_keyed(self, ) -> bool:
        """
        checks if can set as keyed based on children
        :return:
        """
        if not self.list:
            return False
        for button in self.list:
            if button.set_keyed():
                self.keyed = True
                return True
        return False

    def __init__(
            self,
            init_list: list[ButtonHolderTemplate] = None,
            background: Surface = None,
            _rect: Rect = None,
            fill_color: Union[tuple[int, int, int], tuple[int, int, int, int], None] = None,
            outline_color: Union[tuple[int, int, int], None] = None,
            outline_width: int = 0,
    ):
        """
        initializes
        """
        self.list = init_list
        if self.list is None:
            self.list = list()
        self.background = background
        self.rect = _rect
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.keyed = False

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
        mouse_pos = self.adjust_mouse_pos(mouse_pos)
        if self.background is None:
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

    def do_click(self, mouse_pos: tuple[int, int]) -> bool:
        """
        checks if mouse is on the button when mouse button is pressed, and if so, recursively
        :return:
        """
        mouse_pos = self.adjust_mouse_pos(mouse_pos)
        if self.rect is None:
            click = True
        elif self.rect.collidepoint(mouse_pos):
            click = True
        else:
            return False
        if click:
            for button in self.list:
                if button is None:
                    continue
                if button.do_click(mouse_pos):
                    return True
        return False

    def do_key(self) -> bool:
        """
        presses special action key for keyed action selection (not special key press)
        :return:
        """
        if not self.keyed:
            return False
        for button in self.list:
            if button is None:
                continue
            if button.do_key():
                return True
        return True

    def special_key_click(self, key) -> None:
        """
        passes key press down the line
        :param key:
        :return:
        """
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
        for button in self.list:
            if button is None:
                continue
            match res:
                case 0:
                    res = button.iter_key()
                case 1:
                    if button.set_keyed():
                        return 2
                case 2:
                    return 2
        return res

    @keyed.setter
    def keyed(self, value):
        self._keyed = value

    def add_button(self, button: ButtonHolderTemplate):
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
