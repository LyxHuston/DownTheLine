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

minigame functions
"""
from typing import Callable, Iterable, Type

import pygame

from general_use import utility, game_structures
from run_game import entities, items, gameboard, tutorials
from data import game_states, images, switches


class Minigame:

	minigames = []

	funcs = ("init", "setup", "tick", "check_win", "finish", "draw")

	def __init__(
			self,
			*args,
			**kwargs
	):
		if len(args) > len(self.funcs):
			raise TypeError(f"{self.__init__} takes {len(self.funcs)} positional argument but {len(args)} were given")
		for name in kwargs:
			if name in self.funcs:
				raise TypeError(f"{self.__init__} got an unexpected keyword argument '{name}'")
		for i, name in enumerate(self.funcs):
			if i < len(args) and f"{name}_func" in kwargs:
				raise TypeError(f"{self.__init__} got multiple values for argument '{name}_func'")
			setattr(self, name, args[i] if i < len(args) else kwargs.get(f"{name}_func", utility.passing))

		self.minigames.append(self)

	maker = staticmethod(lambda name: lambda self, val: (setattr(self, name, val), val)[1])

	for name in funcs:
		# def __set(self, val: Callable, name=name):
		# 	setattr(self, name, val)
		# 	return val
		# exec(f"def set_{name}(self, val: Callable):setattr(self, \"{name}\", val);return val")
		locals()[f"set_{name}"] = maker(name)
		# setattr(cls, f"set_{name}", maker(name))
	# locals()[f"set_{name}"] = __set
	# del __set
	del maker
	del name

	def __repr__(self):
		return "Minigame[" + ", ".join(
			f"{name}: {getattr(self, name).__name__}"
			for name in self.funcs
			if getattr(self, name) is not utility.passing
		) + "]"


fish = Minigame()
notes = Minigame()
lazers = Minigame()

Minigame.minigames = [notes]


def entity_tracker(area): return area.data_pack[0]


def preset(area, *args): area.data_pack = list(args)


@notes.set_tick
def filter_entities(area):
	area.data_pack[0][:] = filter(lambda e: e.alive, area.data_pack[0])


def set_length(factor: float):
	def inner(area):
		area.length = game_states.HEIGHT * factor
	inner.__name__ = f"set_length_{factor}"
	inner.__qualname__ = inner.__qualname__.replace("inner", str(factor))
	return inner


fish.set_init(set_length(2))
lazers.set_init(set_length(1))


@notes.set_check_win
@fish.set_check_win
def empty_area(area):
	return not entity_tracker(area)


@fish.set_setup
def fish_setup(area):
	preset(area, [], 0, None, -10)
	register = entity_tracker(area).append
	wave: list[tuple[Type[entities.Entity], Iterable]] = []
	for i in range(area.difficulty // 10):
		for i2 in range(i + 7):
			wave.append((entities.Fish, [area]))
			area.data_pack[1] += 1
		wave = [(entities.MassDelayedDeploy, (60 * 10, area, wave, register))]
	e = entities.MassDelayedDeploy(0, wave[0][1][1], wave[0][1][2], register)
	gameboard.NEW_ENTITIES.append(e)
	register(e)


@fish.set_tick
def fish_tick(area):
	filter_entities(area)
	area.enforce_center = game_states.DISTANCE


@notes.set_init
def notes_init(area):
	set_length(1)(area)
	area.entity_list.append(entities.ItemEntity(items.simple_stab(
		10,
		60,
		images.BATON.img,
		images.BATON.outlined_img,
		(5, area.length - 200),
		0
	)))
	area.entity_list.append(entities.ItemEntity(items.simple_stab(
		10,
		60,
		images.BATON.img,
		images.BATON.outlined_img,
		(-5, area.length - 400),
		0
	)))
	start_note = entities.Note(area.length // 2, True)
	start_note.freeze_y(False)
	area.entity_list.append(start_note)
	tracker = list()
	spawner = entities.NoteSpawner(area, start_note, tracker.append)
	preset(area, tracker, spawner, None, -10)
	entity_tracker(area).append(start_note)
	area.entity_list.append(spawner)
	entity_tracker(area).append(spawner)


@notes.set_setup
def notes_setup(area):
	area.enforce_center = area.start_coordinate + area.length // 2


@notes.set_finish
def notes_finish(area):
	wall = entities.Obstacle(pos=(0, area.end_coordinate))
	wall.hit(9, area)
	gameboard.NEW_ENTITIES.append(wall)


def make_lazer_register_maker(area) -> Callable[[int], Callable[[entities.Entity], list]]:
	call = entity_tracker(area).append
	return lambda c: lambda entity: [area.data_pack.__setitem__(1, min(c, area.data_pack[1])), call(entity)]


@lazers.set_check_win
def lazer_win(area) -> bool:
	return area.data_pack[0] == 0


@lazers.set_setup
def lazers_setup(area):
	area.enforce_center = area.start_coordinate + area.length // 2
	wave: list[tuple[Type[entities.Entity], Iterable]] = []
	ticks_to_cross = area.length // 14
	rep = area.difficulty // 10 + 1
	preset(area, rep + 1, None, -10)
	# register = entity_tracker(area).append
	register = utility.passing
	# register = None
	# deploy = lambda: None
	deploy = lambda: area.data_pack.__setitem__(0, area.data_pack[0] - 1)
	delay = 0
	# make_register = make_lazer_register_maker(area)

	def wave_make():
		nonlocal wave
		wave = [(entities.MassDelayedDeploy, (delay, area, wave, register, deploy))]

	for i in range(rep):
		# register = make_register(i)
		lazertype = area.random.randint(0, 4)
		# lazertype = 4
		# print(f"wave: {["safety zones", "trackers", "juggle"][lazertype]}")
		if lazertype == 0:  # safety zone(s)
			charge_bonus = 10
			delay = ticks_to_cross + charge_bonus
			wave_make()
			separation = 64
			pre_safe_creation = [
				(entities.Lazer, (y, delay, charge_bonus, area))
				for y in range(area.start_coordinate + separation, area.end_coordinate, separation)
			]
			del_at: int = area.random.randint(0, len(pre_safe_creation) - 2)
			del pre_safe_creation[del_at:del_at + 2]
			wave.extend(pre_safe_creation)
		elif lazertype == 1:  # a bunch of trackers
			tracker_delay = 30
			num = area.random.randint(5, 8)
			delay = (num + 1) * tracker_delay
			wave_make()
			for tracker_count in range(num):
				wave.append((
					entities.DelayedDeploy,
					(
						tracker_delay * tracker_count,
						area,
						entities.TrackingLazer,
						(
							area.start_coordinate + area.length * (tracker_count % 2),
							3 * tracker_delay,
							15,
							area
						),
						register
					)
				))
		elif lazertype == 2:  # juggle 3 trackers
			repeats = area.random.randint(3, 5)
			tracker_delay = 30
			delay = tracker_delay * (repeats + 1)
			wave_make()
			for tracker_count in range(3):
				wave.append((
					entities.DelayedDeploy,
					(
						tracker_delay * tracker_count,
						area,
						entities.TrackingLazer,
						(
							area.start_coordinate + area.length * (tracker_count % 2),
							3 * tracker_delay, 15, area, repeats
						),
						register
					)
				))
		elif lazertype == 3:  # odd-even
			charge_time = 40
			fire_duration = 10
			separation = 72
			repeats = area.random.randint(3, 8)
			delay = repeats * charge_time
			wave_make()
			for rep in range(repeats):
				wave.append((
					entities.MassDelayedDeploy,
					(
						charge_time * rep,
						area,
						[
							(entities.Lazer, (y, charge_time, fire_duration, area))
							for y in
							range(area.start_coordinate + separation * (1 + rep % 2), area.end_coordinate, separation * 2)
						],
						register
					)
				))
		elif lazertype == 4:  # blinking sweepers
			lifetime = 4
			num = area.random.randint(min(2, area.difficulty // 5), max(2, area.difficulty // 5 + 1))
			charge_time = 60
			fire_duration = 40
			deploy_delay = 60
			delay = (area.length // 14 + 12) * lifetime + num * deploy_delay
			wave_make()
			choices = (
				entities.Lazer.BOTTOM,
				entities.Lazer.TOP
			)
			for tracker_count in range(num):
				path = [choices[(tracker_count + dest_num) % 2] for dest_num in range(lifetime)]
				wave.append((
					entities.DelayedDeploy,
					(
						deploy_delay * tracker_count,
						area,
						entities.PathedLazer,
						(
							path,
							charge_time,
							fire_duration,
							area
						),
						register
					)
				))
		# wave = [(entities.MassDelayedDeploy, (delay, area, wave, register, deploy))]
	delay = 0
	wave_make()
	e = wave[0][0](*wave[0][1])
	gameboard.NEW_ENTITIES.append(e)
	register(e)


def outline_img(img: pygame.Surface, outline: int):
	width: int = img.get_width()
	height: int = img.get_height()
	outlining_width: int = width + 4 * outline
	outlining_height: int = height + 4 * outline
	outlining: pygame.Surface = pygame.Surface((
		outlining_width, outlining_height
	), pygame.SRCALPHA)
	outlining.blit(img, (outline * 2, outline * 2))
	coord: int
	checks = tuple(
		(i % (2 * outline + 1) - outline, i // (2 * outline + 1) - outline)
		for i in range((2 * outline + 1) ** 2)
		if (i % 5, i // 5) != (0, 0)
	)
	for coord in range((width + 2 * outline) * (height + 2 * outline)):
		x: int = (coord % (width + 2 * outline) + outline)
		y: int = (coord // (width + 2 * outline) + outline)
		offset_x: int
		offset_y: int
		if outlining.get_at((x, y)).r == 0 or outlining.get_at((x, y)).a == 0:
			if any(
				outlining.get_at((x + offset_x, y + offset_y)).r == 255
				and outlining.get_at((x + offset_x, y + offset_y)).a == 255
				for offset_x, offset_y in checks
				if 0 <= x + offset_x < outlining_width and 0 <= y + offset_y < outlining_height
			):
				outlining.set_at((x, y), (0, 0, 0, 255))
			else:
				outlining.set_at((x, y), (0, 0, 0, 0))
	return outlining


def draw_count(getter: Callable) -> Callable:
	def inner(area):
		count = getter(area)
		if count == 0:
			return
		if area.data_pack[-1] == count:
			draw = area.data_pack[-2]
		else:
			draw = outline_img(game_structures.FONTS[64].render(str(getter(area)), True, (255, 255, 255), None), 2)
			area.data_pack[-2] = draw
		y = 30
		if tutorials.display is not None and not switches.TUTORIAL_TEXT_POSITION:
			y += tutorials.display_height
		game_structures.SCREEN.blit(draw, (game_states.WIDTH // 2 - draw.get_width() // 2, y), draw.get_rect())
	inner.__name__ = f"draw_count_{getter.__name__}"
	inner.__qualname__ = inner.__qualname__.replace("inner", getter.__name__)
	return inner


fish.set_draw(draw_count(lambda area: area.num_entities() - 2))
notes.set_draw(draw_count(lambda area: area.data_pack[1].waves))
lazers.set_draw(draw_count(lambda area: area.data_pack[0]))
