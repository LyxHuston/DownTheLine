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
import functools
import math

from typing import Type, Callable, Any, Self
from enum import Enum

import pygame

from data import game_states
from general_use import game_structures, utility

from run_game import game_areas, items, minigames

from screens import main_screen, run_start_end


button_font: pygame.font.Font | None = None


def get_button_font():
	global button_font
	button_font = game_structures.TUTORIAL_FONTS[64]


def raise_exc(exc: Exception):
	raise exc


@dataclasses.dataclass
class AtomChoices[T]:
	default: T | Callable[[], T]
	to_str: Callable[[T], str]
	prev: Callable[[T], T]
	next: Callable[[T], T]


bool_choices = AtomChoices(True, str, lambda b: not b, lambda b: not b)


def tuple_choices(tup: tuple[Any, ...] | Any, *args, to_str: Callable[[Any], str] = str):
	if args:
		tup = tuple([tup] + list(args))
	return AtomChoices(
		tup[0] if tup else lambda: tup[0],
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
			field_option.options.to_str(field_option.val),
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
				center=(width - 128, 10),
				x_align=1,
				y_align=0,
				down_click=lambda: change_atom_val_to(field_option, button, field_option.options.prev(field_option.val)),
				enforce_width=32
			),
			game_structures.Button.make_text_button(
				next_char,
				button_font,
				center=(width - 64, 10),
				x_align=1,
				y_align=0,
				down_click=lambda: change_atom_val_to(field_option, button, field_option.options.next(field_option.val)),
				enforce_width=32
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
		center=(0, 10),
		x_align=0,
		y_align=0,
		down_click=lambda: change_atom_val_to(field_option, button, not field_option.val)
	)
	return button
	# return game_structures.ButtonHolder([
	# 	button,
	# ], _rect=pygame.rect.Rect(0, 0, width, button.rect.height + 20))


def change_atom_val_to(field_option, button: game_structures.Button, val: Any):
	field_option.val = val
	button.rewrite_button(
		field_option.options.to_str(val),
		button_font,
		center=button.rect.topleft,
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
			lambda fo: fo.options.default() if isinstance(fo.options.default, Callable) else fo.options.default,
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
				default_factory,
				args: tuple[Self, ...],
				buttons: Callable
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.default = default
			self.default_factory = default_factory
			self.args = args
			self.buttons = buttons

		def initialize(self):
			if self.default_factory is not FieldOption._unspecified:
				default = self.default_factory(self)
			else:
				default = self.default
			return FieldOption.InitializedFieldOption(
				self.typ,
				self.options,
				self.finalize,
				default,
				self.buttons
			)

	class InitializedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				buttons: Callable[[Self, int], game_structures.BaseButton]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.val = default
			self.buttons = buttons

		def make(self, area: game_areas.GameArea):
			return self.finalize(self.val, area)

		def get_buttons(self, width: int) -> game_structures.BaseButton:
			return self.buttons(self, width)

	_unspecified = object()

	def __init__(
			self,
			typ: FieldType,
			acceptor: Callable = _no_params,
			options: AtomChoices[Any] = None,
			finalize: Callable = lambda x, _: x,
			default: Any = _unspecified,
			default_factory: Callable[[ConstructedFieldOption], Any] = _unspecified,
			buttons: Callable[[InitializedFieldOption, int], game_structures.BaseButton] = _unspecified
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
		return FieldOption.ConstructedFieldOption(
			self.typ,
			self.options,
			self.finalize,
			self.default,
			self.default_factory,
			tuple(args),
			self.buttons
		)


entity_types = []
normal_enemy_types = []

customizable_enemy_types = []

boss_types = []

item_types = []

enslaught_event_type = []

minigame_type = []


class_name_getter = lambda val: utility.from_camel(val.__name__)
enum_name_getter = lambda val: utility.from_camel(val.name)


class FieldOptions(Enum):
	Bool = FieldOption(FieldOption.FieldType.Atom, options=bool_choices, buttons=make_boolean_atom_changer)
	EntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		entity_types,
		to_str=class_name_getter
	))
	InstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		entity_types,
		to_str=class_name_getter
	))
	NormalEntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		normal_enemy_types,
		to_str=class_name_getter
	))
	NormalInstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		normal_enemy_types,
		to_str=class_name_getter
	))
	BossType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		boss_types,
		to_str=class_name_getter
	))
	ItemType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		item_types,
		to_str=enum_name_getter
	))

	EnslaughtEventType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		enslaught_event_type,
		to_str=enum_name_getter
	))
	MinigameType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		minigame_type,
		to_str=enum_name_getter
	))

	Difficulty = FieldOption(FieldOption.FieldType.Atom, options=positives, buttons=make_increment_atom_changer)
	DifficultyChange = FieldOption(FieldOption.FieldType.Atom, options=integers, buttons=make_increment_atom_changer)

	Label = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args:
			len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], FieldOption.ConstructedFieldOption),
		default_factory=lambda fo: (fo.args[0], fo.args[1].initialize()),
		buttons=lambda ifo, width: game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			20,
			20,
			0,
			math.inf,
			init_list=[
				game_structures.Button.make_text_button(
					ifo.val[0],
					button_font,
					(0, 0)
				),
				ifo.val[1].get_buttons(width)
			]
		)
	)

	@staticmethod
	def list_init_buttons(ifo: FieldOption.InitializedFieldOption, width: int) -> game_structures.BaseButton:
		lst = [
				sub_ifo.get_buttons(width - 128) for sub_ifo in ifo.val[0]
		]
		holder = game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			20,
			20,
			50,
			game_states.HEIGHT,
			init_list=lst
		)

		def add_new_to_list():
			typ: FieldOption.ConstructedFieldOption = ifo.val[1]
			new: FieldOption.InitializedFieldOption = typ.initialize()
			ifo_buttons = new.get_buttons(width - 64)
			buttons = game_structures.ButtonHolder(
				[ifo_buttons],
				_rect=pygame.rect.Rect(0, 0, width - 20, ifo_buttons.rect.height)
			)
			buttons.add_button(
				game_structures.Button.make_text_button(
					"-", button_font, (width - 96, 10),
					down_click=functools.partial(remove_from_list, ifo.val[0], lst, new, buttons),
					x_align=0, y_align=0
				)
			)
			ifo.val[0].append(new)
			lst.insert(-1, buttons)

		holder.add_button(
			game_structures.Button.make_text_button(
				"+",
				button_font,
				(0, 0),
				down_click=add_new_to_list
			)
		)

		return holder

	List = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args: len(args) == 1,
		default_factory=lambda fo: ([], fo.args[0]),
		buttons=list_init_buttons
	)

	del list_init_buttons

	Tuple = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=utility.passing,
		default_factory=lambda fo: tuple(f.initialize() for f in fo.args),
		buttons=lambda ifo, width: game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			20,
			20,
			0,
			math.inf,
			init_list=[sub_ifo.get_buttons(width) for sub_ifo in ifo.val],
			outline_width=5
		)
	)

	@staticmethod
	def mapping_init_buttons(ifo: FieldOption.InitializedFieldOption, width: int) -> game_structures.BaseButton:

		def make_step(direction: int):
			def step(i: int):
				ifo.val[0] = (i + direction) % ifo.val[0]
				switcher.view = ifo.val[0]
				return ifo.val[0]
			return step

		keys = AtomChoices(
			0,
			lambda i: ifo.val[1][i][0],
			make_step(-1),
			make_step(1)
		)
		top_buttons = FieldOption(FieldOption.FieldType.Atom, options=keys)().initialize().get_buttons(width - 20)
		switcher = game_structures.PassThroughSwitchHolder(
			0, [sub_ifo.get_buttons(width - 20) for _, sub_ifo in ifo.val[1]]
		)

		game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			10,
			20,
			0,
			math.inf,
			init_list=[
				top_buttons,
				switcher
			]
		)

	Mapping = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args:
			isinstance(args, dict) and
			all(
				isinstance(name, str) and isinstance(val, FieldOption.ConstructedFieldOption)
				for name, val in args.items()
			),
		default_factory=lambda fo: [
				0, tuple(sorted(((name, val.initialize()) for name, val in fo.args.items()), key=lambda item: item[0]))
			],
		buttons=mapping_init_buttons,
		finalize=lambda val, _: val[1][val[0]][1].finalize()
	)

	del mapping_init_buttons


@dataclasses.dataclass
class CustomRun:
	seed: int | None = None
	tutorial: tuple[int, int, int] = (True, True, True)
	start: int = 3
	custom_run: list[
		tuple[Type[Any], FieldOption.InitializedFieldOption] | Type[Any]
	] = dataclasses.field(default_factory=list)
	guaranteed_type: Type[Any] = None


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
			area.make(*args.make(
				game_areas.GameArea(game_states.LAST_AREA, seed=game_areas.get_determiner(), customized=True)
			))
		else:
			area = run(seed, game_states.LAST_AREA)
			game_structures.AREA_QUEUE.append(area)
		game_states.LAST_AREA += 1

	game_areas.guaranteed_type = custom.guaranteed_type


LIST: game_structures.ListHolder | None = None
custom_run_list: list[FieldOption.InitializedFieldOption] = []

area_types = None


def remove_from_list(
		ifo_list: list[FieldOption.InitializedFieldOption],
		button_list: list[game_structures.BaseButton],
		ifo: FieldOption.InitializedFieldOption,
		button: game_structures.BaseButton
):
	try:
		ifo_list.remove(ifo)
		button_list.remove(button)
	except ValueError:
		pass


def add_new_custom_run(area_type: Type[Any]):
	fields: FieldOption.ConstructedFieldOption = area_type.fields
	new_ifo: FieldOption.InitializedFieldOption = fields.initialize()
	custom_run_list.append(new_ifo)
	buttons: game_structures.ButtonHolder = game_structures.ListHolder(
			pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
			10,
			20,
			0,
			math.inf,
			init_list=[
				new_ifo.get_buttons(game_states.WIDTH - game_structures.BUTTONS[1].rect.width - 40)
			]
		)
	name_bar: game_structures.ButtonHolder = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 100),
		10,
		20,
		0,
		game_states.WIDTH,
		outline_width=5,
		init_list=[
			game_structures.Button.make_text_button(
				utility.from_camel(area_type.__name__),
				button_font,
				(0, 0)
			),
			game_structures.Button.make_text_button(
				"delete",
				button_font,
				(0, 0),
				down_click=functools.partial(remove_from_list, custom_run_list, LIST.list, new_ifo, buttons)
			),
			game_structures.Button.make_text_button(
				"play",
				button_font,
				(0, 0)
			)
		]
	)
	buttons.list.insert(0, name_bar)
	LIST.list.insert(
		-1,
		buttons
	)


def first_enter():
	global LIST, area_types

	from run_game import entities, bosses, items, minigames

	# set tuple/iterable things to get around import order
	entity_types.extend(
		e_t
		for e_t in game_structures.recursive_subclasses(entities.Entity)
		if e_t.make is not entities.Entity.make and not issubclass(e_t, bosses.Boss)
	)
	normal_enemy_types.extend(
		e_t for e_t, _ in game_areas.GameArea.allowable_thresh_holds
	)
	customizable_enemy_types.extend(
		e_t for e_t in entity_types if e_t.fields is not None
	)
	boss_types.extend(game_structures.recursive_subclasses(bosses.Boss))
	item_types.extend(items.ItemTypes)
	enslaught_event_type.extend(game_areas.EnslaughtAreaEventType)
	minigame_type.extend(minigames.Minigame.minigames)

	area_types = tuple(sorted(
		game_structures.recursive_subclasses(game_areas.GameArea),
		key=lambda cls: cls.first_allowed_spawn
	))

	get_button_font()

	LIST = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		game_states.HEIGHT,
		game_states.HEIGHT
	)

	i = 0

	def change_type(direction: int):
		nonlocal i
		i = (i + direction) % len(area_types)
		show_area_type.rewrite_button(
			utility.from_camel(area_types[i].__name__),
			button_font,
			show_area_type.rect.topleft,
			y_align=0,
			x_align=0
		)
		adder.fit_size()

	show_area_type = game_structures.Button.make_text_button(
		"",
		button_font,
		(0, 0)
	)

	adder = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 0),
		20,
		20,
		20,
		game_states.WIDTH,
		init_list=[
			show_area_type,
			game_structures.Button.make_text_button(
				"<",
				button_font,
				(0, 0),
				change_type,
				arguments={"direction": -1}
			),
			game_structures.Button.make_text_button(
				">",
				button_font,
				(0, 0),
				change_type,
				arguments={"direction": 1}
			),
			game_structures.Button.make_text_button(
				"+",
				button_font,
				(0, 0),
				lambda: add_new_custom_run(area_types[i])
			)
		],
		outline_width=5
	)

	adder.fit_y(20)
	adder.rect.height = adder.clip_rect.height = adder.base_rect.height
	change_type(0)

	LIST.add_button(adder)


def setup_custom_run_screen():
	if LIST is None:
		first_enter()

	game_structures.BUTTONS.clear()

	game_structures.BUTTONS.add_button(LIST)

	game_structures.BUTTONS.add_button(
		game_structures.Button.make_text_button(
			"Back", 75, (game_states.WIDTH, 0), main_screen.main_screen_place.start, x_align=1,
			y_align=0, border_width=5
		)
	)


custom_runs_screen = game_structures.Place(
	tick=utility.passing,
	enter=setup_custom_run_screen,
)
