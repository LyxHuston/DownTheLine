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
import enum
import random

import pygame

from data import game_states, images, switches
from run_game import tutorials, entities, bosses, items, gameboard
from general_use.utility import make_async, add_error_checking, make_simple_always
from general_use import game_structures
import math
from collections import deque
from typing import Type, Iterable, Callable


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
    def start_coordinate(self) -> int:
        return self.__start_coordinate

    @start_coordinate.setter
    def start_coordinate(self, val: int):
        self.__start_coordinate = val

    @property
    def end_coordinate(self) -> int:
        return self.start_coordinate + self.length

    def __init__(self, index: int, length: int = None, seed: int = None, customized: bool = False):
        if not hasattr(self, "customized"):
            self.customized = customized
        self.index: int = index
        if not hasattr(self, "difficulty"):
            self.difficulty = index
        self.enforce_center: int | None = None
        self.start_coordinate: int = 0
        if length is not None:
            self.length: int = length
        self.initialized: bool = False
        self.boundary_crossed: bool = False
        self.entity_list: list[entities.Entity] | None = []
        self.particle_maker: Callable[[tuple[int, int]], entities.Particle] = entities.VOID_PARTICLES
        self.particle_list: set = set()
        if seed is None:
            raise ValueError("I cry non-deterministic from set seed (every random call needs to be deterministic from"
                             "the original seed)")
        else:
            self.seed = seed
            self.random = random.Random(seed)
        self.spawn_end = 0  # track which end to spawn a particle on
        self.__class__.last_spawned = index
        self.remove_preceding_obstacle: bool = False
        self.ender: entities.AreaStopper | None = None
        if self.__have_starter:
            self.starter: entities.AreaStarter | None = None
        if not self.customized:
            self.determine_parts()

    __have_starter = False

    def __new_init(self, *args, customized: bool = False, **kwargs):
        self.customized = customized
        self.__class__.__old_init(self, *args, **kwargs)

    def __init_subclass__(cls, have_starter: bool = False):
        if cls.__init__ is not GameArea.__init__:
            cls.__old_init = cls.__init__
            cls.__init__ = cls.__new_init

        super().__init_subclass__()
        cls.tutorial_given = False
        cls.__have_starter = have_starter

    seen = False

    def final_load(self):
        if self.remove_preceding_obstacle:
            i = -1
            if isinstance(gameboard.ENTITY_BOARD[i], entities.AreaStopper):
                i -= 1
            if isinstance(gameboard.ENTITY_BOARD[i], entities.Obstacle):
                gameboard.ENTITY_BOARD[i].alive = False
        if not self.__class__.seen:
            self.__class__.seen = True
            self.start_tutorial()

    first_allowed_spawn = 0
    last_spawned = 0
    required_wait_interval = 0
    required_previous = []
    @classmethod
    def allowed_at(cls, index: int) -> bool:
        if cls.first_allowed_spawn > index or cls.last_spawned + cls.required_wait_interval >= index:
            return False
        return all(map(lambda area_type: area_type.last_spawned > 0, cls.required_previous))

    @classmethod
    def required_at(cls, index: int) -> bool:
        return cls.last_spawned + cls.required_wait_interval * 2 <= index

    def start_tutorial(self):
        pass

    def draw_particles(self):
        for particle in self.particle_list:
            particle.draw()

    def draw(self):
        # if self.player_in():
        #     render = game_structures.FONTS[128].render(
        #         str(self.num_entities()),
        #         False,
        #         (255, 255, 255)
        #     )
        #     game_structures.SCREEN.blit(
        #         render,
        #         (game_states.WIDTH - render.get_width(), (1 - switches.TUTORIAL_TEXT_POSITION) * tutorials.display_height)
        #     )
        pass

    region_length = 32000
    taper_length = 100

    def tick(self):
        if len(gameboard.PARTICLE_BOARD) + len(self.particle_list) < self.length:
            region = 0
            while region * self.region_length + self.taper_length < self.length:  # spawn particles for middle regions
                height = self.start_coordinate + self.random.randint(0, self.region_length - 1) + region * self.region_length
                if height > self.end_coordinate - self.taper_length // 2:
                    break
                # noinspection PyTypeChecker
                self.particle_list.add(self.particle_maker((
                    self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                    height
                )))
                region += 1
            self.spawn_end = not self.spawn_end
            if self.random.randint(0, self.region_length // self.taper_length) == 0:
                # noinspection PyTypeChecker
                self.particle_list.add(self.particle_maker((
                        self.random.randint(-game_states.WIDTH // 2, game_states.WIDTH // 2),
                        self.start_coordinate + self.length // 2 + (self.spawn_end * 2 - 1) * (
                                self.length +
                                self.taper_length - round(math.sqrt(1 + 8 * self.random.randint(0, (self.taper_length + 1) * self.taper_length // 2) - 1) - 1)
                        ) // 2
                )))
            gameboard.particle_set_tick(self.particle_list)
        # print(len(self.particle_list))
        if not self.boundary_crossed and game_states.DISTANCE > self.start_coordinate:
            self.boundary_crossed = True
            self.cross_boundary()

    def player_in(self) -> bool:
        return 0 <= game_states.DISTANCE - self.start_coordinate <= self.length

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

    allowable_thresh_holds = (
        (entities.Slime, 0),
        (entities.Crawler, 5),
        (entities.Fencer, 10),
        (entities.Archer, 10),
        (entities.Knight, 15)
    )

    def get_allowable(self):
        allowable_entities = []
        for entry, threshold in self.allowable_thresh_holds:
            if threshold > self.index:
                return allowable_entities
            if not isinstance(self, BasicArea):
                if not self.previously_seen(entry):
                    return allowable_entities
            allowable_entities.append([entry, 0])
        return allowable_entities

    def previously_seen(self, entity: entities.Entity):
        return entity.first_occurs and self.index > entity.first_occurs

    def num_entities(self):
        if not self.__have_starter:
            return 0
        return self.ender.index - self.starter.index - 1

    def get_entity_snapshot(self) -> list:
        if not self.__have_starter:
            return []
        return gameboard.ENTITY_BOARD[self.starter.index + 1: self.ender.index]

    def determine_parts(self):
        raise NotImplementedError(f"method 'determine parts' not implemented for class '{self.__class__.__name__}'")

    def make(self, *args, **kwargs):
        raise NotImplementedError(f"method 'make' not implemented for class '{self.__class__.__name__}'")


class BasicArea(GameArea):
    """
    a basic fight area.  Fight a few monsters and continue.
    """

    def __init__(self, determiner, count):
        self.difficulty = count
        super().__init__(count, seed=determiner, length=300 + math.floor(math.log2(count)) * 150)

    def determine_parts(self):
        allowance = self.difficulty
        allowable_entities = self.get_allowable()
        entity_list = []
        num = 3
        while allowance > 0:
            index = (self.seed % num) % len(allowable_entities)
            num += 1
            entity: Type[entities.Entity] = allowable_entities[index][0]
            if entity.first_occurs:
                allowance -= entity.cost + allowable_entities[index][1]
                allowable_entities[index][1] += 1
                entity_list.append(entity)
            else:
                add = entity.make(self.seed, self)
                entity.first_occurs = self.index
                self.make([add], True)
                return
        self.make([entity.make(self.seed, self) for entity in entity_list], False)

    def make(self, entity_list: list[entities.Entity], tutorial: bool):
        if tutorial:
            add = entity_list[0]
            self.length = 1500
            add.y = self.length // 2
            self.entity_list.append(add)
            self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=5))
            self.entity_list.append(entities.Obstacle(pos=(0, self.length // 4), health=5))

            def first_see_of_entity():
                if not add.tutorial_given:
                    add.tutorial_given = True
                    tutorials.clear_tutorial_text()
                    tutorials.add_texts([(add.tutorial_text, game_structures.FONTS[100])])

            self.cross_boundary = first_see_of_entity
        else:
            self.entity_list.extend(entity_list)


    # methods to keep rarer/more interesting areas from getting overshadowed
    @classmethod
    def allowed_at(cls, index: int) -> bool:
        return True

    @classmethod
    def required_at(cls, index: int) -> bool:
        return False


class BreakThroughArea(GameArea):
    """
    area that continually spawns monsters, objective to break through them and
    destroy the wall at the end
    """

    first_allowed_spawn = 4
    required_wait_interval = 3

    def __init__(self, determiner: int, count: int):
        self.difficulty = count
        super().__init__(count, seed=determiner, length=game_states.HEIGHT // 2 + math.floor(math.log2(count)) * 150)
        self.entity_list.append(entities.Obstacle(pos=(0, self.length)))

    def determine_parts(self):
        allowance = self.difficulty
        spawner_list = []
        while allowance > 0:
            spawner = entities.Spawner.make(self.seed + allowance, self)
            spawner_list.append(spawner)
            if spawner.limit is None:
                allowance -= 2 * (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
            else:
                allowance -= 2 * (spawner.limit + 1) * spawner.entity.cost ** 2
        allowance = self.difficulty // 3
        allowable_entities = self.get_allowable()
        num = 3
        entity_list = []
        while allowance > 0:
            index = (self.seed % num) % len(allowable_entities)
            num += 1
            entity = allowable_entities[index][0]
            allowance -= entity.cost + allowable_entities[index][1] ** 2
            allowable_entities[index][1] += 1
            entity_list.append(entity.make(self.seed + num, self))
        self.make(spawner_list, entity_list)

    def make(self, spawner_list: list[entities.Spawner], entity_list: list[entities.Entity]):
        self.entity_list = spawner_list + entity_list

    def cross_boundary(self):
        if not BreakThroughArea.tutorial_given:
            BreakThroughArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
	                "Oh, they left their spawners active.",
	                game_structures.FONTS[100]
	            ), (
	                "Irresponsible for the fabric of reality, but oh well.",
	                game_structures.FONTS[100]
	            ), (
	                "You'll need to kill them quick enough to break through.",
	                game_structures.FONTS[100]
	            )
            ])


class GiftArea(GameArea):
    """
    gives player a new item and area to practice it with.
    """

    first_allowed_spawn = 4
    required_previous = [BreakThroughArea]
    required_wait_interval = 2

    def __init__(self, determiner, count):
        self.remove_preceding_obstacle = True
        self.difficulty = count
        super().__init__(count, seed=determiner, length=1500)

    experiment_area_length = 1200

    def determine_parts(self):
        self.make(
            items.make_random_reusable(self.random, (0, 1 * self.experiment_area_length // 3)),
            items.make_random_reusable(self.random, (0, 2 * self.experiment_area_length // 3))
        )

    def make(self, gift1: items.Item, gift2: items.Item):
        spawn = entities.Spawner.make(self.seed, self)
        spawn.y += self.experiment_area_length
        self.length += self.experiment_area_length
        self.entity_list.append(spawn)
        self.entity_list.append(entities.Obstacle(pos=(0, self.experiment_area_length), health=1))
        self.entity_list.append(entities.Obstacle(pos=(0, self.length), health=10))
        self.entity_list.append(entities.ItemEntity(gift1))
        self.entity_list.append(entities.ItemEntity(gift2))

    def cross_boundary(self):
        if not GiftArea.tutorial_given:
            GiftArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
                    "New items for you!",
                    game_structures.FONTS[100]
                ), (
                    "I'm not certain if it will be more powerful than your current ones.",
                    game_structures.FONTS[100]
                ), (
                    "Hold space to switch items.",
                    game_structures.TUTORIAL_FONTS[90],
                )
            ])


class EnslaughtAreaEventType(enum.Enum):
    ItemDuplicator = 0
    Lazers = 10
    Fish = 15
    Enemies = 30
    Spawners = math.inf


class EnslaughtAreaEvent:

    def __init__(self, typ: EnslaughtAreaEventType, target_change: int, area: GameArea):
        self.change_difficulty = 0
        self.add_entities = []

        def modify_entity(entity):
            entity.y += area.start_coordinate

        if typ is EnslaughtAreaEventType.ItemDuplicator:
            pos = (
                area.random.randint(100, game_states.WIDTH // 2) * (area.random.randint(0, 1) * 2 - 1),
                area.random.randint(area.start_coordinate + 100, area.end_coordinate - 100)
            )
            self.add_entities.append(entities.Spawner(
                pos,
                1,
                0,
                entities.make_item_duplicator(items.make_random_single_use(area.random, pos)),
                (0, None),
                1
            ))
            self.change_difficulty -= 20
        elif typ is EnslaughtAreaEventType.Lazers:
            for i in range(target_change):
                self.add_entities.append(entities.DelayedDeploy(
                    i * 60,
                    area,
                    entities.TrackingLazer,
                    (
                        (entities.TrackingLazer.TOP, entities.TrackingLazer.BOTTOM)[i % 2],
                        60,
                        60,
                        area
                    )
                ))
        elif typ is EnslaughtAreaEventType.Fish:
            fish = target_change // 3
            for i in range(fish):
                self.add_entities.append(entities.Fish(area))
            self.change_difficulty += 2 * fish
        elif typ is EnslaughtAreaEventType.Enemies:
            allowable_entities = area.get_allowable()
            num = 3
            determiner = area.random.randint(0, 2 ** 31)
            while target_change > 0:
                index = (determiner % num) % len(allowable_entities)
                num += 1
                e = allowable_entities[index][0]
                target_change -= e.cost + allowable_entities[index][1] ** 2
                self.change_difficulty += e.cost + allowable_entities[index][1] ** 2
                allowable_entities[index][1] += 1
                made_entity = e.make(determiner, area)
                made_entity.y += area.start_coordinate
                self.add_entities.append(made_entity)

            def modify_entity(entity):
                entity.y += area.start_coordinate
                if game_states.CAMERA_BOTTOM + entity.height < entity.y < game_states.CAMERA_BOTTOM + game_states.HEIGHT - entity.height:
                    if game_states.DISTANCE - area.start_coordinate < area.length // 2:
                        entity.y = area.end_coordinate - 100
                    else:
                        entity.y = area.start_coordinate + 100

        elif typ is EnslaughtAreaEventType.Spawners:
            for i in range(target_change // 15):
                spawner = entities.Spawner.make(area.random.randint(0, 2 ** 31), area)
                if spawner.limit is None:
                    self.change_difficulty += (spawner.delay // 200 + 1) * (spawner.entity.cost + 1) ** 2
                else:
                    self.change_difficulty += (spawner.limit + 1) * spawner.entity.cost ** 2
                spawner.y += area.start_coordinate
                self.add_entities.append(spawner)
        self.modify_entity = modify_entity

    def get_entities(self):
        for entity in self.add_entities:
            self.modify_entity(entity)
        return self.add_entities


class EnslaughtArea(GameArea, have_starter=True):
    """
    game area that is just surviving a bunch of enemies
    """

    first_allowed_spawn = 10
    required_previous = [GiftArea]  # BreakThroughArea implicit
    required_wait_interval = 4

    def __init__(self, determiner, count):
        self.difficulty = count
        self.length = game_states.HEIGHT * 4
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)
        self.state = 0  # 0: not started 1: in progress 2: finished, killing off entities
        self.timer = 0
        self.num_events = 0
        self.max = 0
        self.cooldown_ticks = 0
        self.events = deque()
        super().__init__(count, seed=determiner)

    cooldown = 300

    def determine_parts(self):
        event_list = deque()
        current_difficulty = self.difficulty
        timer = 30 * 60 + 120 * math.floor(math.log2(self.difficulty))
        for _ in range(timer // self.cooldown):
            target_change = (self.difficulty - current_difficulty) // 2 + 8 * self.random.randint(-1, 3)
            for typ in EnslaughtAreaEventType:
                do_typ = typ
                if typ.value > target_change:
                    new_event = EnslaughtAreaEvent(do_typ, target_change, self)
                    current_difficulty += new_event.change_difficulty
                    event_list.append(new_event)
                    break
        self.make(event_list)

    def make(self, event_list: deque[EnslaughtAreaEvent]):
        self.timer = (len(event_list) + 1) * self.cooldown
        self.max = self.timer
        self.num_events = len(event_list)
        self.events = event_list
        self.entity_list.append(self.end_wall)

    def draw(self):
        super(EnslaughtArea, self).draw()
        if self.state == 1:
            max_size = 3 * game_states.WIDTH // 8
            width = max_size * self.timer / self.max
            outline = 5
            y = 30 + outline
            if tutorials.display is not None and not switches.TUTORIAL_TEXT_POSITION:
                y += tutorials.display_height
            pygame.draw.line(
                game_structures.SCREEN,
                (255, 255, 255),
                (game_states.WIDTH // 2 - (width + outline), y),
                (game_states.WIDTH // 2 + (width + outline), y),
                20 + outline * 2
            )
            pygame.draw.line(
                game_structures.SCREEN,
                (0, 0, 0),
                (game_states.WIDTH // 2 - width, y),
                (game_states.WIDTH // 2 + width, y),
                20
            )
            step = max_size / (self.num_events + 1)
            for d in (1, -1):
                for i in range(1, 1 + self.num_events):
                    center = step * i
                    pygame.draw.circle(
                        game_structures.SCREEN,
                        (255, 255, 255),
                        (game_states.WIDTH // 2 + d * center, y),
                        15 + outline
                    )
                    pygame.draw.circle(
                        game_structures.SCREEN,
                        (0, 0, 0),
                        (game_states.WIDTH // 2 + d * center, y),
                        15
                    )

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
            if (self.max - self.timer) % self.cooldown == 0:
                self.event()
            if self.timer <= 0:
                self.state = 2
                self.cooldown_ticks = 0
                self.end_wall.alive = False
                self.entity_list = [e for e in self.get_entity_snapshot() if not e.allied_with_player]
        elif self.state == 2:
            if self.cooldown_ticks <= 0:
                self.cooldown_ticks = 30
                for entity in self.entity_list:
                    entity.health -= 1
            self.cooldown_ticks -= 1
        return ret

    def event(self):
        if self.events:
            gameboard.NEW_ENTITIES.extend(self.events.popleft().get_entities())

    def cross_boundary(self):
        if not EnslaughtArea.tutorial_given:
            EnslaughtArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
                    "Oh, it's one of these places.",
                    game_structures.FONTS[100]
                ), (
                    "Challenges will come in waves.  You won't get time to rest.  Good luck.",
                    game_structures.FONTS[100]
                )
            ])


from run_game.minigames import Minigame


class MinigameArea(GameArea, have_starter=True):
    first_allowed_spawn = 10
    required_wait_interval = 6

    class States(enum.Enum):
        pre_init = 0
        running = 1
        done = 2

    def __init__(self, determiner, count):
        self.difficulty = max(count, 10)
        self.state = MinigameArea.States.pre_init
        self.data_pack = None
        self.type: [Type[Minigame]] = None
        self.end_wall = None
        super().__init__(count, seed=determiner)

    def determine_parts(self):
        self.make(self.random.choice(Minigame.minigames))

    def make(self, typ: Type[Minigame]):
        self.type = typ
        self.type.init(self)
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)
        self.entity_list.append(self.end_wall)

    def draw(self):
        super().draw()
        if self.state is MinigameArea.States.running:
            self.type.draw(self)

    def tick(self):
        ret = super(MinigameArea, self).tick()
        if self.state is MinigameArea.States.pre_init:  # setup game
            if game_states.DISTANCE > self.start_coordinate + self.length // 2:
                self.state = MinigameArea.States.running
                end_wall = entities.InvulnerableObstacle(pos=(0, self.start_coordinate + 1), health=1)
                end_wall.final_load()
                gameboard.NEW_ENTITIES.append(end_wall)
                self.type.setup(self)
        elif self.state is MinigameArea.States.running:  # in game
            self.type.tick(self)
            if self.type.check_win(self):
                self.state = MinigameArea.States.done
                self.enforce_center = None
                self.type.finish(self)
                self.end_wall.alive = False

        return ret

    def cross_boundary(self):
        if not MinigameArea.tutorial_given:
            MinigameArea.tutorial_given = True
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
                    "Ah, one of their sports.",
                    game_structures.FONTS[100]
                ), (
                    "I don't know much about these, but there's some sort of goal.",
                    game_structures.FONTS[100]
                ), (
                    "Try to figure out the game quick, before it kills you.",
                    game_structures.FONTS[100]
                )
            ])


class BossArea(GameArea):
    """
    fight a boss!
    """

    first_allowed_spawn = 20
    required_previous = [EnslaughtArea]  # GiftArea and BreakThroughArea implicit
    required_wait_interval = 15

    def __init__(self, determiner, count):
        super(BossArea, self).__init__(count, game_states.HEIGHT * 4, seed=determiner)
        self.difficulty = count
        self.boss: bosses.Boss | None = None  # TODO make boss options
        self.state = 0
        self.end_wall = entities.InvulnerableObstacle(pos=(0, self.length), health=1)

    def determine_parts(self):
        self.make(None) # TODO

    def make(self, boss: bosses.Boss | None):
        self.boss = boss
        self.entity_list.append(self.end_wall)
        self.entity_list.append(self.boss)

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
            tutorials.add_texts([
                (
                    "You stumbled across one of their generals.",
                    game_structures.FONTS[100]
                ), (
                    "I suppose it was inevitable.  Only one way to go, after all.",
                    game_structures.FONTS[100]
                ), (
                    "Any of their generals are more powerful than any creature you've seen so far,",
                    game_structures.FONTS[100]
                ), (
                    "and they don't follow the same rules as you, I, or the others.",
                    game_structures.FONTS[100]
                )
            ])


guaranteed_type: Type[GameArea] | None = None


def get_determiner():
    return hash(str(game_states.SEED + game_states.LAST_AREA))


@make_async(with_lock=True)
@add_error_checking
def add_game_area():
    # print(game_states.LAST_AREA)
    area: GameArea
    determinator = get_determiner()
    if game_states.LAST_AREA == 0:
        def first_area_tutorial():
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
                    "Pick up the weapon and use it to destroy the wall.",
                    game_structures.FONTS[100],
                ), (
                    "Hurry, you don't have much time.",
                    game_structures.FONTS[100],
                ), (
                    "Stand on top of the item and use right or left mouse button to pick it up and use it.",
                    game_structures.TUTORIAL_FONTS[90],
                ), (
                    "You'll need to use the weapon to kill the slime.  Beware, they move entirely randomly.",
                    game_structures.FONTS[100],
                )
            ])

        area = GameArea(0, 450, determinator, customized=True)
        area.cross_boundary = first_area_tutorial
        area.entity_list.append(entities.Obstacle(pos=(0, 450)))
        area.entity_list.append(entities.ItemEntity(items.simple_stab(
            50,
            35,
            images.SIMPLE_SWORD.img,
            images.SIMPLE_SWORD.outlined_img,
            (-images.SIMPLE_SWORD.outlined_img.get_width() // 4, 60)
        )))

        # area.entity_list.append(entities.ItemEntity(items.simple_stab(
        #     50,
        #     35,
        #     images.SIMPLE_DAGGER.img,
        #     images.SIMPLE_DAGGER.outlined_img,
        #     (-images.SIMPLE_DAGGER.outlined_img.get_width() // 4, 120)
        # )))
        # area.entity_list.append(entities.ItemEntity(items.simple_shield((0, 180))))
        # area.entity_list.append(
        #     entities.ItemEntity(items.random_simple_throwable(20, area.random, (0, 240))))  # throwable
        # area.entity_list.append(entities.ItemEntity(items.bow(20, area.random, (0, 300))))  # bow
        # area.entity_list.append(entities.ItemEntity(items.boomerang(20, area.random, (0, 360))))  # boomerang
        # area.entity_list.append(entities.ItemEntity(items.hammer(20, area.random, (0, 420))))  # hammer
    elif guaranteed_type is not None:
        area = guaranteed_type(determinator, game_states.LAST_AREA + guaranteed_type.first_allowed_spawn)
    elif game_states.LAST_AREA == 1:
        area = GameArea(1, 450, determinator, customized=True)
        area.entity_list.append(entities.Obstacle(pos=(0, area.length), health=5))
        area.entity_list.append(entities.Slime((0, area.length // 2), area.random.randint(0, 2 ** 32 - 1)))

        entities.Slime.first_occurs = 1
        entities.Slime.seen = True
    elif game_states.LAST_AREA == 2:

        def last_tutorial_area():
            tutorials.clear_tutorial_text()
            tutorials.add_texts([
                (
                    "There's another weapon here for you, but unfortunately I can't help you much.",
                    game_structures.FONTS[100],
                ), (
                    "Good luck.  Maybe if you go far enough you'll be able to find something that will let you escape from this.",
                    game_structures.FONTS[100],
                )
            ])

        area = GameArea(2, 750, determinator, customized=True)
        area.cross_boundary = last_tutorial_area
        area.entity_list.append(entities.Obstacle(pos=(0, + area.length), health=5))
        area.entity_list.append(entities.Slime((0, area.length // 3), area.random.randint(0, 2 ** 32 - 1)))
        area.entity_list.append(entities.Slime((0, 2 * area.length // 2), area.random.randint(0, 2 ** 32 - 1)))
        area.entity_list.append(entities.ItemEntity(items.simple_stab(
            100,
            10,
            images.SIMPLE_SPEAR.img,
            images.SIMPLE_SPEAR.outlined_img,
            (-images.SIMPLE_SPEAR.outlined_img.get_width() // 4, 180),
            2
        )))
    else:
        # print(determinator, game_states.SEED + game_states.LAST_AREA)
        typ = determinator % 64
        area_type: Type[GameArea]
        threshold: int
        for area_type, threshold in area_thresholds:
            if area_type.allowed_at(game_states.LAST_AREA) and (typ <= threshold or area_type.required_at(game_states.LAST_AREA)):
                area = area_type(determinator, game_states.LAST_AREA)
                break
    game_states.LAST_AREA += 1
    area.finalize()
    # print(game_states.LAST_AREA_END)
    game_structures.NEW_AREAS.append(area)


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
