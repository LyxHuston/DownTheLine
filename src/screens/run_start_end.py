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

starts up a game instance
"""
import dataclasses
import datetime
import enum
import math

from collections import deque
import pygame

from general_use import game_structures
from data import game_states
from run_game import game_areas, gameboard, ingame, tutorials, abilities
import random
import sys
from typing import Type


def visual_distance() -> int:
    # if d is None:
    #     d = game_states.RECORD_DISTANCE
    # return d / 128
    return game_states.RECORD_DISTANCE // 512


def log_area(area: game_areas.GameArea):
    game_states.AREAS_PASSED += 1
    if area.__class__.__name__ in GameAreaLog.areas_dict:
        GameAreaLog.areas_dict[area.__class__.__name__] += 1


PAUSE_BUTTONS = game_structures.ButtonHolder()

MESSAGE_LOG = game_structures.ScrollableButtonHolder(
    pygame.rect.Rect(game_states.WIDTH // 4, 0, game_states.WIDTH // 2 + 40, game_states.HEIGHT),
    None,
    scrollable_x=False,
    fill_color=(0, 0, 0, 255),
    outline_color=(255, 255, 255),
    outline_width=5
)

MESSAGE_LOG_BUTTONS = game_structures.ButtonHolder(
    [None, MESSAGE_LOG]
)

PAUSE_SWITCHER = game_structures.SwitchHolder(
    0,
    [[PAUSE_BUTTONS], [MESSAGE_LOG_BUTTONS]],
    background=None,
    fill_color=(0, 0, 0, 127),
    visible_check=lambda: ingame.paused
)


def switch_to_message_log():
    y = 0
    width = 2 * game_states.WIDTH // 3 + 40
    MESSAGE_LOG.rect = pygame.rect.Rect(0, 0, width, game_states.HEIGHT)
    MESSAGE_LOG.clip_rect = pygame.rect.Rect(0, 0, width, game_states.HEIGHT)
    MESSAGE_LOG.window = pygame.rect.Rect((game_states.WIDTH - width) // 2, 0, width, game_states.HEIGHT)
    MESSAGE_LOG.background = pygame.surface.Surface(
        (width, 0)
    )
    for log in tutorials.LOG:
        button = game_structures.Button.make_text_button(
            log.text,
            log.font,
            (20, y),
            max_line_pixels=width - 40,
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            x_align=0,
            y_align=0,
            border_width=2
        )
        MESSAGE_LOG.add_button(button)
        y += button.img.get_height() + 20
    MESSAGE_LOG.fit_y(20)
    PAUSE_SWITCHER.view = 1


def switch_to_main_pause():
    PAUSE_SWITCHER.view = 0


def quit_run():
    from screens import main_screen
    log_run(RunEndReasons.quit)
    main_screen.main_screen_place.start()


def end():
    for area in game_structures.AREA_QUEUE:
        area.cleanup()
    for entity in gameboard.ENTITY_BOARD:
        entity.cleanup()
    game_structures.BUTTONS.remove(PAUSE_SWITCHER)


def clean_gameboard():
    tutorials.clear_tutorial_text()
    gameboard.heart_data.clear()
    gameboard.ENTITY_BOARD.clear()
    gameboard.NEW_ENTITIES.clear()
    gameboard.PARTICLE_BOARD.clear()
    game_structures.AREA_QUEUE.clear()
    game_structures.NEW_AREAS.clear()

    from run_game import entities
    entities.Particle.__id = 0

    on: Type[entities.Entity]
    for on in game_structures.recursive_subclasses(entities.Entity):
        on.clean()
    entities.Slime.seen = True
    for attr_value in game_structures.recursive_subclasses(game_areas.GameArea):
        attr_value.seen = False
        attr_value.tutorial_given = False
        attr_value.last_spawned = 0
    GameAreaLog.refresh()


def reset_gameboard():
    heart_data_randomization = random.Random(game_states.SEED)
    cutoffs = [i for i in range(game_states.HEALTH)]
    heart_data_randomization.shuffle(cutoffs)
    for i, index in zip(cutoffs, range(game_states.HEALTH)):
        gameboard.heart_data.append(gameboard.HeartData(heart_data_randomization.random() * math.tau, i, index))
    for heart in gameboard.heart_data:
        heart.find_goals()

    # print(sys.int_info)
    # print(game_states.SEED)


def setup(with_seed: int = None, full: bool = True):
    if full:
        PAUSE_BUTTONS.clear()
        PAUSE_BUTTONS.add_button(game_structures.Button.make_text_button(
            "Quit",
            128,
            (game_states.WIDTH // 2, game_states.HEIGHT // 4),
            enforce_width=768,
            text_align=0.5,
            up_click=quit_run,
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            border_width=5
        ))
        PAUSE_BUTTONS.add_button(game_structures.Button.make_text_button(
            "Resume",
            128,
            (game_states.WIDTH // 2, 2 * game_states.HEIGHT // 4),
            enforce_width=768,
            text_align=0.5,
            up_click=lambda: setattr(ingame, "paused", False),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            border_width=5
        ))
        PAUSE_BUTTONS.add_button(game_structures.Button.make_text_button(
            "Message Log",
            128,
            (game_states.WIDTH // 2, 3 * game_states.HEIGHT // 4),
            enforce_width=768,
            text_align=0.5,
            up_click=switch_to_message_log,
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            border_width=5
        ))
        PAUSE_BUTTONS.add_button(game_structures.ScrollableButtonHolder(
            window_rect=pygame.Rect(
                0, 0, (game_states.WIDTH - 768) // 2 - 20, game_states.HEIGHT
            ),
            background=pygame.Surface((0, 0), pygame.SRCALPHA),
            fill_color=(0, 0, 0, 0)
        ))
        PAUSE_BUTTONS.add_button(game_structures.ScrollableButtonHolder(
            window_rect=pygame.Rect(
                (game_states.WIDTH + 768) // 2 + 20, 0, (game_states.WIDTH - 768) // 2 - 20, game_states.HEIGHT
            ),
            background=pygame.Surface((0, 0), pygame.SRCALPHA),
            fill_color=(0, 0, 0, 0)
        ))
        for i in range(3, 5):
            PAUSE_BUTTONS[i].fit_size()

        MESSAGE_LOG_BUTTONS[0] = game_structures.Button.make_text_button(
            "Back", 128, (0, 0), switch_to_main_pause,
            background_color=(0, 0, 0), outline_color=(255, 255, 255), x_align=0,
            y_align=0, border_width=5)

        game_structures.BUTTONS.clear()
        PAUSE_SWITCHER.background = pygame.Surface((game_states.WIDTH, game_states.HEIGHT), flags=pygame.SRCALPHA)
        PAUSE_SWITCHER.background.convert()
        PAUSE_SWITCHER.rect = PAUSE_SWITCHER.background.get_rect()
        game_structures.BUTTONS.add_button(PAUSE_SWITCHER)

        if not game_states.CUSTOM_SEED:
            if with_seed is None:
                game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
            else:
                game_states.SEED = with_seed
        if game_states.PRINT_SEED:
            print("The seed is:", game_states.SEED)

    game_states.DISTANCE = 100
    game_states.BOTTOM = 0
    if full:
        game_states.RECORD_DISTANCE = 0
        game_states.LAST_AREA_END = 0
        # player state management
        game_states.HEALTH = 5
        game_states.LAST_HEAL = 20
        game_states.LAST_DIRECTION = 1
        game_structures.PLAYER_ENTITY.start_glide(
            0,
            0,
            0,
            0
        )
        # screen shake management
        game_states.X_DISPLACEMENT = 0
        game_states.Y_DISPLACEMENT = 0
        game_states.SHAKE_DURATION = 0
        game_states.X_LIMIT = 0
        game_states.Y_LIMIT = 0
        game_states.X_CHANGE = 0
        game_states.Y_CHANGE = 0
    # screen
    game_states.CAMERA_BOTTOM = game_states.DISTANCE - game_states.CAMERA_THRESHOLDS[0]
    if full:
        # area management
        game_states.AREAS_PASSED = 0
        game_states.LAST_AREA = 0
        # times
        game_states.RUN_START = datetime.datetime.now()

        abilities.last_dash_time = -1 - abilities.dash_cooldown

        game_structures.HANDS[:] = None, None

    clean_gameboard()
    gameboard.ENTITY_BOARD.append(game_structures.PLAYER_ENTITY)

    if full:
        game_areas.guaranteed_type = None

        ingame.paused = False

        reset_gameboard()

        tutorials.add_text(
            "Oh, you're awake.  Good.  (press ENTER)",
            game_structures.FONTS[100]
        )
        tutorials.add_text(
            "You need to be able to defend yourself.  They won't let you live in peace.",
            game_structures.FONTS[100]
        )
        tutorials.add_text(
            "Can you go up?",
            game_structures.FONTS[100]
        )
        tutorials.add_text(
            "Use the w and s keys to move up and down.  Press d to dash in your current direction.",
            game_structures.TUTORIAL_FONTS[90]
        )


def start(with_seed: int = None, full: bool = True):
    setup(with_seed, full)
    game_areas.add_game_area().join()
    for i in range(game_states.AREA_QUEUE_MAX_LENGTH - 1):
        game_areas.add_game_area()


@dataclasses.dataclass
class CustomRun:
    tutorial: tuple[int, int, int] = (True, True, True)
    start: int = 3
    custom_run: list[
        tuple[Type[game_areas.GameArea], tuple] | Type[game_areas.GameArea]
    ] = dataclasses.field(default_factory=list)
    guaranteed_type: Type[game_areas.GameArea] = None


def start_custom(custom: CustomRun):
    setup()

    for i, do in enumerate(custom.tutorial):
        if do:
            game_states.LAST_AREA = i
            game_areas.add_game_area().join()

    game_states.LAST_AREA = custom.start

    for run in custom.custom_run:
        if isinstance(run, tuple):
            area_type: Type[game_areas.GameArea]
            args: tuple
            area_type, args = run
            area = area_type(game_areas.get_determiner(), game_states.LAST_AREA, customized=True)
            area.make(*args)
        else:
            area = run(game_areas.get_determiner(), game_states.LAST_AREA)
        game_structures.AREA_QUEUE.append(area)
        game_states.LAST_AREA += 1

    game_areas.guaranteed_type = custom.guaranteed_type


class GameAreaLog:

    areas_dict: dict[str, int] = dict()

    @staticmethod
    def refresh():
        for sub in game_areas.GameArea.__subclasses__():
            GameAreaLog.areas_dict[sub.__name__] = 0

    @staticmethod
    def get_result_string():
        return str({area_name: count for area_name, count in GameAreaLog.areas_dict.items() if count > 0})


class RunEndReasons(enum.Enum):
    die = "death"
    lose = "loss"
    win = "victory"
    close = "game closed"
    error = "game crashed"
    quit = "quit"


def log_run(reason: RunEndReasons):
    """
    logs the results of a run, including why it ended
    :return:
    """
    now = datetime.datetime.now()
    duration: datetime.timedelta = now - game_states.RUN_START
    log_string = str({
        "reason": reason.value,
        "date": now.date().strftime("%y/%m/%d"),
        "start_time": game_states.RUN_START.strftime("%H:%M:%S"),
        "end_time": now.strftime("%H:%M:%S"),
        "duration": str(duration),
        "seed": game_states.SEED,
        "furthest": visual_distance(),
        "progress": game_states.AREAS_PASSED,
        "room_record": GameAreaLog.get_result_string()
    })
    with open("./run_log.txt", "a") as file:
        file.write(log_string + "\n")
