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

handles the custom runs, logic, and starting
"""

import dataclasses

from typing import Type

from data import game_states
from general_use import game_structures
from run_game import game_areas
from screens import run_start_end


@dataclasses.dataclass
class CustomRun:
	seed: int | None = None
	tutorial: tuple[int, int, int] = (True, True, True)
	start: int = 3
	custom_run: list[
		tuple[Type[game_areas.GameArea], tuple] | Type[game_areas.GameArea]
	] = dataclasses.field(default_factory=list)
	guaranteed_type: Type[game_areas.GameArea] = None


def start_custom(custom: CustomRun):
	run_start_end.setup()

	if custom.seed is not None:
		game_states.SEED = custom.seed

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