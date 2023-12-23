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
import tutorials
import game_structures
import game_states
from game_areas import add_game_area
import ingame
import random
import sys
import utility


@utility.make_async(singular=True)
def start(with_seed: int = None):
    if game_states.PLACE == ingame.tick:
        return
    game_structures.BUTTONS.clear()
    if not game_states.CUSTOM_SEED:
        if with_seed is None:
            game_states.SEED = random.randrange(2 ** sys.int_info.bits_per_digit)
        else:
            game_states.SEED = with_seed
    if game_states.PRINT_SEED:
        print("The seed is:", game_states.SEED)

    # game_structures.CUSTOM_EVENT_CATCHERS.append(game_structures.ALERTS.catch_event)  # (commented out because this one should never be removed)
    game_structures.CUSTOM_EVENT_CATCHERS.append(ingame.event_catcher)

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
    game_states.CAMERA_BOTTOM = 0
    # area management
    game_states.AREAS_PASSED = 0
    game_states.LAST_AREA = 0

    game_structures.HANDS = [None, None]

    tutorials.clear_tutorial_text()

    # print(sys.int_info)
    # print(game_states.SEED)

    import entities
    for attr_value in entities.__dict__.values():
        if isinstance(attr_value, type):
            if issubclass(attr_value, entities.Entity):
                attr_value.seen = False
    entities.Slime.seen = True
    import game_areas
    for attr_value in game_areas.__dict__.values():
        if isinstance(attr_value, type):
            if issubclass(attr_value, game_areas.GameArea):
                attr_value.seen = False

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
    add_game_area().join()
    game_states.PLACE = game_structures.PLACES.in_game
    for i in range(game_states.AREA_QUEUE_MAX_LENGTH - 1):
        add_game_area()

