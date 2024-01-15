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

describe the run log screen of the game
"""

import ast

import game_states
import game_structures
import main_screen
import utility
import pygame


RECORDS = game_structures.ScrollableButtonHolder(
    pygame.rect.Rect(game_states.WIDTH // 4 - 20, 0, 3 * game_states.WIDTH // 4, game_states.HEIGHT),
    pygame.surface.Surface((3 * game_states.WIDTH // 4 + 20, game_states.HEIGHT))
)
BUTTONS = game_structures.ButtonHolder()
BUTTONS.add_button(RECORDS)
BUTTONS.add_button(game_structures.Button.make_text_button(
    "Back",
    75,
    main_screen.main_screen_place.start,
    (game_states.WIDTH, 0),
    background_color=(0, 0, 0),
    outline_color=(255, 255, 255),
    x_align=1,
    y_align=0
))


class RunRecord(game_structures.Place, game_structures.Button):

    def __init__(self, reason: str, furthest: int, progress: int, date: str, duration: str, start_time: str,
                 end_time: str, seed: str, room_record: str):

        game_structures.Place.__init__(self, tick=utility.passing, enter=self.enter, end=self.end)
        text = f"{reason}: {furthest}"
        img = self.draw_text(
            text,
            100,
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255)
        )
        game_structures.Button.__init__(
            self,
            self.start,
            img,
            text,
            img.get_rect(),
            (0, 0, 0),
            (255, 255, 255),
            inflate_center=(0, 0.5),
            outline_width=2
        )
        self.reason = reason
        self.furthest = furthest
        self.progress = progress
        self.date = date
        self.duration = duration
        self.start_time = start_time
        self.end_time = end_time
        self.seed = seed
        self.room_record = room_record
        self.buttons = None

    def set_seed(self):
        game_states.CUSTOM_SEED = self.seed

    def enter(self):
        self.buttons = game_structures.ButtonHolder()
        self.buttons.add_button(
            game_structures.Button.make_text_button(
                self.reason,
                400,
                None,
                (game_states.WIDTH // 4, 20),
                background_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                x_align=0,
                y_align=0
            )
        )
        self.buttons.add_button(
            game_structures.Button.make_text_button(
                f"seed: {self.seed}",
                50,
                self.set_seed,
                (game_states.WIDTH // 4, 420),
                background_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                x_align=0,
                y_align=0,
            )
        )

        lines = [
            f"time: {self.date}",
            f"{self.start_time}-{self.end_time} ({self.duration} elapsed)",
            "",
            f"distance: {self.furthest}",
            f"progress: {self.progress} rooms",
            ""
        ]
        room_record_lines = []
        for item in ast.literal_eval(self.room_record).items():
            i = 0
            while i < len(room_record_lines) and room_record_lines[i][1] < item[1]:
                i += 1
            room_record_lines.insert(i, item)
        for item in room_record_lines:
            lines.append(f"{item[0]}: {item[1]}")

        self.buttons.add_button(
            game_structures.Button.make_text_button(
                "\n".join(lines),
                80,
                None,
                (game_states.WIDTH // 4, 550),
                background_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                x_align=0,
                y_align=0
            )
        )

        self.buttons.add_button(
            game_structures.Button.make_text_button(
                "Back",
                75,
                screen.start,
                (game_states.WIDTH, 0),
                background_color=(0, 0, 0),
                outline_color=(255, 255, 255),
                x_align=1,
                y_align=0
            )
        )

        game_structures.BUTTONS.add_button(self.buttons)

    def end(self):
        game_structures.BUTTONS.remove(self.buttons)


def make_record(line: dict):
    RECORDS.add_button(RunRecord(
        line.get("reason", "N/A"),
        line.get("furthest", "N/A"),
        line.get("progress", "N/A"),
        line.get("date", "N/A"),
        line.get("duration", "N/A"),
        line.get("start_time", "N/A"),
        line.get("end_time", "N/A"),
        line.get("seed", "N/A"),
        line.get("room_record", "N/A"),
    ))


@utility.make_async(singular=True)
def enter():
    """
    enter run log screen and populate records
    :return:
    """
    RECORDS.clear()
    game_structures.BUTTONS.add_button(BUTTONS)
    with open("run_log.txt", "r") as log_file:
        line = log_file.readline()
        while line:
            make_record(ast.literal_eval(line))
            line = log_file.readline()
    if len(RECORDS) > 0:
        record_height = (RECORDS[0].rect.height * 1.25)
        RECORDS.background = pygame.surface.Surface(
            (game_states.WIDTH, max(record_height * len(RECORDS), game_states.HEIGHT))
        )
        i = 0
        for record in RECORDS:
            record.rect.y = i * record_height
            record.rect.x = 20
            i += 1
        RECORDS.y = RECORDS.background.get_rect().height - game_states.HEIGHT
    else:
        RECORDS.background = pygame.surface.Surface(
            (game_states.WIDTH, game_states.WIDTH)
        )
        RECORDS.add_button(game_structures.Button.make_text_button(
            "No runs logged.",
            80,
            None,
            (game_states.WIDTH // 4, game_states.HEIGHT // 2),
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255),
            border_width=0,
            text_align=0.5
        ))
    RECORDS.rect.fit(RECORDS.background.get_rect())


def end():
    game_structures.BUTTONS.remove(BUTTONS)


screen = game_structures.Place(
    tick=utility.passing,
    enter=enter,
    end=end
)
