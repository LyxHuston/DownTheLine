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
"""

import pygame
import game_states
import game_structures
import draw_constants
import tutorials

dash_img = pygame.image.load("resources/abilities/ability_icons/dash_icon.png")

dash_sensitivity = 10

last_press_for_dash = -1 - dash_sensitivity

dash_cooldown = 100

last_dash_time = -1 - dash_cooldown

last_dash_input = 0

def dash_input_catch(direction: int, tick_counter) -> None:
    global dash_cooldown, dash_sensitivity, last_dash_time, last_press_for_dash, last_dash_input
    if last_dash_time + dash_cooldown > tick_counter:
        return
    if last_dash_input == direction and last_press_for_dash + dash_sensitivity >= tick_counter:
        last_dash_input = 0
        last_dash_time = tick_counter
        game_states.GLIDE_SPEED = 25
        game_states.TAPER_AMOUNT = 100
        game_states.GLIDE_DURATION = 20
        game_states.GLIDE_DIRECTION = direction
        game_structures.begin_shake(
            20,
            (3, 0),
            (1, 0)
        )
        return
    last_dash_input = direction
    last_press_for_dash = tick_counter


def draw_dash_icon(tick_counter) -> None:
    x, y = game_states.WIDTH // 2 - dash_img.get_width() // 2, game_states.HEIGHT - 2 * draw_constants.row_separation - tutorials.display_height
    game_structures.SCREEN.blit(
        dash_img,
        (x, y)
    )
    pygame.draw.rect(
        game_structures.SCREEN,
        (0, 0, 0),
        pygame.Rect(x, y, draw_constants.icon_size - round(
            -draw_constants.icon_size * (last_dash_time - tick_counter) / dash_cooldown), draw_constants.icon_size),
    )