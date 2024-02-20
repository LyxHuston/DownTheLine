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

import threading
from typing import Callable, Any, Union, Hashable
import traceback
import logging
from sys import argv

memoize_not_have = object()


def memoize(func: Callable):
    """
    if the function has previously been invoked with the same (hashable) arguments, make it work
    :param func:
    :return:
    """

    cache = dict()

    def internal(*args, **kwargs):

        key = (args, tuple(sorted(kwargs.items())))
        if isinstance(key, Hashable):
            res = cache.get(key, memoize_not_have)
            if res is memoize_not_have:
                res = func(*args, **kwargs)
                cache[key] = res
        else:
            res = func(*args, **kwargs)
        return res

    return internal


@memoize
def make_simple_always(result: Any) -> Callable:
    """
    makes a simple function that regardless of input produces the same output
    :param result: what output it makes
    :return: lambda function
    """
    return lambda *args, **kwargs: result


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
        self.log = True

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

if len(argv) >= 2 and argv[1] == "admin":
    admin = True
else:
    admin = False


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


logging.basicConfig(filename="./errors.log", format='%(asctime)s\n%(message)s', filemode='a')


def log_error(exc: Exception) -> None:
    """
    logs an error.  Requires there to be an error.
    :return:
    """
    stack: traceback.StackSummary = traceback.extract_tb(exc.__traceback__)
    if not admin:
        root = argv[0][:len(argv[0]) - 6].replace("/", "\\")
        for frame in stack:
            if frame.filename.startswith(root):
                frame.filename = frame.filename[len(root):]
            else:
                frame.filename = "<filename outside of program, obscured for privacy>"
    logging.error("".join(traceback.format_exception(exc)))


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
            pygame.quit()
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
                if event.key == special_key and not keyed_down:
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