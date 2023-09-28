import threading
from typing import Callable, Any, Union
import traceback
import logging
from sys import argv


def make_async(with_lock: Union[threading.Lock, bool] = None) -> Callable:
    """
    makes a function asynchronous
    :param with_lock:
    :return:
    """

    def inner_make_async(func: Callable):
        nonlocal with_lock

        if with_lock is None:
            res_func = func
        else:
            if with_lock is True:
                with_lock = threading.Lock()

            def res_func(*args, **kwargs):
                with_lock.acquire()
                func(*args, **kwargs)
                with_lock.release()

        def async_func(*args, **kwargs) -> threading.Thread:
            thread = threading.Thread(target=res_func, args=args, kwargs=kwargs)
            thread.start()
            return thread

        return async_func

    return inner_make_async


import game_structures
import pygame
import game_states


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


logging.basicConfig(filename="errors.log", format='%(asctime)s\n%(message)s', filemode='a')


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


def tick() -> None:
    global button_hover_keyed
    """
    function that handles game clock and frame rate
    also handles some other actions that need to happen every frame
    :return: noting
    """
    game_structures.BUTTONS.render_onto(game_structures.SCREEN, pygame.mouse.get_pos())
    alert_img = game_structures.ALERTS.tick()
    if alert_img is not None:
        game_structures.SCREEN.blit(
            alert_img,
            (240 * 2 - game_structures.ALERTS.width / 2, 0)
        )
    pygame.display.flip()
    game_structures.CLOCK.tick(60)
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
                        match game_structures.BUTTONS.iter_key():
                            case 1:
                                button_hover_keyed = False
                            case 0:
                                game_structures.BUTTONS.set_keyed()
                    else:
                        game_structures.BUTTONS.set_keyed()
                        button_hover_keyed = True
                    if button_hover_keyed:
                        game_structures.ALERTS.speak.add(game_structures.BUTTONS.get_hover_keyed_text())
                if event.key == pygame.K_RETURN:
                    event_handled = True
                    game_structures.BUTTONS.do_key()
                game_structures.BUTTONS.special_key_click(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                event_handled = game_structures.BUTTONS.do_click(event.pos)
        if not event_handled:
            for catcher in game_structures.CUSTOM_EVENT_CATCHERS:
                if catcher(event):
                    break