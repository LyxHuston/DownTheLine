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
from run_game import tutorials, entities, bosses, items, gameboard
from general_use.utility import make_async, add_error_checking, make_simple_always
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

    def __init__(self, index: int, length: int = 0, seed: int = None):
        self.index = index
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
            raise ValueError("I cry non-deterministic from set seed (every random call needs to be deterministic from"
                             "the original seed)")
        else:
            self.random = random.Random(seed)
        self.spawn_end = 0  # track which end to spawn a particle on
        self.__class__.last_spawned = index
        self.ender: entities.AreaStopper | None = None
        if self.__have_starter:
            self.starter: entities.AreaStarter | None = None

    __have_starter = False

    def __init_subclass__(cls, have_starter: bool = False):
        super().__init_subclass__()
        cls.__have_starter = have_starter

    seen = False

    def final_load(self):
        if not self.__class__.seen:
            self.__class__.seen = True
            self.start_tutorial()
        for entity in self.entity_list:
            entity.final_load()

    first_allowed_spawn = 0
    last_spawned = 0
    required_wait_interval = 0
    required_previous = []
    @classmethod
    def allowed_at(cls, index: int) -> bool:
        if cls.first_allowed_spawn > index or cls.last_spawned + cls.required_wait_interval >= index:
            return False
        return all(map(lambda area_type: area_type.last_spawned > 0, cls.required_previous))

    def start_tutorial(self):
        pass

    def draw_particles(self):
        remove_list = deque()
        for particle in self.particle_list:
            if particle.tick():
                particle.draw()
            else:
                remove_list.append(particle)
        for particle in remove_list:
            self.particle_list.remove(particle)
            # prevent
            particle.reset_id_check()

    def draw(self):
        pass

    region_length = 32000
    taper_length = 100

    def tick(self):
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
        if not self.boundary_crossed and game_states.DISTANCE > self.start_coordinate:
            self.boundary_crossed = True
            self.cross_boundary()

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
        if self.__have_starter:
            self.starter: entities.Entity = entities.AreaStarter(self)
            self.entity_list.insert(0, self.starter)
        self.ender = entities.AreaStopper(self)
        self.entity_list.append(self.ender)
        self.entity_list.sort(key=lambda e: e.y)

    def cleanup(self):
        if self.entity_list is not None:
            for entity in self.entity_list:
                entity.cleanup()
        for particle in self.particle_list:
            particle.reset_id_check()

    def get_allowable(self):
        allowable_entities = []
        for entry, threshold in BasicArea.allowable_thresh_holds:
            if threshold > self.index:
                return allowable_entities
            if not isinstance(self, BasicArea):
                if not self.previously_seen(entry):
                    return allowable_entities
            allowable_entities.append([entry, 0])
        return allowable_entities

    def previously_seen(self, entity: entities.Entity):
        return entity.first_occurs or self.index < entity.first_occurs

    def num_entities(self):
        if not self.__have_starter:
            return 0
        return self.ender.index - self.starter.index - 1

    def get_entity_snapshot(self) -> list:
        if not self.__have_starter:
            return []
        return gameboard.ENTITY_BOARD[self.starter.index + 1: self.ender.index]


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    allowable_thresh_holds = ((entities.Slime, 0), (entities.Crawler, 5), (entities.Fencer, 10), (entities.Archer, 10),
                              (entities.Knight, 15))
    # allowable_thresh_holds = [(entities.Knight, 0)]

    def __init__(self, determiner, count):
        super().__init__(count, seed=determiner)
        self.length = 300 + math.floor(math.log2(count)) * 150
        self.difficulty = count
        allowance = count
        allowable_entities = self.get_allowable()
        num = 3
        while allowance > 0:
            index = (determiner % num) % len(allowable_entities)
            num += 1
            entity: entities.Entity = allowable_entities[index][0]
            if entity.first_occurs:
                allowance -= entity.cost + allowable_entities[index][1]
                allowable_entities[index][1] += 1
                self.entity_list.append(entity.make(determiner, self))
            else:
                self.entity_list.clear()
                self.length = 1500
                add = entity.make(determiner, self)
                entity.first_occurs = count
                add.y = self.length // 2
                self.entity_list.append(add)
                self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=5))
                self.entity_list.append(entities.Obstacle(pos=(0, self.length // 4), health=5))

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
    first_allowed_spawn = 4
    required_wait_interval = 2

    def __init__(self, determiner: int, count: int):
        super().__init__(count, seed=determiner)
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
        allowable_entities = self.get_allowable()
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
    first_allowed_spawn = 4
    required_previous = [BreakThroughArea]
    required_wait_interval = 6

    def __init__(self, determiner, count):
        super().__init__(count, seed=determiner)
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
    first_allowed_spawn = 10
    required_previous = [GiftArea]  # BreakThroughArea implicit
    required_wait_interval = 5

    def __init__(self, determiner, count):
        super().__init__(count, seed=determiner)
        self.difficulty = count
        self.current_difficulty = count
        self.length = game_states.HEIGHT * 4
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)
        self.entity_list.append(self.end_wall)
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
                start_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate))
                start_wall.final_load()
                gameboard.NEW_ENTITIES.append(start_wall)
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
                self.end_wall.alive = False
                self.entity_list = self.get_entity_snapshot()
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
            gameboard.NEW_ENTITIES.append(entities.Spawner(
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
                gameboard.NEW_ENTITIES.append(entities.DelayedDeploy(
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
                gameboard.NEW_ENTITIES.append(entities.Fish(self))
                self.current_difficulty += 2
        elif target_change < 30:
            # print("Spawning")
            allowable_entities = self.get_allowable()
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
                gameboard.NEW_ENTITIES.append(made_entity)
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
                gameboard.NEW_ENTITIES.append(spawner)
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
    first_allowed_spawn = 10
    required_wait_interval = 7

    def __init__(self, determiner, count):
        super().__init__(count, seed=determiner)
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
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)
        self.entity_list.append(self.end_wall)

    def tick(self):
        ret = super(MinigameArea, self).tick()
        if self.state == 0:  # setup game
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                self.state = 1
                end_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate), health=1)
                end_wall.final_load()
                gameboard.NEW_ENTITIES.append(end_wall)
                if self.type == 0:  # obligatory fishing minigame
                    wave: list[tuple[Type[entities.Entity], Iterable]] = []
                    for i in range(self.difficulty // 10):
                        for i2 in range(10):
                            wave.append((entities.Fish, [self]))
                        wave = [(entities.MassDelayedDeploy, (60 * 10, self, wave))]
                    gameboard.NEW_ENTITIES.append(entities.MassDelayedDeploy(0, wave[0][1][1], wave[0][1][2]))
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
                    gameboard.NEW_ENTITIES.append(wave[0][0](*wave[0][1]))
        elif self.state == 1:  # in game
            if self.type == 0:
                self.enforce_center = game_states.DISTANCE
            if self.num_entities() == self.solved_entity_number:
                self.state = 2
                self.enforce_center = None
                if self.type == 1:
                    wall = entities.Obstacle(pos=(0, self.end_coordinate))
                    wall.hit(9, self)
                    gameboard.NEW_ENTITIES.append(wall)
                self.end_wall.alive = False

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
    first_allowed_spawn = 20
    required_previous = [EnslaughtArea]  # GiftArea and BreakThroughArea implicit
    required_wait_interval = 15

    def __init__(self, determiner, count):
        super(BossArea, self).__init__(count, game_states.HEIGHT * 4, seed=determiner)
        self.difficulty = count
        self.boss: bosses.Boss | None = None  # TODO make boss options
        self.state = 0
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)
        self.entity_list.append(self.end_wall)
        self.entity_list.append(self.boss)
        self.cooldown_ticks = 0

    def tick(self):
        ret = super().tick()
        if self.state == 0:
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                gameboard.NEW_ENTITIES.append(entities.InvulnerableObstacle(pos=(0, self.start_coordinate), health=1))
        elif self.state == 1:
            if not self.boss.alive:
                self.end_wall.alive = False
                self.entity_list = self.get_entity_snapshot()
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

        area = GameArea(0, 300, determinator)
        area.cross_boundary = first_area_tutorial
        area.entity_list.append(entities.Obstacle(pos=(0, 170)))
        area.entity_list.append(entities.ItemEntity(items.simple_stab(
            50,
            35,
            images.SIMPLE_SWORD.img,
            (0, 60)
        )))
    elif game_states.LAST_AREA == 1:
        area = GameArea(1, 450, determinator)
        area.entity_list.append(entities.Obstacle(pos=(0, area.length), health=5))
        area.entity_list.append(entities.Slime((0, area.length // 2), area.random.randint(0, 2 ** 32 - 1)))

        entities.Slime.first_occurs = 1
        entities.Slime.seen = True
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

        area = GameArea(2, 750, determinator)
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
        area_type: Type[GameArea]
        threshold: int
        for area_type, threshold in area_thresholds:
            if typ <= threshold and area_type.allowed_at(game_states.LAST_AREA):
                area = area_type(determinator, game_states.LAST_AREA)
                break
        if area is None:
            area = GameArea(game_states.LAST_AREA, length=400)
    game_states.LAST_AREA += 1
    area.finalize()
    # print(game_states.LAST_AREA_END)
    with game_structures.AREA_QUEUE_LOCK:
        game_structures.AREA_QUEUE.append(area)
    game_structures.make_save()


area_thresholds = (
    (BasicArea, 0),  # GOD room (40+) TODO
    (BasicArea, 1),  # player room (20+) TODO
    (BasicArea, 3),  # boss room (20+) TODO
    (MinigameArea, 6),  # minigame area (10+)
    (EnslaughtArea, 12),  # enslaught area (10+)
    (GiftArea, 18),  # gift area (4+)
    (BreakThroughArea, 32),  # breakthrough area (4+)
    (BasicArea, 64)  # basic area (0+)
)


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