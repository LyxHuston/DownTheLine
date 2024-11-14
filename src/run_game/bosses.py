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

entities file, but only for bosses
"""
import dataclasses
import functools
import math
import random

from run_game import entities, gameboard
from data import images, game_states
import pygame
from general_use import game_structures, utility
from collections import deque
from typing import Self, Callable, Any
from screens.custom_runs import FieldOptions


class Boss(entities.Entity):
    """
    a boss superclass.  Just has a 'player entered' and alive property
    """

    @dataclasses.dataclass
    class HitTrack:
        source: Any
        time: int

    def __init__(self, img: pygame.Surface, rotation: int, pos: tuple[int, int]):
        super().__init__(img, rotation, pos)
        self.hit_track = []  # used to check if multiple body parts are being hit by the same thing in the same tick
        self.state = 0  # 0 if not crossed middle, 1 if crossed middle
        self.target: entities.Entity | None = None

    def player_entered(self):
        pass

    def hit(self, damage: int, source) -> bool:
        if source not in (hit.source for hit in self.hit_track):
            self.health -= damage
            self.hit_track.append(Boss.HitTrack(source, 60))
            return True
        return False

    def tick(self):
        self.hit_track = list(hit for hit in self.hit_track if hit.time > 0)
        for hit in self.hit_track:
            hit.time -= 1

    def cross_boundary(self):
        """called when the player has crossed the halfway point into a boss area"""
        self.state = 1
        self.target = self.closest_enemy()

    def despawn(self):
        gameboard.NEW_ENTITIES.append(self)


class BodyPart(entities.Entity):
    """
    a body part of a boss
    """

    collide_priority: int = 3
    immune_collide_below: int = 4

    def damage_player(self):
        game_structures.begin_shake(
            self.damage * 30,
            (self.damage * 5, self.damage * 5),
            (self.damage * 2 + 1, self.damage * 3 - 1)
        )
        self.boss.damage_player()

    @property
    def img(self):
        return self.img_getter(self.rotation, False)

    @property
    def flashing_img(self):
        return self.img_getter(self.rotation, True)

    @img.setter
    def img(self, _):
        pass

    def __init__(self, img_getter: Callable[[int, bool], pygame.Surface], rotation: int, pos: tuple[int, int],
                 boss: Boss, damage: int, collides: bool = True):
        super().__init__(img_getter(rotation, False), rotation, pos)
        self.boss: Boss = boss
        self.collides: bool = collides
        self.damage: int = damage
        self.img_getter = img_getter

    @property
    def alive(self) -> bool:
        return self.boss.alive

    @alive.setter
    def alive(self, val):
        self.boss.alive = val

    def tick(self):
        if not self.boss.alive:
            return
        if not self.collides:
            return
        for en in self.colliding(lambda other: other.allied_with_player is not self.allied_with_player):
            en.hit(self.damage, self)

    def hit(self, damage: int, source) -> bool:
        return self.boss.hit(damage, source)

    def draw(self):
        """
        draws boss body part, flashing based on if the boss is damaged.  Doesn't shake
        """
        img = self.img_getter(self.rotation, self.boss.flashing > 0)
        if img is None:
            return
        game_structures.SCREEN.blit(
            img,
            (
                game_structures.to_screen_x(self.x) - img.get_width() // 2,
                game_structures.to_screen_y(self.y) - img.get_height() // 2
            )
        )
        return self.pos

    def despawn(self):
        gameboard.NEW_ENTITIES.append(self)


class Serpent(Boss):
    """
    a serpent that coils around the track
    """

    @dataclasses.dataclass
    class PathItem:
        rotation: int
        position: tuple[int, int]

    @dataclasses.dataclass
    class PathTracker:
        body_part: BodyPart
        path_parts: deque

    @dataclasses.dataclass
    class MovementOption:
        turn: Callable[[], None]
        finish_check: Callable[[], bool]

    @dataclasses.dataclass
    class MovementMakerEntry:
        make: Callable[[], tuple[Callable[[], None], Callable[[], bool]]]
        weight: int
        available: Callable[[], bool] = lambda: True

    fields = (
        FieldOptions.Area.value(),
        FieldOptions.Label.value(
            "Size",
            FieldOptions.Positive.value()
        )
    )

    def die(self):
        gameboard.NEW_ENTITIES.append(SerpentDeathHandler(self))

    def __init__(self, area, size: int, rot=0, pos=(0, 0)):
        super().__init__(images.EMPTY, rot, pos)
        self.parts: tuple[Serpent.PathTracker, ...] | None = None
        self.max_health = size * 10 + 20
        self.health = self.max_health
        self.area_length: int = area.length
        self.area_start = area.start_coordinate
        self.area_end = area.end_coordinate
        self.movement: Serpent.MovementOption = Serpent.MovementOption(lambda: None, lambda: True)
        self.random = random.Random(area.get_next_seed())
        self.size = size
        self.min_speed = 8 + 4 * self.size
        self.speed = 10 + 4 * self.size
        self.max_speed = 12 + 5 * self.size
        self.body_part_sep = self.size + 2
        self.body_length = 30 + 7 * self.size
        self.imgs = tuple(pygame.transform.scale_by(img.img, self.size) for img in images.SERPENT_BODY)
        self.spiral_in_a_row = 0

        self.movement_options: dict[bool, tuple[Serpent.MovementMakerEntry, ...]] = {
            True: (
                Serpent.MovementMakerEntry(
                    self.make_spiral_movement,
                    5
                ),
                Serpent.MovementMakerEntry(
                    self.make_goto_movement,
                    1
                )
            ),
            False: (
                Serpent.MovementMakerEntry(
                    self.make_spiral_movement,
                    2,
                    lambda: self.spiral_in_a_row < 300
                ),
                Serpent.MovementMakerEntry(
                    self.make_dive_movement,
                    5
                ),
                Serpent.MovementMakerEntry(
                    self.make_wave_movement,
                    1,
                    lambda: abs(self.y - self.target.y) > game_states.HEIGHT // 4
                )
            )
        }

    @classmethod
    def make(cls, area) -> Self:
        min_size = max(min(2, area.difficulty // 15), 1)

        max_size = min(max(2, (math.isqrt(area.difficulty) + 2) // 3), 5)

        return cls(area, 2 + min(area.random.randint(min_size, max_size) for _ in range(2)))

    def turn_towards(self, angle):
        diff: int = angle - self.rotation
        if abs(diff) > 180:
            diff = (360 - diff) % 360
        if abs(diff) > 20:
            self.slow_down()
        self.turn(diff)

    def turn(self, angle):
        if abs(angle) > 9:
            self.rotation += math.copysign(5, angle)
        elif abs(angle) > 1:
            self.rotation += angle // 2
        else:
            self.speed_up()

    def speed_up(self):
        self.speed = min(self.speed + 0.125, self.max_speed)

    def slow_down(self):
        self.speed = max(self.speed - 0.25, self.min_speed)

    def make_spiral_movement(self) -> tuple[Callable[[], None], Callable[[], bool]]:
        direction = self.random.choice((-1, 1))
        tightness = self.random.randint(2, 5)
        change = self.random.randint(-2, 2) / 20
        duration = 60 * self.random.randint(1, 5)
        if change > 0:
            duration = min(duration, int((8 - tightness) / change))
        duration = min(300 - self.spiral_in_a_row, duration)

        self.spiral_in_a_row += duration

        def turn():
            nonlocal change, duration, tightness
            duration -= 1
            if duration % self.size == 0:
                self.turn(direction * int(tightness))
                tightness += change

        return turn, lambda: duration <= 0

    def make_goto_movement(self) -> tuple[Callable[[], None], Callable[[], bool]]:
        destination = (
            self.random.choice((-1, 1)) * self.random.randint(game_states.WIDTH // 4, game_states.WIDTH // 2),
            self.random.randint(
                max(self.area_start + self.area_length // 4, self.y - self.area_length // 8),
                min(self.area_end - self.area_length // 4, self.y + self.area_length // 8)
            )
        )

        self.spiral_in_a_row = 0

        def turn():
            to_angle = math.degrees(math.atan2(destination[0] - self.x, self.y - destination[1])) % 360
            diff: int = to_angle - self.rotation
            if abs(diff) > 180:
                diff = 360 - diff
            if abs(diff) > 3:
                self.rotation += math.copysign(2, diff)
            elif abs(diff) > 1:
                self.rotation += diff // 2

        return turn, lambda: (self.x - destination[0]) ** 2 + (self.y - destination[1]) < 4 * self.speed ** 2

    def make_dive_movement(self):
        diving = False
        left = None

        self.spiral_in_a_row = 0

        def turn():
            nonlocal diving, left

            if diving:  # has already entered the correct cone, assume it's close enough still, keep diving
                to_angle = math.degrees(math.atan2(self.target.x - self.x, self.y - self.target.y)) % 360
                # limit to 45 degree incident angle (https://www.desmos.com/calculator/pt0opyurc0)
                to_angle = 90 - min(abs(abs(to_angle - 180) - 90), 40) * (-1 if to_angle < 180 else 1) * (
                    1 if 90 < to_angle < 270 else -1) + (0 if to_angle < 180 else 180)
            else:  # go away from line
                left = self.x < 0
                to_angle = 270 if left else 90
                # angle towards player, more so if further from track.  Asymptotic to 90 degrees
                if abs(self.x) > 0:
                    adjust = math.degrees(math.atan(self.x / 100))
                    # modify so it angles correctly based on position
                    # adjust *= 1 if left else -1  already done in atan
                    adjust *= 1 if self.y < self.target.y else -1
                    to_angle += adjust
                if (
                        abs(self.x - self.target.x) > game_states.WIDTH // 6
                        and abs(self.y - self.target.y) < abs(self.x - self.target.x)
                ):  # check if has entered into about 30 degree cone
                    diving = True
            self.turn_towards(to_angle)

        return turn, lambda: self.target is None or (diving and left is not self.x < 0)  # check it's dived to the other side or target dead

    def make_wave_movement(self):
        stage = 0  # 0: retreating, 1: diving, 2: wave
        tightness = 5  # how quickly the snake turns.  Higher number, the tighter the wave.
        direction = 0  # up/down

        self.spiral_in_a_row = 0

        def turn():
            nonlocal stage, direction, tightness

            left = self.x < 0
            if stage == 0:  # go away from track
                to_angle = 270 if left else 90
                # angle away from player, more so if further from track.  Asymptotic to 90 degrees
                adjust = math.degrees(math.atan(self.x / 100))
                # modify so it angles correctly based on position
                adjust *= -1 if left else 1
                adjust *= -1 if self.y < self.target.y else 1
                to_angle += adjust
                self.turn_towards(to_angle)
                if abs(self.x) > game_states.WIDTH // 4:
                    stage = 1
            elif stage == 1:  # return to track, intercepting at a (hopefully) 90 degree angle
                to_angle = 90 if left else 270
                self.turn_towards(to_angle)
                if abs(self.x) < self.speed:
                    self.rotation = 270 if self.rotation > 180 else 90  # take no chances about intercept angle
                    direction = -1 if self.y < self.target.y else 1
                    stage = 2
            elif stage == 2:
                adjust = round(tightness) * direction * (1 if self.x < 0 else -1)
                self.rotation += adjust
                if abs(self.x) < self.speed:
                    self.speed_up()
                    self.speed_up()
                    tightness += 0.25

        return turn, lambda: self.target is None or stage == 2 and abs(self.x) < self.speed and (-1 if self.y < self.target.y else 1) != direction

    def get_next_movement(self) -> MovementOption:
        out_y = not self.area_start < self.y < self.area_end  # keep it in the area
        out_x = abs(self.x) > game_states.WIDTH // 3  # keep it on the screen
        if out_y or out_x:  # return

            if out_y:
                ideal_angle = 180 if self.y < self.area_start else 360
                # angle away from track, more so if closer
                adjust = 5 * round(math.sin(1/(self.x ** 2 + 3)) / math.sin(1 / 3))
                # modify so it angles correctly based on position
                adjust *= -1 if self.x < 0 else 1
                adjust *= -1 if self.y < self.area_start else 1
                ideal_angle += adjust
                ideal_angle %= 360

                def finish_check():
                    return self.area_start + self.area_length // 4 < self.y < self.area_end - self.area_length // 4

            else:
                ideal_angle = 90 if self.x < 0 else 270

                def finish_check():
                    return abs(self.x) < game_states.WIDTH // 4

            turn = functools.partial(self.turn_towards, ideal_angle)

        else:

            options: tuple[Serpent.MovementMakerEntry] = tuple(filter(
                lambda movement_option: movement_option.available(),
                self.movement_options[self.target is None]
            ))

            tot = sum(op.weight for op in options)

            select = self.random.randint(1, tot)

            i = -1
            while select > 0:
                i += 1
                select -= options[i].weight

            turn, finish_check = options[i].make()

        return Serpent.MovementOption(turn, finish_check)

    def next_path_item(self) -> PathItem:
        if self.movement.finish_check():
            self.movement = self.get_next_movement()
        self.movement.turn()
        rads = math.radians(self.rotation)
        self.x += round(self.speed * math.sin(rads))
        self.y -= round(self.speed * math.cos(rads))
        return Serpent.PathItem(
            self.rotation,
            self.pos
        )

    def tick(self):
        if not self.state:
            return
        super().tick()
        if self.target is None or not self.target.alive:
            self.target = self.closest_enemy(self.area_length)
        last: Serpent.PathItem = self.next_path_item()
        part: Serpent.PathTracker
        for part in self.parts:
            part.path_parts.append(last)
            part.body_part.pos = last.position
            part.body_part.rotation = last.rotation + 180
            last = part.path_parts.popleft()

    def get_image_index_from_part_index(self, i: int) -> int:
        # equation: https://www.desmos.com/calculator/j0qun80i6c idk how long that will be valid
        # constants that let it expand if necessary
        l = len(images.SERPENT_BODY)  # length of the images options.  Range of graph.
        m = self.body_length  # number of body parts.  Domain of graph.
        # constants that affect the shape of the graph
        c = 1 / 3  # center of main body hump
        d = 3  # dampener for the hump
        bfl = 1 / 4  # body flattening constant
        nfl = 1 / 4  # neck flattening constant

        f_1 = math.sin(1 / (bfl * (i - c * m) ** 2 + d)) / math.sin(1 / d)  # calculate main body hump
        f_1 *= i * (m - i) / ((m / 2) ** 2)  # make sure it's 0 at the edges

        f_2 = 1 / (1 + i / (nfl * m)) - i / m * 1 / (1 + 1 / nfl)  # calculate neck width

        # join f_1 and f_2 smoothly.  Basically has each of them be a percent of height remaining
        final = 1 - (1 - f_1) * (1 - f_2)

        index = round((l - 1) * final)

        return index

    def get_image_from_index(self, i: int) -> pygame.Surface:
        return self.imgs[self.get_image_index_from_part_index(i)]

    def final_load(self) -> None:
        super().final_load()
        self.area_start = self.y
        self.area_end = self.area_start + self.area_length
        self.y += self.area_length + 90

        img_parts = (
            pygame.transform.scale_by(images.SERPENT_HEAD.img, self.size),
            *self.imgs
        )

        @utility.memoize
        def get_img(index: int, rot: int, flashing: bool):
            if flashing:
                return utility.make_flashing_img(get_img(index, rot, False))
            else:
                return pygame.transform.rotate(img_parts[index], rot)

        make_img_getter = lambda i: lambda rot, flashing: get_img(i, rot, flashing)

        self.parts = (
            Serpent.PathTracker(
                BodyPart(make_img_getter(0), 0, (game_states.WIDTH, self.y), self, self.size + 2),
                deque(Serpent.PathItem(0, self.pos) for _ in range(4 + self.body_part_sep))
            ),
            *(Serpent.PathTracker(
                BodyPart(make_img_getter(1 + self.get_image_index_from_part_index(i)), 0, (game_states.WIDTH, self.y + i * 100), self, self.size + 1),
                deque(Serpent.PathItem(0, (self.x, self.y + i * 100)) for _ in range(self.body_part_sep))
            ) for i in range(self.body_length))
        )
        parts: tuple[BodyPart, ...] = tuple(part.body_part for part in self.parts)
        part: BodyPart
        num = len(parts)
        for i, part in enumerate(parts):
            part.final_load()
            part.draw_priority = 1 - i / num
        gameboard.NEW_ENTITIES.extend(parts)


class SerpentDeathHandler(entities.InvulnerableEntity):

    @property
    def alive(self) -> bool:
        return len(self.serpent.parts) > 0

    def __init__(self, serpent: Serpent):
        super().__init__(images.EMPTY, 0, serpent.pos)
        self.serpent = serpent
        self.explosion_tick = self.serpent.body_part_sep
        self.move_queue = deque()
        self.slow = 0.75  # tick delays between a tick
        self.slow_progress = 0
        self.slow_increase_delay = 1  # proper ticks between a slow increase
        self.slow_increase_progress = 0

    def tick(self):
        if self.slow_progress >= self.slow:
            self.slow_progress = 0
            self.slow_increase_progress += 0.25
            if self.slow_increase_progress >= self.slow_increase_delay:
                self.slow += 1
                self.slow_increase_progress = 0
                self.slow_increase_delay += 2
        else:
            self.slow_progress += 1
            return
        self.explosion_tick += 1
        if self.explosion_tick > self.serpent.body_part_sep // 2:
            self.explosion_tick = 0

            if len(self.serpent.parts) >= 2:
                part_0 = self.serpent.parts[0].body_part
                part_1 = self.serpent.parts[1].body_part
                part_0_dist = part_0.height
                part_1_dist = part_1.height
                part_0_rot = math.radians(part_0.rotation)  # check behind
                part_1_rot = math.radians((part_1.rotation + 180) % 180)  # check in front
                part_0_pos = (
                    part_0.x + round(part_0_dist * math.sin(part_0_rot)),
                    part_0.y - round(part_0_dist * math.cos(part_0_rot))
                )
                part_1_pos = (
                    part_1.x + round(part_1_dist * math.sin(part_1_rot)),
                    part_1.y - round(part_1_dist * math.cos(part_1_rot))
                )
                gameboard.PARTICLE_BOARD.add(
                    entities.EXPLOSION_PARTICLES(
                        (
                            (part_0_pos[0] + part_1_pos[0]) // 2,
                            (part_0_pos[1] + part_1_pos[1]) // 2
                        ),
                        rotation=self.serpent.random.randint(0, 359)
                    )
                )

            body_part = self.serpent.parts[0].body_part
            self.move_queue = self.serpent.parts[0].path_parts

            self.serpent.parts = self.serpent.parts[1:]

            rads = math.radians((body_part.rotation + 180) % 360)
            momentum = (round(self.serpent.speed * math.sin(rads) / self.slow), -round(self.serpent.speed * math.cos(rads) / self.slow))
            # if I want to add break-apart stuff to the particles, need to get the original image, somehow
            gameboard.PARTICLE_BOARD.add(entities.Particle(
                imgs=[body_part.img],
                tick_rate=1000,
                lifespan=30,
                radius=body_part.radius(),
                pos=body_part.pos,
                momentum=momentum
            ))

        last: Serpent.PathItem = self.move_queue.popleft()
        part: Serpent.PathTracker
        i = 0
        for part in self.serpent.parts:
            shakiness = 52 // (i + 2)
            part.path_parts.append(last)
            part.body_part.pos = last.position
            part.body_part.x += round(shakiness * bounce_1(
                i * self.slow + self.slow_increase_progress + self.slow_increase_delay
            ))
            part.body_part.y += round(shakiness * bounce_1(
                i * (self.slow_increase_progress + self.slow_increase_delay) + self.slow
            ))
            part.body_part.rotation = last.rotation + 180
            last = part.path_parts.popleft()
            i += 1

    def draw(self):
        for part in self.serpent.parts:
            part.body_part.draw()


def bounce_1(num: float) -> float:
    """
    get a number between 1 and 0, with a slope of absolute value 1, going up on evens and down on odds.
    On the interval of [0,1], bounce_1(x) = x
    """
    return 1 - abs(num % 2 - 1)


class Star(Boss):

    pulse_difference = 20

    def __init__(self, y: int, layers: int):
        super().__init__(pygame.Surface((60, 60)), 0, (0, y))
        self.max_health: int = 16
        self.health: int = 16
        self.layers: list[entities.Lazer] = []
        self.layer_radiuses: list[float] = []
        self.pulses = [(0, 0) for _ in range(self.pulse_difference * (layers - 1) + 1)]
        self.pulse = (0, 1)
        radius: float = 128
        for i in range(layers):
            n = i + 3
            new_lazer: entities.RotatingLazer = entities.RotatingLazer(
                0, radius, n, self.pos, 240, 240, 0, halt_dashes=True
            )
            self.layers.append(new_lazer)
            self.layer_radiuses.append(radius)
            new_lazer.set_momentum(3 / math.log2(n) ** 1.5 * (-1 if (n % 4) // 2 == 0 else 1))
            if i % 2 == 0:
                new_lazer.start_firing()
            else:
                new_lazer.stop_firing()
            radius /= math.cos(math.pi / n)

    @classmethod
    def make(cls, area) -> Self:
        min_size = max(min(2, area.difficulty // 15), 1)

        max_size = min(max(2, (math.isqrt(area.difficulty) + 2) // 3), 5)

        return cls(area.length, 2 + min(area.random.randint(min_size, max_size) for _ in range(2)))

    def final_load(self) -> None:
        super().final_load()
        gameboard.NEW_ENTITIES.extend(self.layers)

    def die(self):
        for layer in self.layers:
            layer.repeats = 0

    def tick(self) -> None:
        self.y += 1 if self.y < game_structures.PLAYER_ENTITY.y else -1
        pulse = self.pulse
        for i in range(len(self.pulses)):
            pulse, self.pulses[i] = self.pulses[i], pulse
        for i in range(len(self.layers)):
            pulse, factor = self.pulses[i * self.pulse_difference]
            radius = (self.layer_radiuses[i] + pulse) * factor
            layer = self.layers[i]
            layer.pos = self.pos
            layer.rad = radius

    def draw(self) -> None:
        pass


boss_types = game_structures.recursive_subclasses(Boss)
