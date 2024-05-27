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

essentially, a bunch of trackers for game states.  If it is more than a single
function, string, or integer, it's too much and should go in game_structures.
Except for dev tool storage
"""

# overall game state
RUNNING: bool = True
PLACE = None
# distance management
DISTANCE: int = 100
BOTTOM: int = 0
RECORD_DISTANCE: int = 0
LAST_AREA_END: int = 0
# player state management
HEALTH: int = 5
TIME_SINCE_LAST_INTERACTION: int = 0
LAST_HEAL: int = 0
LAST_DIRECTION: int = 1
# dash management is now on player entity
# GLIDE_SPEED: int = 0
# GLIDE_DIRECTION: int = 0
# GLIDE_DURATION: int = 0
# TAPER_AMOUNT: int = 0
INVULNERABILITY_LEFT: int = 0
# screen shake management
X_DISPLACEMENT: int = 0
Y_DISPLACEMENT: int = 0
SHAKE_DURATION: int = 0
X_LIMIT: int = 0
Y_LIMIT: int = 0
X_CHANGE: int = 0
Y_CHANGE: int = 0
# camera management
HEIGHT: int = 0
WIDTH: int = 0
CAMERA_THRESHOLDS: tuple[int, int] = (0, 0)
CAMERA_BOTTOM: int = 0
JITTER_PROTECTION_DISTANCE: int = 0
JITTER_PROTECTION_CAMERA: int = 0
# area management
AREAS_PASSED: int = 0
LAST_AREA: int = 0
AREA_QUEUE_MAX_LENGTH: int = 7
# the seed
SEED: int = 0
# settings
DO_TTS: bool = False
# dev tools
INVULNERABLE: bool = False
CUSTOM_SEED: bool = False
PRINT_SEED: bool = False
# times
RUN_START = None
