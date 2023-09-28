"""
essentially, a bunch of trackers for game states.  If it is more than a single
function, string, or integer, it's too much and should go in game_structures
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
LAST_DIRECTION = 1
GLIDE_SPEED = 0
GLIDE_DIRECTION = 0
GLIDE_DURATION = 0
TAPER_AMOUNT = 0
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
AREA_QUEUE_MAX_LENGTH = 3
# the seed
SEED = 0
# settings
DO_TTS = False