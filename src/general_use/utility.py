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
"""
import enum
import math
import os
import threading
from typing import Callable, Any, Union, Hashable
import traceback
import logging
import functools
from sys import argv
import pygame


def from_camel(string: str):
    return ''.join([char if char.islower() else ' ' + char for char in string])[1:]


import cProfile
import atexit
import pstats


__output_lock = threading.Lock()


def profile_func(func: Callable):
    profile = cProfile.Profile()
    profile.disable()

    def inner(*args, **kwargs):
        with profile:
            return func(*args, **kwargs)

    def output():
        profile.create_stats()
        stats = pstats.Stats(profile)
        stats.sort_stats("cumulative")
        with __output_lock:
            print(f"{func.__name__} profile:")
            stats.print_stats()

    atexit.register(output)

    return inner


memoize_not_have = object()


def memoize(func: Callable = None, /, *, guarantee_single: bool = False, guarantee_natural: bool = False):
    """
    if the function has previously been invoked with the same (hashable) arguments, make it work
    :param func:
    :param guarantee_single: guarantee that there will only ever be 1 argument passed
    :param guarantee_natural: guarantee that there will only ever be natural numbers passed
    :return:
    """

    determine = (guarantee_single, guarantee_natural)

    def inner_make(true_func: Callable):

        if determine == (True, True):
            cache = []

            def internal(num):
                if num < len(cache):
                    res = cache[num]
                    if res is memoize_not_have:
                        res = true_func(num)
                        cache[num] = res
                    return res
                else:
                    res = true_func(num)
                    cache.extend([memoize_not_have] * (num - len(cache)) + [res])
                return res

        elif determine == (True, False):

            cache = dict()

            def internal(arg):

                if isinstance(arg, Hashable):
                    res = cache.get(arg, memoize_not_have)
                    if res is memoize_not_have:
                        res = true_func(arg)
                        cache[arg] = res
                else:
                    res = true_func(arg)
                return res

        else:
            internal = functools.cache(true_func)

        return internal

    if func is None:
        return inner_make
    return inner_make(func)


@memoize(guarantee_single=True)
def make_simple_always(result: Any) -> Callable:
    """
    makes a simple function that regardless of input produces the same output
    :param result: what output it makes
    :return: lambda function
    """
    return lambda *args, **kwargs: result


class OutlineTypes(enum.Enum):
    Block = lambda check, width: True
    Circle = lambda check, width: math.sqrt(check[0] ** 2 + check[1] ** 2) <= width
    Manhattan = lambda check, width: check[0] + check[1] <= width


def outline_img(img: pygame.Surface, outline: int, outline_type: OutlineTypes | Callable[[tuple[int, int], int], bool] = OutlineTypes.Block):
    width: int = img.get_width()
    height: int = img.get_height()
    outlining_width: int = width + 2 * outline
    outlining_height: int = height + 2 * outline
    outlining: pygame.Surface = pygame.Surface((
        outlining_width, outlining_height
    ), pygame.SRCALPHA)
    coord: int
    if isinstance(outline_type, OutlineTypes):
        outline_type = outline_type.value
    # checks = tuple(
    #     (ox, oy)
    #     for ox in range(-outline, outline + 1)
    #     for oy in range(-outline, outline + 1)
    #     if ox != 0 or oy != 0
    #     and outline_type((ox, oy), outline)
    # )
    outlining.blits(
        blit_sequence=list(
            (img, (outline + ox, outline + oy))
            for ox in range(-outline, outline + 1)
            for oy in range(-outline, outline + 1)
            if ox != 0 or oy != 0
            and outline_type((ox, oy), outline)
        ),
        doreturn=False
    )
    # for x_offset, y_offset in checks:
    #     outlining.blit(img, (outline + x_offset, outline + y_offset))
    outlining.fill(
        (0, 0, 0, 0),
        special_flags=pygame.BLEND_RGB_MIN
    )
    outlining.blit(img, (outline, outline))
    # for coord in range((width + 2 * outline) * (height + 2 * outline)):
    #     x: int = (coord % (width + 2 * outline) + outline)
    #     y: int = (coord // (width + 2 * outline) + outline)
    #     offset_x: int
    #     offset_y: int
    #     if outlining.get_at((x, y)).r == 0 or outlining.get_at((x, y)).a == 0:
    #         if any(
    #                 outlining.get_at((x + offset_x, y + offset_y)).r == 255
    #                 and outlining.get_at((x + offset_x, y + offset_y)).a == 255
    #                 for offset_x, offset_y in checks
    #                 if 0 <= x + offset_x < outlining_width and 0 <= y + offset_y < outlining_height
    #         ):
    #             outlining.set_at((x, y), (0, 0, 0, 255))
    #         else:
    #             outlining.set_at((x, y), (0, 0, 0, 0))
    return outlining


"""
simple to put for anything, does nothing.  Use for objects without a tick effect
also now used for just anything that needs to provide a useless function
:return: True, for use in the tick function
"""
passing = make_simple_always(True)


class ThreadWithResult(threading.Thread):

    @property
    def result(self):
        if not self.__finished:
            threading.Thread.join(self)
        return self.__result

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, daemon=False, log_errors=True):
        if kwargs is None:
            kwargs = dict()
        threading.Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)
        self.__result = None
        self.__finished = False
        self.log = log_errors

    def run(self):
        if self._target is None:
            return
        try:
            self.__result = self._target(*self._args, **self._kwargs)
        except Exception as exc:
            if self.log:
                log_error(exc)

    def join(self, *args):
        super(ThreadWithResult, self).join(*args)
        return self.__result


def make_async(
        *args, with_lock: Union[threading.Lock, bool] = None, singular: bool = False, daemon: bool = False,
        log_errors: bool = True
) -> Callable:
    """
    makes a function asynchronous
    :param with_lock: if multiple calls of the function can't overlap
    :param singular: if there can only be one call of the function active at a time
    :param daemon: if the thread should be a daemon thread
    :param log_errors: whether or not to log errors
    :return:
    """

    if with_lock and singular:
        raise ValueError("An asynchronous function cannot both have a lock and be singular")

    def inner_make_async(func: Callable):
        nonlocal with_lock

        if singular:

            lock = threading.Lock()

            def res_func(*args, **kwargs):
                if lock.locked():
                    return
                with lock:
                    func(*args, **kwargs)

        elif with_lock:
            if with_lock is True:
                with_lock = threading.Lock()

            def res_func(*args, **kwargs):
                with with_lock:
                    func(*args, **kwargs)
        else:
            res_func = func

        def async_func(*args, **kwargs) -> threading.Thread:
            thread = ThreadWithResult(target=res_func, args=args, kwargs=kwargs, daemon=daemon, log_errors=log_errors)
            thread.start()
            return thread

        return async_func

    if len(args) == 1:
        return inner_make_async(args[0])

    return inner_make_async


from general_use import game_structures
import pygame
from data import game_states


admin = game_states.ADMIN


def add_error_checking(
        func: Callable,
        message: str = "Error occurred during execution!  Details added to log.",
        *callback_args,
        callback_error_fn: Callable = None,
        callback_done_fn: Callable = None,
        callback_finally_fn: Callable = None,
) -> Callable:
    """
    adds error handling to a callable
    :param func:
    :param message: error message
    :param callback_args: arguments passed to callback errors, if any
    :param callback_error_fn: gjkawjhh idk callback stuff
    :param callback_done_fn: callback if finished successfully
    :param callback_finally_fn: callback for end, no matter what
    :return:
    """

    def error_wrap(*args, **kwargs) -> Any:
        """
        interior try/except wrap
        :param args:
        :param kwargs:
        :return:
        """
        try:
            res = func(*args, **kwargs)
            if callback_done_fn is not None:
                callback_done_fn(*callback_args)
        except Exception as exc:
            res = None
            log_error(exc)
            game_structures.ALERTS.add_alert(message)
            if callback_error_fn is not None:
                callback_error_fn(*callback_args)
        finally:
            if callback_finally_fn is not None:
                callback_finally_fn(*callback_args)
        return res

    return error_wrap


logger_on = False


def log_error(exc: Exception) -> None:
    """
    logs an error.  Requires there to be an error.
    :return:
    """
    global logger_on

    if not logger_on:
        logger_on = True
        logging.basicConfig(filename="./errors.log", format='%(asctime)s\n%(message)s', filemode='a')
    message = "".join(traceback.format_exception(exc))
    if not admin:
        root = os.getcwd()
        message = message.replace(root, "DownTheLine:")
    logging.error(message)


def make_reserved_audio_channel() -> pygame.mixer.Channel:
    """
    makes an audio channel to return.  Also, reserves all audio channels.
    :return:
    """
    channels = pygame.mixer.get_num_channels()
    pygame.mixer.set_num_channels(channels + 1)
    pygame.mixer.set_reserved(channels + 1)
    return pygame.mixer.Channel(channels)


button_hover_keyed = False
special_key = pygame.K_RETURN


keyed_down = False
mouse_down = False


def tick() -> None:
    global button_hover_keyed, keyed_down, mouse_down
    """
    function that handles game clock and frame rate
    also handles some other actions that need to happen every frame
    :return: noting
    """
    mouse_pos = pygame.mouse.get_pos()
    if game_structures.TRUE_SCREEN is not None:
        factor = game_states.HEIGHT / game_structures.TRUE_HEIGHT
        mouse_pos = (mouse_pos[0] * factor, mouse_pos[1] * factor)
    game_structures.BUTTONS.render_onto(game_structures.SCREEN, mouse_pos)
    alert_img = game_structures.ALERTS.tick()
    if alert_img is not None:
        game_structures.SCREEN.blit(
            alert_img,
            (game_states.WIDTH // 2 - game_structures.ALERTS.width // 2, 0)
        )

    if keyed_down:
        if pygame.key.get_pressed()[special_key]:
            game_structures.BUTTONS.do_key(game_structures.Button.ClickTypes.hold)
        else:
            game_structures.BUTTONS.do_key(game_structures.Button.ClickTypes.up)
            keyed_down = False

    if mouse_down:
        pos = pygame.mouse.get_pos()
        if game_structures.TRUE_SCREEN is not None:
            factor = game_states.HEIGHT / game_structures.TRUE_HEIGHT
            pos = (pos[0] * factor, pos[1] * factor)
        if pygame.mouse.get_pressed()[0]:
            game_structures.BUTTONS.do_click(pos, game_structures.Button.ClickTypes.hold)
        else:
            game_structures.BUTTONS.do_click(pos, game_structures.Button.ClickTypes.up)
            mouse_down = False

    for event in pygame.event.get():
        event_handled = False
        if event.type == pygame.QUIT:
            game_states.RUNNING = False
            event_handled = True
        elif event.type == pygame.KEYDOWN:
            if game_structures.TYPING.typing:
                event_handled = True
                if event.key == pygame.K_RETURN:
                    game_structures.TYPING.text += "\n"
                elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                    if game_structures.TYPING.text != "":
                        game_structures.TYPING.text = game_structures.TYPING.text[:-1]
                else:
                    game_structures.TYPING.text += event.unicode
                    # print(event.key, event.mod, pygame.KMOD_CTRL)
            else:
                if event.key == pygame.K_TAB:
                    event_handled = True
                    if button_hover_keyed:
                        res = game_structures.BUTTONS.iter_key()
                        if res == 1:
                            button_hover_keyed = False
                        elif res == 0:
                            game_structures.BUTTONS.set_keyed()
                    else:
                        game_structures.BUTTONS.set_keyed()
                        button_hover_keyed = True
                    if button_hover_keyed:
                        game_structures.ALERTS.speak.add(game_structures.BUTTONS.get_hover_keyed_text())
                if event.key == special_key and not keyed_down and game_structures.BUTTONS.keyed:
                    event_handled = True
                    keyed_down = True
                    game_structures.BUTTONS.do_key(game_structures.Button.ClickTypes.down)
                game_structures.BUTTONS.special_key_click(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_down = True
                pos = event.pos
                if game_structures.TRUE_SCREEN is not None:
                    factor = game_states.HEIGHT / game_structures.TRUE_HEIGHT
                    pos = (pos[0] * factor, pos[1] * factor)
                event_handled = game_structures.BUTTONS.do_click(pos, game_structures.Button.ClickTypes.down)
        if not event_handled:
            for catcher in game_structures.CUSTOM_EVENT_CATCHERS:
                if catcher(event):
                    break

    game_structures.display_screen()
    game_structures.CLOCK.tick(60)
