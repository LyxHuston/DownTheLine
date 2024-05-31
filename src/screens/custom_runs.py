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

handles the custom runs, logic, and starting
"""

import dataclasses

from typing import Type, Callable, Any, Self
from enum import Enum

from data import game_states
from general_use import game_structures, utility
from run_game import game_areas, entities, bosses, items, minigames


def raise_exc(exc: Exception):
	raise exc


@dataclasses.dataclass
class AtomChoices[T]:
	default: T
	prev: Callable[[T], T]
	next: Callable[[T], T]


def tuple_choices(tup: tuple[Any, ...] | Any, *args):
	if args:
		tup = tuple([tup] + list(args))
	return AtomChoices(
		tup[0],
		lambda t: tup[tup.index(t) - 1],
		lambda t: tup[(tup.index(t) + 1) % len(tup)]
	)


def range_choices(low: int | float = None, high: int | float = None, step: int | float = 1):
	assert step > 0, f"Range step must be > 0 (is {step})"
	if low is not None and high is not None:
		assert high >= low, f"Range high must be greater than low (is {low}:{high})"
		assert ((high - low) / step) % 1 == 0, f"Range with defined high and low must be divisible by step (is {low}:{high}:{step})"
	return AtomChoices(
		(0 if high is None else high) if low is None else low,
		(lambda i: i - step) if low is None else (lambda i: max(i - step, low)),
		(lambda i: i + step) if high is None else (lambda i: min(i - step, high))
	)


integers = range_choices()
naturals = range_choices(0)
positives = range_choices(1)


@dataclasses.dataclass
class FieldDatatype:
	call: Callable
	default_default_factory: Callable


class FieldOption:

	_no_params: Callable = lambda args: len(args) == 0

	class FieldType(Enum):
		Atom = FieldDatatype(
			lambda acc, options: acc is FieldOption._no_params and options is not None,
			lambda fo: fo.options.default
		)
		Constructed = FieldDatatype(
			lambda acc, options: acc is not FieldOption._no_params and options is None,
			lambda fo: raise_exc(RuntimeError("Constructed FieldOption not given a default or default factory"))
		)

	class ConstructedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				args: tuple[Self, ...]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.default = default
			self.args = args

		def initialize(self):
			return FieldOption.InitializedFieldOption(
				self.typ,
				self.options,
				self.finalize,
				self.default,
				tuple(c.initialize() for c in self.args)
			)

	class InitializedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				contains: tuple[Self, ...]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.contains = contains
			self.val = default

		def make(self):
			return self.finalize(self.val)

	_unspecified = object()

	def __init__(
			self,
			typ: FieldType,
			acceptor: Callable = _no_params,
			options: AtomChoices[Any] = None,
			finalize: Callable = lambda x: x,
			default: Any = _unspecified,
			default_factory: Any = _unspecified
	):
		if not typ.value.call(acceptor, options):
			raise ValueError(f"Incorrect acceptor or options for field option of type {typ.name}")
		self.typ = typ
		self.acceptor = acceptor
		self.options = options
		self.finalize = finalize
		if default is not FieldOption._unspecified and default_factory is not FieldOption._unspecified:
			raise ValueError("Default and default_factory cannot both be specified.")
		self.default = default
		self.default_factory = default_factory
		if default is FieldOption._unspecified and default_factory is FieldOption._unspecified:
			self.default_factory = self.typ.value.default_default_factory

	def __call__(self, *args):
		if not self.acceptor(args):
			raise ValueError(f"Incorrect values to create field of type {self.typ.name}")
		if self.default_factory is not FieldOption._unspecified:
			default = self.default_factory(self)
		else:
			default = self.default
		return FieldOption.ConstructedFieldOption(
			self.typ,
			self.options,
			self.finalize,
			default,
			tuple(args)
		)


entity_types = tuple(
	e_t
	for e_t in game_structures.recursive_subclasses(entities.Entity)
	if e_t.make is not entities.Entity.make and not issubclass(e_t, bosses.Boss)
)

boss_types = tuple(game_structures.recursive_subclasses(bosses.Boss))


class FieldOptions(Enum):
	Bool = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(True, False))
	EntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(entity_types)))
	InstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(entity_types)))
	BossType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(boss_types)))
	ItemType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(items.ItemTypes)))

	EnslaughtEventType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(game_areas.EnslaughtAreaEventType)))
	MinigameType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(tuple(minigames.Minigame.minigames)))

	Difficulty = FieldOption(FieldOption.FieldType.Atom, options=positives)
	DifficultyChange = FieldOption(FieldOption.FieldType.Atom, options=integers)

	@staticmethod
	def list_default(_):
		pass

	List = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args: len(args) == 1,
		default_factory=list_default
	)

	del list_default

	@staticmethod
	def tuple_default(_):
		pass

	Tuple = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=utility.passing,
		default_factory=tuple_default
	)

	del tuple_default

	@staticmethod
	def mapping_default(_):
		pass

	Mapping = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args: len(args) == 2 and all(a.t is FieldOption.FieldType.Atom for a in args),
		default_factory=mapping_default
	)

	del mapping_default


@dataclasses.dataclass
class CustomRun:
	seed: int | None = None
	tutorial: tuple[int, int, int] = (True, True, True)
	start: int = 3
	custom_run: list[
		tuple[Type[game_areas.GameArea], FieldOption.InitializedFieldOption] | Type[game_areas.GameArea]
	] = dataclasses.field(default_factory=list)
	guaranteed_type: Type[game_areas.GameArea] = None


def start_custom(custom: CustomRun):
	from screens import run_start_end
	run_start_end.setup()

	if custom.seed is not None:
		game_states.SEED = custom.seed

	for i, do in enumerate(custom.tutorial):
		if do:
			game_states.LAST_AREA = i
			game_areas.add_game_area().join()

	game_states.LAST_AREA = custom.start

	for run in custom.custom_run:
		seed = game_areas.get_determiner()
		if isinstance(run, tuple):
			area_type: Type[game_areas.GameArea]
			args: FieldOption.InitializedFieldOption
			area_type, args = run
			area = area_type(seed, game_states.LAST_AREA, customized=True)
			area.make(*args.finalize(
				game_areas.GameArea(game_states.LAST_AREA, seed=game_areas.get_determiner(), customized=True)
			))
		else:
			area = run(seed, game_states.LAST_AREA)
			game_structures.AREA_QUEUE.append(area)
		game_states.LAST_AREA += 1

	game_areas.guaranteed_type = custom.guaranteed_type
