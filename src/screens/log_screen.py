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

from data import game_states
from general_use import game_structures, utility
from screens import main_screen, custom_runs
from run_game import ingame
import pygame


log_file_name: str = "./run_log.txt"


RECORDS = game_structures.ScrollableButtonHolder(
    pygame.rect.Rect(game_states.WIDTH // 4, 0, game_states.WIDTH // 2, game_states.HEIGHT),
    pygame.surface.Surface((game_states.WIDTH // 2, game_states.HEIGHT)),
    scrollable_x=False,
    scrollable_y=True,
    outline_width=2,
    outline_color=(255, 255, 255)
)
BUTTONS = game_structures.ButtonHolder()


def clear_log():
    RECORDS.x = 0
    RECORDS.y = 0
    RECORDS.background = pygame.surface.Surface((game_states.WIDTH // 2, game_states.HEIGHT))
    RECORDS.rect = RECORDS.background.get_rect()
    with open(log_file_name, "w") as log_file:
        log_file.write("")
    screen.start()


class RunRecord(game_structures.Place, game_structures.Button):

    def __init__(self, reason: str, furthest: int | str, progress: int | str, date: str, duration: str, start_time: str,
                 end_time: str, seed: str | str, room_record: str, custom_run: None | str):

        game_structures.Place.__init__(self, tick=utility.passing, enter=self.enter, end=self.end)
        text = f"{reason}: {furthest}"
        img = self.draw_text(
            text,
            100,
            background_color=(0, 0, 0),
            outline_color=(255, 255, 255)
        )
        game_structures.Button.__init__(self, img, text, img.get_rect(), self.start, fill_color=(0, 0, 0),
                                        outline_color=(255, 255, 255), outline_width=2, inflate_center=(0, 0.5))
        self.reason = reason
        self.furthest = furthest
        self.progress = progress
        self.date = date
        self.duration = duration
        self.start_time = start_time
        self.end_time = end_time
        self.seed = seed
        self.room_record = room_record
        self.custom_run = custom_run
        self.buttons = None

    def set_seed(self):
        game_states.SEED = self.seed
        game_states.CUSTOM_SEED = True

    def enter(self):
        self.buttons = game_structures.ButtonHolder()
        self.buttons.add_button(
            game_structures.Button.make_text_button(self.reason, 400, (game_states.WIDTH // 4, 20), None,
                                                    background_color=(0, 0, 0), outline_color=(255, 255, 255),
                                                    x_align=0, y_align=0, max_width=3 * game_states.WIDTH // 4 - 20)
        )
        self.buttons.add_button(
            game_structures.Button.make_text_button(f"seed: {self.seed}", 50, (game_states.WIDTH // 4, 520),
                                                    self.set_seed, background_color=(0, 0, 0),
                                                    outline_color=(255, 255, 255), x_align=0, y_align=0)
        )

        if self.custom_run is None:
            self.buttons.add_button(
                game_structures.Button.make_text_button("Play", 50,
                                                        (game_states.WIDTH // 4, 610),
                                                        lambda: ingame.screen.start(with_seed=self.seed),
                                                        background_color=(0, 0, 0),
                                                        outline_color=(255, 255, 255), x_align=0, y_align=0)
            )
        else:
            try:
                if custom_runs.LIST is None:
                    custom_runs.first_enter()  # without this, decoding will fail.

                custom_run = custom_runs.custom_run_from_string(self.custom_run)

                self.buttons.add_button(
                    game_structures.Button.make_text_button(f"Play \"{custom_run.name}\"", 50,
                                                            (game_states.WIDTH // 4, 610),
                                                            lambda: ingame.screen.start(custom=custom_run),
                                                            background_color=(0, 0, 0),
                                                            outline_color=(255, 255, 255), x_align=0, y_align=0)
                )

            except Exception as e:
                self.buttons.add_button(
                    game_structures.Button.make_text_button("Custom run cannot be decoded: cannot replay", 50,
                                                            (game_states.WIDTH // 4, 610),
                                                            background_color=(0, 0, 0),
                                                            outline_color=(255, 255, 255), x_align=0, y_align=0)
                )
                e.add_note("This may be caused by the custom run format being out of date.")
                utility.log_error(e)

        self.buttons.add_button(
            game_structures.Button.make_text_button("\n".join(
                [
                    f"time: {self.date}",
                    f"{self.start_time}-{self.end_time} ({self.duration} elapsed)",
                    "",
                    f"distance: {self.furthest}",
                    f"progress: {self.progress} rooms",
                    ""
                ] + [
                    f"""{
                        utility.from_camel(item[0])
                    }: {item[1]}""" for item in sorted(
                        list(ast.literal_eval(self.room_record).items()), key=lambda tup: tup[1]
                    )
                ]), 80, (game_states.WIDTH // 4, 740), None, background_color=(0, 0, 0),
                outline_color=(255, 255, 255), x_align=0, y_align=0)
        )

        self.buttons.add_button(
            game_structures.Button.make_text_button("Back", 75, (game_states.WIDTH, 0), screen.start,
                                                    background_color=(0, 0, 0), outline_color=(255, 255, 255),
                                                    x_align=1, y_align=0, arguments={"re_setup": False})
        )

        game_structures.BUTTONS.add_button(self.buttons)

    def end(self, **kwargs):
        game_structures.BUTTONS.remove(self.buttons)


@utility.add_error_checking
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
        line.get("custom_run", None)
    ))


@utility.make_async(singular=True)
@utility.add_error_checking
def enter(re_setup: bool = True):
    """
    enter run log screen and populate records
    :return:
    """
    game_structures.BUTTONS.add_button(BUTTONS)

    BUTTONS.clear()

    if re_setup:
        RECORDS.change_background_size(
            (game_states.WIDTH // 2, game_states.HEIGHT)
        )
        RECORDS.change_window((game_states.WIDTH // 4, 0), (game_states.WIDTH // 2, game_states.HEIGHT))

    BUTTONS.add_button(RECORDS)
    BUTTONS.add_button(
        game_structures.Button.make_text_button("Back", 75, (game_states.WIDTH, 0), main_screen.main_screen_place.start,
                                                background_color=(0, 0, 0), outline_color=(255, 255, 255), x_align=1,
                                                y_align=0))
    BUTTONS.add_button(
        game_structures.Button.make_text_button("Clear Log", 75, (0, 0), clear_log, background_color=(0, 0, 0),
                                                outline_color=(255, 255, 255), x_align=0, y_align=0))

    if not re_setup:
        return
    RECORDS.clear()
    with open(log_file_name, "r") as log_file:
        line = log_file.readline()
        i = 0
        while line:
            i += 1
            make_record(ast.literal_eval(line))
            line = log_file.readline()
    if len(RECORDS) > 0:
        record_height: int = RECORDS[0].rect.height * 1.25
        i: int = 0
        for record in RECORDS.list:
            record.rect.y = i * record_height
            record.rect.x = 0
            i += 1
        RECORDS.change_background_size((game_states.WIDTH // 2, i * record_height))
        RECORDS.y = RECORDS.background.get_rect().height - game_states.HEIGHT
    else:
        RECORDS.add_button(game_structures.Button.make_text_button("No runs logged.", 80,
                                                                   (game_states.WIDTH // 4, game_states.HEIGHT // 2),
                                                                   None, background_color=(0, 0, 0),
                                                                   outline_color=(255, 255, 255), border_width=0,
                                                                   text_align=0.5))
    RECORDS.convert()


def end():
    game_structures.BUTTONS.remove(BUTTONS)


screen = game_structures.Place(
    tick=utility.passing,
    enter=enter,
    end=end
)
