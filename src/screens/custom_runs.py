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

import pygame

from data import game_states
from general_use import game_structures, utility
from run_game import game_areas, entities, bosses, items, minigames

from screens import main_screen, run_start_end


button_font: pygame.font.Font | None = None


def get_button_font():
	global button_font
	button_font = game_structures.TUTORIAL_FONTS[32]


def raise_exc(exc: Exception):
	raise exc


@dataclasses.dataclass
class AtomChoices[T]:
	default: T
	to_str: Callable[[T], str]
	prev: Callable[[T], T]
	next: Callable[[T], T]


bool_choices = AtomChoices(True, str, lambda b: not b, lambda b: not b)


def tuple_choices(tup: tuple[Any, ...] | Any, *args, to_str: Callable[[Any], str] = str):
	if args:
		tup = tuple([tup] + list(args))
	return AtomChoices(
		tup[0],
		to_str,
		lambda t: tup[tup.index(t) - 1],
		lambda t: tup[(tup.index(t) + 1) % len(tup)]
	)


def range_choices(low: int | float = None, high: int | float = None, step: int | float = 1, rounding: int = None):
	assert step > 0, f"Range step must be > 0 (is {step})"
	if low is not None and high is not None:
		assert high >= low, f"Range high must be greater than low (is {low}:{high})"
		assert ((high - low) / step) % 1 == 0, f"Range with defined high and low must be divisible by step (is {low}:{high}:{step})"
	if rounding is None:
		to_str = str
	else:
		to_str = lambda i: str(round(i, rounding))
	return AtomChoices(
		(0 if high is None else high) if low is None else low,
		to_str,
		(lambda i: i - step) if low is None else (lambda i: max(i - step, low)),
		(lambda i: i + step) if high is None else (lambda i: min(i - step, high))
	)


integers: AtomChoices[int] = range_choices()
naturals: AtomChoices[int] = range_choices(0)
positives: AtomChoices[int] = range_choices(1)


def atom_changer_with_chars(prev_char: str, next_char: str):
	def inner(field_option, width: int):
		button = game_structures.Button.make_text_button(
			str(field_option.val),
			button_font,
			center=(0, 0),
			x_align=0,
			y_align=0
		)
		return game_structures.ButtonHolder([
			button,
			game_structures.Button.make_text_button(
				prev_char,
				button_font,
				center=(width - 32, 10),
				x_align=1,
				y_align=0,
				down_click=lambda: change_atom_val_to(field_option, button, field_option.options.prev(field_option.val)),
				border_width=5
			),
			game_structures.Button.make_text_button(
				next_char,
				button_font,
				center=(width, 10),
				x_align=1,
				y_align=0,
				down_click=lambda: change_atom_val_to(field_option, button, field_option.options.next(field_option.val)),
				border_width=5
			),
		], _rect=pygame.rect.Rect(0, 0, width, button.rect.height + 20))
	return inner


make_basic_atom_changer: Callable[[Any, int], game_structures.BaseButton] = atom_changer_with_chars(
	"<", ">"
)
make_increment_atom_changer: Callable[[Any, int], game_structures.BaseButton] = atom_changer_with_chars(
	"-", "+"
)


def make_boolean_atom_changer(field_option, width: int):
	button = game_structures.Button.make_text_button(
		str(field_option.val),
		button_font,
		center=(0, 0),
		x_align=0,
		y_align=0,
		down_click=lambda: change_atom_val_to(field_option, button, not field_option.val)
	)
	return game_structures.ButtonHolder([
		button,
	], _rect=pygame.rect.Rect(0, 0, width, button.rect.height + 20))


def change_atom_val_to(field_option, button: game_structures.Button, val: Any):
	field_option.val = val
	button.rewrite_button(
		str(val),
		button_font,
		center=(0, 10),
		x_align=0,
		y_align=0
	)


@dataclasses.dataclass
class FieldDatatype:
	call: Callable
	default_default_factory: Callable
	default_buttons: Callable[[Self, int], game_structures.BaseButton]


class FieldOption:

	_no_params: Callable = lambda args: len(args) == 0

	class FieldType(Enum):
		Atom = FieldDatatype(
			lambda acc, options: acc is FieldOption._no_params and options is not None,
			lambda fo: fo.options.default,
			make_basic_atom_changer
		)
		Constructed = FieldDatatype(
			lambda acc, options: acc is not FieldOption._no_params and options is None,
			lambda fo: raise_exc(RuntimeError("Constructed FieldOption not given a default or default factory")),
			lambda fo, width: raise_exc(RuntimeError("Constructed FieldOption not given a button constructor"))
		)

	class ConstructedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				args: tuple[Self, ...],
				buttons: Callable
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.default = default
			self.args = args
			self.buttons = buttons

		def initialize(self):
			return FieldOption.InitializedFieldOption(
				self.typ,
				self.options,
				self.finalize,
				self.default,
				tuple(c.initialize() for c in self.args),
				self.buttons
			)

	class InitializedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				contains: tuple[Self, ...],
				buttons: Callable[[Self, int], game_structures.BaseButton]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.contains = contains
			self.val = default
			self.buttons = buttons

		def make(self):
			return self.finalize(self.val)

		def get_buttons(self, width: int) -> game_structures.BaseButton:
			return self.buttons(self, width)

	_unspecified = object()

	def __init__(
			self,
			typ: FieldType,
			acceptor: Callable = _no_params,
			options: AtomChoices[Any] = None,
			finalize: Callable = lambda x: x,
			default: Any = _unspecified,
			default_factory: Any = _unspecified,
			buttons: Callable[[Self, int], game_structures.BaseButton] = _unspecified
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
		if default is FieldOption._unspecified and default_factory is FieldOption._unspecified:
			self.default_factory = self.typ.value.default_default_factory
		else:
			self.default_factory = default_factory
		if buttons is FieldOption._unspecified:
			self.buttons = self.typ.value.default_buttons
		else:
			self.buttons = buttons

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
			tuple(args),
			self.buttons
		)


entity_types = tuple(
	e_t
	for e_t in game_structures.recursive_subclasses(entities.Entity)
	if e_t.make is not entities.Entity.make and not issubclass(e_t, bosses.Boss)
)

boss_types = tuple(game_structures.recursive_subclasses(bosses.Boss))


class_name_getter = lambda val: val.__name__
enum_name_getter = lambda val: val.name


class FieldOptions(Enum):
	Bool = FieldOption(FieldOption.FieldType.Atom, options=bool_choices, buttons=make_boolean_atom_changer)
	EntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(entity_types),
		to_str=class_name_getter
	))
	InstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(entity_types),
		to_str=class_name_getter
	))
	BossType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(boss_types),
		to_str=class_name_getter
	))
	ItemType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(items.ItemTypes),
		to_str=enum_name_getter
	))

	EnslaughtEventType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(game_areas.EnslaughtAreaEventType),
		to_str=enum_name_getter
	))
	MinigameType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		tuple(minigames.Minigame.minigames),
		to_str=enum_name_getter
	))

	Difficulty = FieldOption(FieldOption.FieldType.Atom, options=positives, buttons=make_increment_atom_changer)
	DifficultyChange = FieldOption(FieldOption.FieldType.Atom, options=integers, buttons=make_increment_atom_changer)

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


LIST = None


def first_enter():
	global LIST

	LIST = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		game_states.HEIGHT,
		game_states.HEIGHT
	)


def setup_custom_run_screen():
	if LIST is None:
		first_enter()

	game_structures.BUTTONS.clear()

	game_structures.BUTTONS.add_button(LIST)

	game_structures.BUTTONS.add_button(
		game_structures.Button.make_text_button(
			"Back", 75, (game_states.WIDTH, 0), main_screen.main_screen_place.start, x_align=1, y_align=0)
	)


custom_runs_screen = game_structures.Place(
	tick=utility.passing,
	enter=setup_custom_run_screen,
)
