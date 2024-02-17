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

handles making and managing game areas
"""
import random

import pygame

from data import game_states, images
from run_game import tutorials, entities, bosses, items
from general_use.utility import make_async, add_error_checking
from general_use import game_structures
import math
from collections import deque
from typing import Type, Iterable


class GameArea:
    """
    an area with entities to interact with.  Must always be initialized offscreen

    this superclass should only be directly initialized for a tutorial instance
    """

    @property
    def enforce_center(self) -> int | None:
        if self.start_coordinate < game_states.DISTANCE < self.end_coordinate:
            return self.__enforce_center
        return None

    @enforce_center.setter
    def enforce_center(self, val: int | None):
        self.__enforce_center = val

    @property
    def start_coordinate(self):
        return self.__start_coordinate

    @start_coordinate.setter
    def start_coordinate(self, val):
        self.__start_coordinate = round(val)

    @property
    def end_coordinate(self):
        return self.start_coordinate + self.length

    def __init__(self, length: int = 0, seed: int = None):
        self.enforce_center = None
        self.start_coordinate = 0
        self.length = length
        self.initialized = False
        self.boundary_crossed = False
        self.entity_list = []
        self.particle_args: tuple[list[images.Image] | list[pygame.Surface], int, int] = (
            images.VOID_PARTICLES, 30, 120
        )
        self.particle_list = set()
        if seed is None:
            self.random = random.Random()
        else:
            self.random = random.Random(seed)
        self.spawn_end = 0  # track which end to spawn a particle on

    seen = False

    def final_load(self):
        if not self.__class__.seen:
            self.__class__.seen = True
            self.start_tutorial()
        for entity in self.entity_list:
            entity.final_load()

    def start_tutorial(self):
        pass

    def draw(self):
        remove_list = deque()
        for particle in self.particle_list:
            if particle.tick():
                particle.draw()
            else:
                remove_list.append(particle)
        for particle in remove_list:
            self.particle_list.remove(particle)
        for entity in self.entity_list:
            entity.draw()

    region_length = 32000
    taper_length = 100

    def tick(self) -> tuple[int, int]:
        region = 0
        while region * self.region_length + self.taper_length < self.length:  # spawn particles for middle regions
            height = self.start_coordinate + self.random.randint(0, self.region_length - 1) + region * self.region_length
            if height > self.end_coordinate - self.taper_length // 2:
                break
            # noinspection PyTypeChecker
            self.particle_list.add(entities.Particle(
                *self.particle_args,
                (
                    self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                    height
                )
            ))
            region += 1
        self.spawn_end = not self.spawn_end
        if self.random.randint(0, self.region_length // self.taper_length) == 0:
            # noinspection PyTypeChecker
            self.particle_list.add(entities.Particle(
                *self.particle_args,
                (
                    self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                    self.start_coordinate + self.length // 2 + (self.spawn_end * 2 - 1) * (
                            self.length +
                            self.taper_length - round(math.sqrt(1 + 8 * self.random.randint(0, (self.taper_length + 1) * self.taper_length // 2) - 1) - 1)
                    ) // 2
                )
            ))
        # print(len(self.particle_list))
        i = 0
        mass = 0
        total = 0
        while i < len(self.entity_list):
            e: entities.Entity = self.entity_list[i]
            if e.alive:
                e.tick()
                i += 1
                dist = e.distance_to_player()
                if dist < game_states.HEIGHT:
                    if dist > 100 or not e.in_view(game_states.CAMERA_THRESHOLDS[0]):
                        mass += (game_states.DISTANCE < e.y) * 2 - 1
                        total += 1
                # if game_states.DISTANCE + game_states.HEIGHT > e.y > game_states.DISTANCE:
                #     mass += 1
                # elif game_states.DISTANCE - game_states.HEIGHT < e.y < game_states.DISTANCE:
                #     mass -= 1
                # total += 1
            else:
                e.die()
                del self.entity_list[i]
        if not self.boundary_crossed and game_states.DISTANCE > self.start_coordinate:
            self.boundary_crossed = True
            self.cross_boundary()
        return mass, total

    def cross_boundary(self):
        """
        called when player actually enters an area.  Usually used for a tutorial or gods.
        :return:
        """
        pass

    def finalize(self):
        """
        called at the end of an intialization.  Ensures that the start
        coordinate is offscreen and moves everything to correct position

        DON'T CALL THIS IN __INIT__!!!  Called during add_area().
        :return:
        """
        if self.start_coordinate < game_states.CAMERA_BOTTOM + game_states.HEIGHT + 100 or self.start_coordinate < game_states.LAST_AREA_END:
            self.start_coordinate = max(game_states.CAMERA_BOTTOM + game_states.HEIGHT + 100, game_states.LAST_AREA_END)
        game_states.LAST_AREA_END = self.end_coordinate
        for entity in self.entity_list:
            entity.y += self.start_coordinate

    def cleanup(self):
        for entity in self.entity_list:
            entity.cleanup()


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    allowable_thresh_holds = [(entities.Slime, 0), (entities.Crawler, 5), (entities.Fencer, 10), (entities.Archer, 10), (
    entities.Knight, 15)]
    # allowable_thresh_holds = [(entities.Knight, 0)]

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.length = 300 + math.floor(math.log2(count)) * 150
        self.difficulty = count
        allowance = count
        allowable_entities = []
        for entry in self.allowable_thresh_holds:
            if entry[1] > count:
                break
            allowable_entities.append([entry[0], 0])
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            num += 1
            entity = allowable_entities[index][0]
            if entity.seen:
                allowance -= entity.cost + allowable_entities[index][1]
                allowable_entities[index][1] += 1
                self.entity_list.append(entity.make(determiner, self))
            else:
                self.entity_list.clear()
                self.length = 1500
                add = entity.make(determiner, self)
                add.y = self.length // 2
                self.entity_list.append(add)
                self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=5))

                def first_see_of_entity():
                    if not entity.tutorial_given:
                        entity.tutorial_given = True
                        tutorials.clear_tutorial_text()
                        tutorials.add_text(entity.tutorial_text, game_structures.FONTS[100])

                self.cross_boundary = first_see_of_entity

                break


class BreakThroughArea(GameArea):
    """
    area that continually spawns monsters, objective to break through them and
    destroy the wall at the end
    """

    tutorial_given = False

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.length = game_states.HEIGHT // 2 + math.floor(math.log2(count)) * 150
        allowance = count
        while allowance > 0:
            spawner = entities.Spawner.make(determiner, self)
            self.entity_list.append(spawner)
            if spawner.limit is None:
                allowance -= 2 * (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
            else:
                allowance -= 2 * (spawner.limit + 1) * spawner.entity.cost ** 2
        allowance = count // 3
        allowable_entities = []
        for entry in BasicArea.allowable_thresh_holds:
            if entry[1] > count or not entry[0].seen:
                break
            allowable_entities.append([entry[0], 0])
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            num += 1
            entity = allowable_entities[index][0]
            allowance -= entity.cost + allowable_entities[index][1] ** 2
            allowable_entities[index][1] += 1
            self.entity_list.append(entity.make(determiner, self))
        self.entity_list.append(entities.Obstacle(pos=(0, self.length)))

    def cross_boundary(self):
        if not BreakThroughArea.tutorial_given:
            BreakThroughArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "Oh, they left their spawners active.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "Irresponsible for the fabric of reality, but oh well.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "You'll need to kill them quick enough to break through.",
                game_structures.FONTS[100]
            )


class GiftArea(GameArea):
    """
    gives player a new item and area to practice it with.
    """

    tutorial_given = False

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.length = 1500
        spawn = entities.Spawner.make(determiner, self)
        experiment_area = 900
        spawn.y += experiment_area
        self.length += experiment_area
        self.entity_list.append(spawn)
        self.entity_list.append(entities.Obstacle(pos=(0, experiment_area), health=1))
        self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=10))
        self.entity_list.append(entities.ItemEntity(items.make_random_reusable(self.random, (0, experiment_area // 2))))

    def cross_boundary(self):
        if not GiftArea.tutorial_given:
            GiftArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "A new item for you!",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "I'm not certain if it will be more powerful than your current ones.",
                game_structures.FONTS[100]
            )


class EnslaughtArea(GameArea):
    """
    game area that is just surviving a bunch of enemies
    """

    tutorial_given = False

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.current_difficulty = count
        self.length = game_states.HEIGHT * 4
        self.entity_list.append(entities.InvulnerableObstacle(pos=(0, self.length), health=1))
        self.state = 0  # 0: not started 1: in progress 2: finished, killing off entities
        self.timer = 30 * 60 + 120 * math.floor(math.log2(count))
        self.max = self.timer
        self.cooldown_ticks = 0

    def draw(self):
        super(EnslaughtArea, self).draw()
        if self.state == 1:
            width = 3 * game_states.WIDTH // 4 * self.timer / self.max
            pygame.draw.line(
                game_structures.SCREEN,
                (255, 255, 255),
                (game_states.WIDTH // 2 - width // 2, 20),
                (game_states.WIDTH // 2 + width // 2, 20),
                20
            )

    cooldown = 300

    def tick(self):
        ret = super(EnslaughtArea, self).tick()
        if self.state == 0:
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                self.state = 1
                end_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate))
                end_wall.final_load()
                self.entity_list.append(end_wall)
                self.cooldown_ticks = self.cooldown
        elif self.state == 1:
            self.timer -= 1
            if self.cooldown_ticks <= 0:
                self.cooldown_ticks = self.cooldown
                self.event()
            self.cooldown_ticks -= 1
            if self.timer <= 0:
                self.state = 2
                self.cooldown_ticks = 0
                self.entity_list[0].die()
                del self.entity_list[0]
        elif self.state == 2:
            if self.cooldown_ticks <= 0:
                self.cooldown_ticks = 30
                for entity in self.entity_list:
                    entity.health -= 1
            self.cooldown_ticks -= 1
        return ret

    def event(self):
        target_change = (self.difficulty - self.current_difficulty) // 2 + 8 * self.random.randint(-1, 3)
        if target_change < 0:
            # print("Item duplicator")
            pos = (
                self.random.randint(100, game_states.WIDTH // 2) * (self.random.randint(0, 1) * 2 - 1),
                self.random.randint(self.start_coordinate + 100, self.end_coordinate - 100)
            )
            self.entity_list.append(entities.Spawner(
                pos,
                1,
                self,
                0,
                entities.make_item_duplicator(items.make_random_single_use(self.random, pos)),
                (0, None),
                1
            ))
            self.current_difficulty -= 20
        elif target_change < 10:
            # print("Lazers")
            for i in range(target_change):
                self.entity_list.append(entities.DelayedDeploy(
                    i * 60,
                    self,
                    entities.TrackingLazer,
                    (
                        self.end_coordinate,
                        60,
                        60,
                        self
                    )
                ))
        elif target_change < 15:
            # print("Fishies")
            for i in range(target_change // 3):
                self.entity_list.append(entities.Fish(self))
                self.current_difficulty += 2
        elif target_change < 30:
            # print("Spawning")
            allowable_entities = []
            for entry in BasicArea.allowable_thresh_holds:
                if entry[1] > self.difficulty or not entry[0].seen:
                    break
                allowable_entities.append([entry[0], 0])
            num = 3
            determiner = self.random.randint(0, 2 ** 31)
            while target_change > 0:
                index = (determiner % num) % len(allowable_entities)
                num += 1
                entity = allowable_entities[index][0]
                target_change -= entity.cost + allowable_entities[index][1] ** 2
                self.current_difficulty += entity.cost + allowable_entities[index][1] ** 2
                allowable_entities[index][1] += 1
                made_entity = entity.make(determiner, self)
                made_entity.y += self.start_coordinate
                if game_states.CAMERA_BOTTOM + made_entity.height < made_entity.y < game_states.CAMERA_BOTTOM + game_states.HEIGHT - made_entity.height:
                    if game_states.DISTANCE - self.start_coordinate < self.length // 2:
                        made_entity.y = self.end_coordinate - 100
                    else:
                        made_entity.y = self.start_coordinate + 100
                self.entity_list.append(made_entity)
                # print(made_entity)
        else:
            # print("Spawners")
            for i in range(target_change // 15):
                spawner = entities.Spawner.make(self.random.randint(0, 2 ** 31), self)
                if spawner.limit is None:
                    self.current_difficulty += (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
                else:
                    self.current_difficulty += (spawner.limit + 1) * spawner.entity.cost ** 2
                spawner.y += self.start_coordinate
                self.entity_list.append(spawner)
        # print(f"{self.current_difficulty}/{self.difficulty}")

    def cross_boundary(self):
        if not EnslaughtArea.tutorial_given:
            EnslaughtArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "Oh, it's one of these places.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "Challenges will come in waves.  You won't get time to rest.  Good luck.",
                game_structures.FONTS[100]
            )


class MinigameArea(GameArea):
    tutorial_given = False

    def __init__(self, determiner, count):
        super().__init__(seed=determiner)
        self.difficulty = count
        self.state = 0
        self.solved_entity_number = 2
        self.type = self.random.randint(0, 2)
        # print(f"minigame area: {["fishing", "notes", "lazers"][self.type]}")
        if self.type == 0:  # obligatory fishing minigame
            self.length = game_states.HEIGHT * 2
        elif self.type == 1:  # notes
            self.solved_entity_number = 4
            self.length = game_states.HEIGHT
            self.entity_list.append(entities.ItemEntity(items.simple_stab(
                10,
                60,
                images.BATON.img,
                (5, self.length - 200),
                0
            )))
            self.entity_list.append(entities.ItemEntity(items.simple_stab(
                10,
                60,
                images.BATON.img,
                (-5, self.length - 400),
                0
            )))
            start_note = entities.Note(self.length // 2, True)
            start_note.freeze_y(False)
            self.entity_list.append(start_note)
            self.entity_list.append(entities.NoteSpawner(self, start_note))
        else:  # lazer dodge
            self.length = game_states.HEIGHT
        self.entity_list.append(entities.InvulnerableObstacle(pos=(0, self.length), health=1))

    def tick(self):
        ret = super(MinigameArea, self).tick()
        if self.state == 0:  # setup game
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                self.state = 1
                end_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate), health=1)
                end_wall.final_load()
                self.entity_list.append(end_wall)
                if self.type == 0:  # obligatory fishing minigame
                    wave: list[tuple[Type[entities.Entity], Iterable]] = []
                    for i in range(self.difficulty // 10):
                        for i2 in range(10):
                            wave.append((entities.Fish, [self]))
                        wave = [(entities.MassDelayedDeploy, (60 * 10, self, wave))]
                    self.entity_list.append(entities.MassDelayedDeploy(0, wave[0][1][1], wave[0][1][2]))
                elif self.type == 1:  # notes
                    self.enforce_center = self.start_coordinate + self.length // 2
                else:  # lazer dodge
                    self.enforce_center = self.start_coordinate + self.length // 2
                    wave: list[tuple[Type[entities.Entity], Iterable]] = []
                    ticks_to_cross = self.length // 10
                    delay = 0
                    for i in range(self.difficulty // 10):
                        lazertype = self.random.randint(0, 2)
                        # print(f"wave: {["safety zones", "trackers", "juggle"][lazertype]}")
                        if lazertype == 0:  # safety zone(s)
                            charge_bonus = 10
                            delay = ticks_to_cross + charge_bonus
                            pre_safe_creation = [
                                (entities.Lazer, (y, ticks_to_cross + charge_bonus, charge_bonus, self))
                                for y in range(self.start_coordinate + 64, self.end_coordinate, 64)
                            ]
                            del pre_safe_creation[self.random.randint(0, len(pre_safe_creation) - 1)]
                            wave.extend(pre_safe_creation)
                        elif lazertype == 1:  # a bunch of trackers
                            tracker_delay = 30
                            delay = self.random.randint(5, 8)
                            for tracker_count in range(delay):
                                wave.append((
                                    entities.DelayedDeploy,
                                    (tracker_delay * tracker_count,
                                     self, entities.TrackingLazer,
                                     (self.start_coordinate + self.length * (tracker_count % 2),
                                      3 * tracker_delay, 15, self))
                                ))
                            delay *= tracker_delay
                        elif lazertype == 2:  # juggle 3 trackers
                            repeats = self.random.randint(3, 5)
                            tracker_delay = 30
                            for tracker_count in range(3):
                                wave.append((
                                    entities.DelayedDeploy,
                                    (tracker_delay * tracker_count,
                                     self, entities.TrackingLazer,
                                     (self.start_coordinate + self.length * (tracker_count % 2),
                                      3 * tracker_delay, 15, self, repeats))
                                ))
                            delay = tracker_delay * (repeats + 1)
                        wave = [(entities.MassDelayedDeploy, (delay, self, wave))]
                    self.entity_list.append(wave[0][0](*wave[0][1]))
        elif self.state == 1:  # in game
            if self.type == 0:
                self.enforce_center = game_states.DISTANCE
            if len(self.entity_list) == self.solved_entity_number:
                self.state = 2
                self.enforce_center = None
                if self.type == 1:
                    wall = entities.Obstacle(pos=(0, self.end_coordinate))
                    wall.hit(9, self)
                    self.entity_list[0] = wall
                else:
                    self.entity_list[0].die()
                    del self.entity_list[0]

        return ret

    def cross_boundary(self):
        if not MinigameArea.tutorial_given:
            MinigameArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "Ah, one of their sports.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "I don't know much about these, but there's some sort of goal.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "Try to figure out the game quick, before it kills you.",
                game_structures.FONTS[100]
            )


class BossArea(GameArea):
    """
    fight a boss!
    """

    tutorial_given = False

    def __init__(self, determiner, count):
        super(BossArea, self).__init__(game_states.HEIGHT * 4, seed=determiner)
        self.difficulty = count
        self.boss: bosses.Boss = None  # TODO make boss options
        self.state = 0
        self.entity_list.append(entities.InvulnerableObstacle(pos=(0, self.length), health=1))
        self.entity_list.append(self.boss)
        self.cooldown_ticks = 0

    def tick(self):
        ret = super().tick()
        if self.state == 0:
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                self.entity_list.append(entities.InvulnerableObstacle(pos=(0, self.start_coordinate), health=1))
        elif self.state == 1:
            if not self.boss.alive:
                del self.entity_list[0]
                self.state = 2
        elif self.state == 2:
            if self.cooldown_ticks <= 0:
                self.cooldown_ticks = 30
                for entity in self.entity_list:
                    entity.health -= 1
            self.cooldown_ticks -= 1
        return ret

    def cross_boundary(self):
        if not BossArea.tutorial_given:
            BossArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "You stumbled across one of their generals.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "I suppose it was inevitable.  Only one way to go, after all.",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "Any of their generals are more powerful than any creature you've seen so far,",
                game_structures.FONTS[100]
            )
            tutorials.add_text(
                "and they don't follow the same rules as you, I, or the others.",
                game_structures.FONTS[100]
            )


@make_async(with_lock=True)
@add_error_checking
def add_game_area():
    # print(game_states.LAST_AREA)
    determinator = hash(str(game_states.SEED + game_states.LAST_AREA))
    if game_states.LAST_AREA == 0:
        def first_area_tutorial():
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "Pick up the weapon and use it to destroy the wall.",
                game_structures.FONTS[100],
            )
            tutorials.add_text(
                "Hurry, you don't have much time.",
                game_structures.FONTS[100],
            )
            tutorials.add_text(
                "Stand on top of the item and use right or left mouse button to pick it up and use it.",
                game_structures.TUTORIAL_FONTS[90],
            )
            tutorials.add_text(
                "You'll need to use the weapon to kill the slime.  Beware, they move entirely randomly.",
                game_structures.FONTS[100],
            )

        area = GameArea(300, determinator)
        area.cross_boundary = first_area_tutorial
        area.entity_list.append(entities.Obstacle(pos=(0, 170)))
        area.entity_list.append(entities.ItemEntity(items.simple_stab(
            50,
            35,
            images.SIMPLE_SWORD.img,
            (0, 60)
        )))
    elif game_states.LAST_AREA == 1:
        area = GameArea(450, determinator)
        area.entity_list.append(entities.Obstacle(pos=(0, area.length), health=5))
        area.entity_list.append(entities.Slime((0, area.length // 2), area.random.randint(0, 2 ** 32 - 1)))
    elif game_states.LAST_AREA == 2:

        def last_tutorial_area():
            tutorials.clear_tutorial_text()
            tutorials.add_text(
                "There's another weapon here for you, but unfortunately I can't help you much.",
                game_structures.FONTS[100],
            )
            tutorials.add_text(
                "Good luck.  Maybe if you go far enough you'll be able to find something that will let you escape from this.",
                game_structures.FONTS[100],
            )

        area = GameArea(750, determinator)
        area.cross_boundary = last_tutorial_area
        area.entity_list.append(entities.Obstacle(pos=(0, + area.length), health=5))
        area.entity_list.append(entities.Slime((0, area.length // 3), area.random.randint(0, 2 ** 32 - 1)))
        area.entity_list.append(entities.Slime((0, 2 * area.length // 2), area.random.randint(0, 2 ** 32 - 1)))
        area.entity_list.append(entities.ItemEntity(items.simple_stab(
            100,
            10,
            images.SIMPLE_SPEAR.img,
            (15, 180),
            2
        )))
        game_states.AREA_QUEUE_MAX_LENGTH = 3
    else:
        # print(determinator, game_states.SEED + game_states.LAST_AREA)
        area = None
        typ = determinator % 64
        if typ < 2 and game_states.LAST_AREA < 40:
            typ = 2
        if typ < 4 and game_states.LAST_AREA < 20:
            typ = 4
        if typ < 13 and game_states.LAST_AREA < 10:
            typ = 13
        if typ < 33 and game_states.LAST_AREA < 4:
            typ = 33
        if typ == 0:  # 1/64
            # GOD room
            pass
        elif typ <= 1:  # 1/64
            # player room
            pass
        elif typ <= 3:  # 3/64
            # boss room
            pass
        elif typ <= 6:  # 3/64
            area = MinigameArea(determinator, game_states.LAST_AREA)
        elif typ <= 12:  # 6/64
            area = EnslaughtArea(determinator, game_states.LAST_AREA)
        elif typ <= 18:  # 6/64
            area = GiftArea(determinator, game_states.LAST_AREA)
        elif typ <= 32:  # 14/64
            area = BreakThroughArea(determinator, game_states.LAST_AREA)
        else:  # 32/64
            area = BasicArea(determinator, game_states.LAST_AREA)
        if area is None:
            area = GameArea(400)
    game_states.LAST_AREA += 1
    area.finalize()
    # print(game_states.LAST_AREA_END)
    game_structures.AREA_QUEUE.append(area)
    game_structures.make_save()


if __name__ == "__main__":
    from general_use import utility, game_structures
    import main

    game_states.PLACE = game_structures.PLACES.in_game

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
    game_states.AREA_QUEUE_MAX_LENGTH = 3

    game_structures.HANDS = [None, None]

    add_game_area()
    add_game_area()
    add_game_area().join()
    area = MinigameArea(90230923, 20)
    area.finalize()
    game_states.LAST_AREA_END = area.end_coordinate
    game_structures.AREA_QUEUE.append(area)

    while game_states.RUNNING:
        game_structures.SCREEN.fill(main.backdrop)
        game_states.PLACE.tick()
        utility.tick()