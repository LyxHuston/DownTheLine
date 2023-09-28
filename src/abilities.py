import pygame
import game_states
import game_structures

dash_img = pygame.image.load("resources/abilities/ability_icons/dash_icon.png")

dash_sensitivity = 20

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
    game_structures.SCREEN.blit(
        dash_img,
        (0, 136)
    )
    pygame.draw.rect(
        game_structures.SCREEN,
        (0, 0, 0),
        pygame.Rect(0, 136, 64 - round(-64 * (last_dash_time - tick_counter) / dash_cooldown), 64),
    )