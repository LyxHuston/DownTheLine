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
import datetime
import enum
from typing import Type

import tutorials
import game_structures
import game_states
import game_areas
import ingame
import random
import sys
import utility


def start(with_seed: int = None):
    game_structures.BUTTONS.clear()
    if not game_states.CUSTOM_SEED:
        if with_seed is None:
            game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
        else:
            game_states.SEED = with_seed
    if game_states.PRINT_SEED:
        print("The seed is:", game_states.SEED)

    game_states.DISTANCE = 100
    game_states.BOTTOM = 0
    game_states.RECORD_DISTANCE = 0
    game_states.LAST_AREA_END = 0
    # player state management
    game_states.HEALTH = 5
    game_states.LAST_DIRECTION = 1
    game_states.GLIDE_SPEED = 0
    game_states.GLIDE_DIRECTION = 0
    game_states.GLIDE_DURATION = 0
    game_states.TAPER_AMOUNT = 0
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
    # area management
    game_states.AREAS_PASSED = 0
    game_states.LAST_AREA = 0
    # times
    game_states.RUN_START = datetime.datetime.now()

    game_structures.HANDS = [None, None]

    tutorials.clear_tutorial_text()

    # print(sys.int_info)
    # print(game_states.SEED)

    import entities
    for attr_value in entities.Entity.__subclasses__():
        attr_value.seen = False
    entities.Slime.seen = True
    for attr_value in game_areas.GameArea.__subclasses__():
        attr_value.seen = False
    GameAreaLog.refresh()

    tutorials.add_text(
        "Oh, you're awake.  Good.",
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
        "Use the w and s keys to move up and down.  You can also double tap to dash.",
        game_structures.TUTORIAL_FONTS[90]
    )

    game_structures.AREA_QUEUE.clear()
    game_areas.add_game_area().join()
    for i in range(game_states.AREA_QUEUE_MAX_LENGTH - 1):
        game_areas.add_game_area()


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
        "furthest": game_states.RECORD_DISTANCE,
        "progress": game_states.AREAS_PASSED,
        "room_record": GameAreaLog.get_result_string()
    })
    with open("run_log.txt", "a") as file:
        file.write(log_string + "\n")
