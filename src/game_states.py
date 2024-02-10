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
RUNNING = True
PLACE = None
# distance management
DISTANCE = 100
BOTTOM = 0
RECORD_DISTANCE = 0
LAST_AREA_END = 0
# player state management
HEALTH = 5
TIME_SINCE_LAST_INTERACTION = 0
LAST_HEAL = 0
LAST_DIRECTION = 1
GLIDE_SPEED = 0
GLIDE_DIRECTION = 0
GLIDE_DURATION = 0
TAPER_AMOUNT = 0
INVULNERABILITY_LEFT = 0
# screen shake management
X_DISPLACEMENT = 0
Y_DISPLACEMENT = 0
SHAKE_DURATION = 0
X_LIMIT = 0
Y_LIMIT = 0
X_CHANGE = 0
Y_CHANGE = 0
# camera management
HEIGHT = 0
WIDTH = 0
CAMERA_THRESHOLDS = (0, 0)
CAMERA_BOTTOM = 0
# area management
AREAS_PASSED = 0
LAST_AREA = 0
AREA_QUEUE_MAX_LENGTH = 7
# the seed
SEED = 0
# settings
DO_TTS = False
# dev tools
AUTOSAVE = False
SAVE_DATA = None
HANDS_SAVE = None
QUEUE_SAVE = None
INVULNERABLE = False
CUSTOM_SEED = False
PRINT_SEED = False
# times
RUN_START = None
