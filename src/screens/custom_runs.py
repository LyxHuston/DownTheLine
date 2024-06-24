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

from run_game import game_areas

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
	to_save_str: Callable[[T], str]
	from_save_str: Callable[[Any, str], T]


bool_choices = AtomChoices(True, str, lambda b: not b, lambda b: not b, str, lambda _, string: bool(string))


def tuple_choices(tup: tuple[Any, ...] | Any, *args, to_str: Callable[[Any], str] = str):
	if args:
		tup = tuple([tup] + list(args))
	return AtomChoices(
		tup[0] if tup else lambda: tup[0],
		to_str,
		lambda t: tup[tup.index(t) - 1],
		lambda t: tup[(tup.index(t) + 1) % len(tup)],
		to_str,
		lambda _, string: tuple(t for t in tup if to_str(t) == string)[0]
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
		(lambda i: i + step) if high is None else (lambda i: min(i - step, high)),
		str,
		(lambda call: lambda _, string: call(string))(float if isinstance(step, float) or isinstance(low, float) else int),
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
	default_to_str: Callable
	default_from_str: Callable


class FieldOption:

	_no_params: Callable = lambda args: len(args) == 0

	class FieldType(Enum):
		Atom = FieldDatatype(
			lambda acc, options: acc is FieldOption._no_params and options is not None,
			lambda fo: fo.options.default() if isinstance(fo.options.default, Callable) else fo.options.default,
			make_basic_atom_changer,
			lambda fo: fo.options.to_save_str,
			lambda fo: fo.options.from_save_str
		)
		Constructed = FieldDatatype(
			lambda acc, options: acc is not FieldOption._no_params and options is None,
			lambda fo: raise_exc(RuntimeError("Constructed FieldOption not given a default or default factory")),
			lambda fo, width: raise_exc(RuntimeError("Constructed FieldOption not given a button constructor")),
			lambda fo: raise_exc(RuntimeError("Constructed FieldOption not given a save function")),
			lambda fo: raise_exc(RuntimeError("Constructed FieldOption not given a from save function"))
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
				buttons: Callable,
				to_string: Callable[[Any], str],
				from_string: Callable[[Self, str], Any]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.default = default
			self.default_factory = default_factory
			self.args = args
			self.buttons = buttons
			self.to_string = to_string
			self.deserialize = from_string

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
				self.buttons,
				self.to_string
			)

		def from_string(self, string: str):
			try:
				assert string[0] == "[", "String form of IFO must start with a bracket."
				assert string[-1] == "]", "String form of IFO must end with a bracket."

				val = self.deserialize(self, string[1:-1])

				return FieldOption.InitializedFieldOption(
					self.typ,
					self.options,
					self.finalize,
					val,
					self.buttons,
					self.to_string
				)
			except Exception as e:
				e.add_note(string)
				raise e

	class InitializedFieldOption:

		def __init__(
				self,
				typ,
				options: AtomChoices[Any],
				finalize: Callable,
				default: Any,
				buttons: Callable[[Self, int], game_structures.BaseButton],
				to_string: Callable[[Any], str]
		):
			self.typ = typ
			self.options = options
			self.finalize = finalize
			self.val = default
			self.buttons = buttons
			self.serialize = to_string

		def make(self, area):
			return self.finalize(self.val, area)

		def get_buttons(self, width: int) -> game_structures.BaseButton:
			return self.buttons(self, width)

		def to_string(self):
			return f"[{self.serialize(self.val)}]"

	_unspecified = object()

	def __init__(
			self,
			typ: FieldType,
			acceptor: Callable = _no_params,
			options: AtomChoices[Any] = None,
			finalize: Callable = lambda x, _: x,
			default: Any = _unspecified,
			default_factory: Callable[[ConstructedFieldOption], Any] = _unspecified,
			buttons: Callable[[InitializedFieldOption, int], game_structures.BaseButton | None] = _unspecified,
			to_save_str: Callable[[Any], str] = _unspecified,
			from_save_str: Callable[[ConstructedFieldOption, str], Any] = _unspecified
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
		if to_save_str is FieldOption._unspecified:
			self.to_save_str = self.typ.value.default_to_str(self)
		else:
			self.to_save_str = to_save_str
		if from_save_str is FieldOption._unspecified:
			self.from_save_str = self.typ.value.default_from_str(self)
		else:
			self.from_save_str = from_save_str

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
			self.buttons,
			self.to_save_str,
			self.from_save_str
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


def and_lambda(func1: Callable[[], bool], func2: Callable[[], bool]) -> Callable[[], bool]:
	return lambda: func1() and func2()


def make_atom_with_tuple_choice(tuple_choice: AtomChoices):
	return FieldOption(FieldOption.FieldType.Atom, options=tuple_choice)


def split_ifo_save(string: str) -> list[str]:
	if not string:
		return []
	splits: list[str] = []
	depth: int = 0
	last: int = 0
	for i, char in enumerate(string):
		if char == "," and depth == 0:
			splits.append(string[last:i])
			last = i + 1
		elif char == "[":
			depth += 1
		elif char == "]":
			assert depth > 0, "unmatched closed bracket in ifo save"
			depth -= 1
	assert depth == 0, "unmatched open bracket in ifo save"
	splits.append(string[last:])
	return splits


class FieldOptions(Enum):
	Bool = FieldOption(FieldOption.FieldType.Atom, options=bool_choices, buttons=make_boolean_atom_changer)
	EntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		entity_types,
		to_str=class_name_getter
	))
	InstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		entity_types,
		to_str=class_name_getter,
	), finalize=lambda val, area: val.make(area))
	NormalEntityType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		normal_enemy_types,
		to_str=class_name_getter
	))
	NormalInstantiatedEntity = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		normal_enemy_types,
		to_str=class_name_getter
	), finalize=lambda val, area: val.make(area))
	BossType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		boss_types,
		to_str=class_name_getter
	))
	ItemType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		item_types,
		to_str=enum_name_getter,
	))

	EnslaughtEventType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		enslaught_event_type,
		to_str=enum_name_getter
	))
	MinigameType = FieldOption(FieldOption.FieldType.Atom, options=tuple_choices(
		minigame_type,
		to_str=enum_name_getter
	))

	Degrees = FieldOption(
		FieldOption.FieldType.Atom, options=range_choices(0, 360, 45),
		buttons=make_increment_atom_changer
	)
	Integer = FieldOption(FieldOption.FieldType.Atom, options=integers, buttons=make_increment_atom_changer)
	Positive = FieldOption(FieldOption.FieldType.Atom, options=positives, buttons=make_increment_atom_changer)

	Seed = FieldOption(
		FieldOption.FieldType.Atom, options=integers, buttons=lambda _, __: None,
		finalize=lambda _, area: area.get_next_seed(),
		to_save_str=lambda _: "<seed>",
		from_save_str=lambda _, __: 0
	)
	Area = FieldOption(
		FieldOption.FieldType.Atom, options=integers, buttons=lambda _, __: None,
		finalize=lambda _, area: area,
		to_save_str=lambda _: "<area>",
		from_save_str=lambda _, __: 0
	)

	NONE = FieldOption(
		FieldOption.FieldType.Atom, options=integers, buttons=lambda _, __: None,
		finalize=lambda _, __: None,
		to_save_str=lambda _: "<none>",
		from_save_str=lambda _, __: 0
	)

	@staticmethod
	def or_none_buttons(ifo: FieldOption.InitializedFieldOption, width: int) -> game_structures.BaseButton:
		switch_button_img = pygame.surface.Surface((10, 10))
		pygame.draw.rect(switch_button_img, (255, 255, 255), switch_button_img.get_rect(), width=5)

		def switch():
			ifo.val[0] ^= True  # should be equivalent to ifo.val[0] = not ifo.val[0]

		switch_button = game_structures.Button.make_img_button(
			switch,
			switch_button_img,
			(15, 15),
			"switch to/from None"
		)

		def set_length():
			buttons.rect.height = 20 + max(10, held_buttons.rect.height if ifo.val[0] else 0)
			return ifo.val[0]

		held_buttons: game_structures.BaseButton = ifo.val[1].get_buttons(width - 40)
		held_buttons.visible = and_lambda(set_length, held_buttons.visible)
		held_buttons.rect.x = 30
		buttons = game_structures.ButtonHolder(
			[switch_button, held_buttons],
			_rect=pygame.rect.Rect(0, 0, width, 30)
		)
		return buttons

	@staticmethod
	def or_none_fromstring(cfo: FieldOption.ConstructedFieldOption, string: str):
		parts = split_ifo_save(string)
		on = bool(parts[0])
		sub_ifo = cfo.args[1].from_string(parts[1])
		return [on, sub_ifo]

	OrNone = FieldOption(
		FieldOption.FieldType.Constructed, buttons=or_none_buttons,
		acceptor=lambda args: len(args) == 1 and isinstance(args[0], FieldOption.ConstructedFieldOption),
		default_factory=lambda cfo: [False, cfo.args[0].initialize],
		finalize=lambda val, area: val[1].make(area) if val[0] else None,
		to_save_str=lambda val: f"{val[0]},{val[1].to_string()}",
		from_save_str=lambda cfo, string: cfo.args[1].from_string(string)
	)

	del or_none_buttons, or_none_fromstring

	Difficulty = Positive
	DifficultyChange = Integer

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
		), finalize=lambda val, area: val[1].make(area),
		to_save_str=lambda val: f"<label>,{val[1].to_string()}",
		from_save_str=lambda cfo, string: (cfo.args[0], cfo.args[1].from_string(string.split(",", maxsplit=1)[1]))
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
		buttons=list_init_buttons,
		finalize=lambda val, area: [sub_ifo.make(area) for sub_ifo in val[0]],
		to_save_str=lambda val: ",".join(sub_ifo.to_string() for sub_ifo in val[0]),
		from_save_str=lambda cfo, string: ([cfo.args[0].from_string(part) for part in split_ifo_save(string)], cfo.args[0])
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
		), finalize=lambda val, area: tuple(sub_ifo.make(area) for sub_ifo in val),
		to_save_str=lambda val: ",".join(sub_ifo.to_string() for sub_ifo in val),
		from_save_str=lambda cfo, string: (cfo.args[i].from_string(part) for i, part in split_ifo_save(string))
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
			make_step(1),
			str,
			lambda _, string: int(string)
		)
		top_buttons = FieldOption(FieldOption.FieldType.Atom, options=keys)().initialize().get_buttons(width - 20)
		switcher = game_structures.PassThroughSwitchHolder(
			0, [sub_ifo.get_buttons(width - 20) for _, sub_ifo in ifo.val[1]]
		)

		return game_structures.ListHolder(
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

	@staticmethod
	def mapping_fromstring(cfo: FieldOption.ConstructedFieldOption, string: str):
		args: dict[str, FieldOption.ConstructedFieldOption] = cfo.args
		names = tuple(sorted(name for name in args))
		parts = split_ifo_save(string)
		return [
			names.index(parts[0]),
			tuple(sorted(
				(
					(
						name,
						val.from_string(parts[1]) if name == parts[0] else val.initialize()
					) for name, val in args.items()
				),
				key=lambda item: item[0]
			))
		]

	Mapping = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args:
			len(args) == 1 and
			isinstance(args[0], dict) and
			all(
				isinstance(name, str) and isinstance(val, FieldOption.ConstructedFieldOption)
				for name, val in args[0].items()
			),
		default_factory=lambda fo: [
				0, tuple(sorted(((name, val.initialize()) for name, val in fo.args.items()), key=lambda item: item[0]))
			],
		buttons=mapping_init_buttons,
		finalize=lambda val, _: val[1][val[0]][1].finalize(),
		to_save_str=lambda val: f"{val[1][val[0]][0]},{val[1][val[0]][1].to_string()}",
		from_save_str=mapping_fromstring,
	)

	del mapping_init_buttons, mapping_fromstring

	InstanceMaker = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=lambda args:
			isinstance(args[0], type) and
			isinstance(args[1], tuple) and
			all(isinstance(sub_arg, FieldOption.ConstructedFieldOption) for sub_arg in args[1]) and
			(len(args) == 2 or (len(args) == 3 and isinstance(args[2], bool))),
			# third arg is should label be shown, default True
		default_factory=lambda cfo: (cfo.args[0], tuple(sub_cfo.initialize() for sub_cfo in cfo.args[1])),
		buttons=lambda ifo, width: game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			20,
			20,
			0,
			math.inf,
			init_list=(
				[
					game_structures.Button.make_text_button(
						utility.from_camel(ifo.val[0].__name__), button_font, (0, 0)
					)
				] if len(ifo.val) == 2 or ifo.val[2] else []
			) + [sub_ifo.get_buttons(width) for sub_ifo in ifo.val[1]],
			outline_width=5
		),
		finalize=lambda val, area: val[0](*(sub_ifo.make() for sub_ifo in val[1])),
		to_save_str=lambda val: ",".join(sub_ifo.to_string() for sub_ifo in val[1]),
		from_save_str=lambda cfo, string: (cfo.args[1][i].from_string(part) for i, part in split_ifo_save(string))
	)

	@staticmethod
	def itemmaker_acceptor(args):
		from run_game import items
		return (
			isinstance(args[0], items.ItemType) and
			isinstance(args[1], tuple) and
			all(isinstance(sub_arg, FieldOption.ConstructedFieldOption) for sub_arg in args[1]) and
			(len(args) == 2 or (len(args) == 3 and isinstance(args[2], bool)))
		)

	ItemMaker = FieldOption(
		FieldOption.FieldType.Constructed,
		acceptor=itemmaker_acceptor,
			# third arg is should label be shown, default True
		default_factory=lambda cfo: (cfo.args[0], tuple(sub_cfo.initialize() for sub_cfo in cfo.args[1])),
		buttons=lambda ifo, width: game_structures.ListHolder(
			pygame.rect.Rect(0, 0, width, game_states.HEIGHT),
			20,
			20,
			0,
			math.inf,
			init_list=(
				[
					game_structures.Button.make_text_button(
						utility.from_camel(ifo.val[0].__name__), button_font, (0, 0)
					)
				] if len(ifo.val) == 2 or ifo.val[2] else []
			) + [sub_ifo.get_buttons(width) for sub_ifo in ifo.val[1]],
			outline_width=5
		),
		finalize=lambda val, area: val[0].constructor(*(sub_ifo.make() for sub_ifo in val[1])),
		to_save_str=lambda val: ",".join(sub_ifo.to_string() for sub_ifo in val[1]),
		from_save_str=lambda cfo, string: (cfo.args[1][i].from_string(part) for i, part in split_ifo_save(string))
	)

	del itemmaker_acceptor


from run_game import items


items.generate_item_construction_map()


@dataclasses.dataclass
class CustomRun:
	name: str = "New custom run"
	seed: int | None = None
	tutorial: list[bool] = dataclasses.field(default_factory=lambda: [True, True, True])
	start: int = 3
	custom_run: list[
		tuple[Type[Any], FieldOption.InitializedFieldOption] | Type[Any]
	] = dataclasses.field(default_factory=list)
	guaranteed_type: Type[Any] = None


def custom_run_from_string(string: str) -> CustomRun:

	def get_area_type_from_name(nm: str) -> Type[game_areas.GameArea]:
		return [area_type for area_type in area_types if nm == class_name_getter(area_type)][0]

	parts = split_ifo_save(string)
	name = parts[0][1:-1]
	seed = parts[1]
	if seed == "None":
		seed = None
	else:
		try:
			seed = int(seed)
		except ValueError:
			pass
	tutorial = [i == "1" for i in parts[2]]  # record it as a string of 1 or 0
	start = int(parts[3])

	custom_run_areas = []

	for part in split_ifo_save(parts[4][1:-1]):
		if not part:
			continue
		start_end = (part[0] == "[") + (part[-1] == "]")
		if start_end == 0:  # just area type
			custom_run_areas.append(get_area_type_from_name(part))
		elif start_end == 1:  # malformed
			raise ValueError("Malformed custom run area list")
		elif start_end == 2:
			print(part)
			area_parts = split_ifo_save(part)
			print(area_parts)
			area_type = get_area_type_from_name(area_parts[0])
			custom_run_areas.append((area_type, area_type.fields.from_string(area_parts[1])))
		else:
			raise ValueError("Uh?!?!?!")

	guaranteed_type = parts[5]
	if guaranteed_type == "None":
		guaranteed_type = None
	else:
		guaranteed_type = get_area_type_from_name(guaranteed_type)

	return CustomRun(name, seed, tutorial, start, custom_run_areas, guaranteed_type)


def custom_run_to_string(custom_run: CustomRun):
	return ",".join([
		f"[{custom_run.name}]",
		str(custom_run.seed),
		"".join("1" if tut else "0" for tut in custom_run.tutorial),
		str(custom_run.start),
		f"[{','.join([
			f'[{class_name_getter(area[0])},{area[1].to_string()}]'
			if isinstance(area, tuple) else
			class_name_getter(area)
			for area in custom_run.custom_run
		])}]",
		"None" if custom_run.guaranteed_type is None else class_name_getter(custom_run.guaranteed_type)
	])


def start_custom(custom: CustomRun):
	from screens import run_start_end
	from run_game import ingame
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
				area
			))
		else:
			area = run(seed, game_states.LAST_AREA)
		game_states.LAST_AREA += 1
		area.finalize()
		game_structures.NEW_AREAS.append(area)

	game_areas.guaranteed_type = custom.guaranteed_type
	run_start_end.populate_area_queue()
	ingame.screen.start(was_customized=True)


LIST: game_structures.ListHolder | None = None
custom_run_list: list[CustomRun] = []

area_types = ()


def remove_from_list[T](
		ifo_list: list[T],
		button_list: list[game_structures.BaseButton],
		ifo: T,
		button: game_structures.BaseButton
):
	try:
		ifo_list.remove(ifo)
		button_list.remove(button)
	except ValueError:
		pass


def change_new_area_type(
		i: list[int], show_area_type: game_structures.Button, adder: game_structures.ButtonHolder, direction: int
):
	i[0] = (i[0] + direction) % len(area_types)
	show_area_type.rewrite_button(
		utility.from_camel(area_types[i[0]].__name__),
		button_font,
		show_area_type.rect.topleft,
		y_align=0,
		x_align=0
	)
	adder.fit_size()


def new_custom_area(
		custom_run_list: list[tuple[Type[Any], FieldOption.InitializedFieldOption] | Type[Any]],
		button_list: list[game_structures.BaseButton],
		area_type
):
	fields: FieldOption.ConstructedFieldOption = area_type.fields
	new_ifo: FieldOption.InitializedFieldOption = fields.initialize()
	add_custom_area_buttons_to_list(custom_run_list, button_list, area_type, new_ifo, True)
	custom_run_list.append((area_type, new_ifo))


def add_custom_area_buttons_to_list(
		custom_run_list: list[tuple[Type[Any], FieldOption.InitializedFieldOption] | Type[Any]],
		button_list: list[game_structures.BaseButton],
		area_type: Type[Any],
		ifo: FieldOption.InitializedFieldOption,
		_customized: bool
):
	buttons: game_structures.ButtonHolder = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		0,
		math.inf
	)

	customized = [_customized]

	def switch_customized():
		customized[0] ^= True
		customized_button.rewrite_button(
			f"customized: {customized[0]}",
			button_font,
			(0, 0)
		)
		custom_run_list[button_list.index(buttons)] = (area_type, ifo) if customized[0] else (area_type)

	def remove():
		i = button_list.index(buttons)
		del custom_run_list[i]
		del button_list[i]

	customized_button = game_structures.Button.make_text_button(
		f"customized: {customized[0]}",
		button_font,
		(0, 0),
		down_click=switch_customized
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
			customized_button,
			game_structures.Button.make_text_button(
				"delete",
				button_font,
				(0, 0),
				down_click=remove
			)
		]
	)
	buttons.add_button(name_bar)
	new_buttons = ifo.get_buttons(game_states.WIDTH - 100)
	new_buttons.visible = and_lambda(lambda: customized[0], new_buttons.visible)
	buttons.add_button(new_buttons)

	button_list.append(buttons)


def add_new_custom_run():
	custom_run = CustomRun()
	add_from_custom_run(custom_run, True)


def add_from_custom_run(custom_run: CustomRun, _expanded: bool = False):
	custom_run_list.append(custom_run)
	buttons: game_structures.ButtonHolder = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		0,
		math.inf
	)

	expanded = [_expanded]

	def change_expanded():
		expanded[0] ^= True
		expanded_button.rewrite_button("hide" if expanded[0] else "show", button_font, expanded_button.rect.center)

	name_button = game_structures.Button.make_text_button(
		custom_run.name,
		button_font,
		(0, 0),
		down_click=lambda: name_button.write_button_text(
			button_font,
			min_characters=1,
			callback=lambda res: setattr(custom_run, "name", res)
		)
	)

	expanded_button = game_structures.Button.make_text_button(
		"hide" if expanded[0] else "show",
		button_font,
		(0, 0),
		down_click=change_expanded
	)

	name_bar: game_structures.ButtonHolder = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 100),
		10,
		20,
		0,
		game_states.WIDTH,
		outline_width=5,
		init_list=[
			name_button,
			expanded_button,
			game_structures.Button.make_text_button(
				"delete",
				button_font,
				(0, 0),
				down_click=functools.partial(remove_from_list, custom_run_list, LIST.list, custom_run, buttons)
			),
			game_structures.Button.make_text_button(
				"play",
				button_font,
				(0, 0),
				down_click=functools.partial(start_custom, custom_run)
			)
		]
	)
	buttons.add_button(name_bar)

	expanded_buttons: game_structures.ButtonHolder = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		0,
		math.inf,
		visible_check=lambda: expanded[0]
	)

	seed: list[int] = [0 if custom_run.seed is None else custom_run.seed]

	def set_seed(text: str):
		try:
			seed[0] = int(text)
		except ValueError:
			seed[0] = hash(text)
		custom_run.seed = seed[0]

	def swap_custom_seed():
		custom_run.seed = seed[0] if custom_run.seed is None else None

	custom_seed_button = game_structures.Button.make_text_button(
		"Custom seed?", button_font, (0, 0), swap_custom_seed
	)

	seed_setter_button = game_structures.Button.make_text_button(
		str(seed[0]), button_font, (0, 0),
		lambda: seed_setter_button.write_button_text(button_font, callback=set_seed),
		visible_check=lambda: custom_run.seed is not None
	)

	seed_bar: game_structures.HorizontalListHolder = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 0), 10, 20, 0, game_states.WIDTH,
		init_list=[custom_seed_button, seed_setter_button], outline_width=5
	)

	seed_bar.fit_y(5)
	seed_bar.fit_x(20)
	seed_bar.clip_rect.size = seed_bar.base_rect.size
	seed_bar.rect.size = seed_bar.base_rect.size

	expanded_buttons.add_button(seed_bar)

	def change_tutorial_do(i: int):
		custom_run.tutorial[i] ^= True
		tutorial_buttons[i].rewrite_button(
			str(custom_run.tutorial[i]), button_font, tutorial_buttons[i].rect.center,
		)
		change_difficulty(0)

	expanded_buttons.add_button(game_structures.Button.make_text_button("Do tutorials?", button_font, (0, 0)))

	tutorial_buttons: game_structures.HorizontalListHolder = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 0),
		10, 20, 0, game_states.WIDTH,
		init_list=[game_structures.Button.make_text_button(
			str(custom_run.tutorial[i]), button_font, (0, 0), down_click=functools.partial(change_tutorial_do, i)
		) for i in range(3)],
		outline_width=5
	)

	tutorial_buttons.fit_y(5)
	tutorial_buttons.fit_x(20)
	tutorial_buttons.clip_rect.size = tutorial_buttons.base_rect.size
	tutorial_buttons.rect.size = tutorial_buttons.base_rect.size

	expanded_buttons.add_button(tutorial_buttons)

	def change_difficulty(direction: int):
		custom_run.start = max(custom_run.start + direction, custom_run.tutorial.count(True))
		difficulty_indicator.rewrite_button(str(custom_run.start), button_font, (0, 0))

	difficulty_indicator = game_structures.Button.make_text_button(
		str(custom_run.start), button_font, (0, 0)
	)

	difficulty_bar = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 0), 10, 20,
		0, game_states.WIDTH, outline_width=5,
		init_list=[
			game_structures.Button.make_text_button(
				"Start difficulty", button_font, (0, 0)
			),
			difficulty_indicator,
			game_structures.Button.make_text_button(
				"-", button_font, (0, 0), down_click=functools.partial(change_difficulty, -1)
			),
			game_structures.Button.make_text_button(
				"+", button_font, (0, 0), down_click=functools.partial(change_difficulty, 1)
			)
		]
	)

	difficulty_bar.fit_y(5)
	difficulty_bar.fit_x(20)
	difficulty_bar.clip_rect.size = difficulty_bar.base_rect.size
	difficulty_bar.rect.size = difficulty_bar.base_rect.size

	expanded_buttons.add_button(difficulty_bar)

	area_buttons: game_structures.ButtonHolder = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		0,
		math.inf,
	)

	expanded_buttons.add_button(area_buttons)

	for area in custom_run.custom_run:
		if isinstance(area, tuple):
			area_type, ifo = area
			customized = True
		else:
			area_type = area
			ifo = area_type.fields.initialize()
			customized = False
		add_custom_area_buttons_to_list(
			custom_run.custom_run,
			area_buttons.list,
			area_type,
			ifo,
			customized
		)


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
		outline_width=5
	)

	i = [0]

	change_type = functools.partial(change_new_area_type, i, show_area_type, adder)

	adder.list = [
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
			lambda: new_custom_area(custom_run.custom_run, area_buttons.list, area_types[i[0]])
		)
	]

	adder.fit_y(20)
	adder.rect.height = adder.clip_rect.height = adder.base_rect.height
	change_type(0)

	expanded_buttons.add_button(adder)

	guaranteed_type: list[int] = [0]

	def change_guaranteed_type(direction: int):
		guaranteed_type[0] = (guaranteed_type[0] + direction) % len(area_types)
		guarantee_indicator.rewrite_button(
			utility.from_camel(area_types[guaranteed_type[0]].__name__), button_font, guarantee_indicator.rect.center
		)

	guarantee_indicator = game_structures.Button.make_text_button(
		utility.from_camel(area_types[guaranteed_type[0]].__name__), button_font, (0, 0),
		visible_check=lambda: custom_run.guaranteed_type is not None
	)

	guarantee_bar = game_structures.HorizontalListHolder(
		pygame.rect.Rect(0, 0, 0, 0), 10, 20,
		0, game_states.WIDTH, outline_width=5,
		init_list=[
			game_structures.Button.make_text_button(
				"Guarantee future types?", button_font, (0, 0),
				down_click=lambda: setattr(
					custom_run, "guaranteed_type",
					area_types[guaranteed_type[0]] if custom_run.guaranteed_type is None else None
				)
			),
			guarantee_indicator,
			game_structures.Button.make_text_button(
				"<", button_font, (0, 0), down_click=functools.partial(change_guaranteed_type, -1),
				visible_check=lambda: custom_run.guaranteed_type is not None
			),
			game_structures.Button.make_text_button(
				">", button_font, (0, 0), down_click=functools.partial(change_guaranteed_type, 1),
				visible_check=lambda: custom_run.guaranteed_type is not None
			)
		]
	)

	guarantee_bar.fit_y(5)
	guarantee_bar.fit_x(20)
	guarantee_bar.clip_rect.size = guarantee_bar.base_rect.size
	guarantee_bar.rect.size = guarantee_bar.base_rect.size

	expanded_buttons.add_button(guarantee_bar)

	buttons.add_button(expanded_buttons)

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
	item_types.extend(item_type for item_type in items.ItemTypes if item_type.value.first != -1)
	enslaught_event_type.extend(game_areas.EnslaughtAreaEventType)
	minigame_type.extend(minigames.Minigame.minigames)

	area_types = tuple(sorted(
		game_structures.recursive_subclasses(game_areas.GameArea),
		key=lambda cls: cls.first_allowed_spawn
	))

	previous_custom_runs = []

	try:
		with open("custom_run_save.txt", "r") as custom_run_save:
			for line in custom_run_save.readlines():
				line = line.strip()
				if not line:
					continue
				try:
					previous_custom_runs.append(custom_run_from_string(line))
				except Exception as e:
					game_structures.ALERTS.add_alert("Reading of custom run failed!  Writing to dump and logging!")
					with open("custom_run_errored_dump.txt", "a") as dump:
						dump.write(line + "\n")
					e.add_note(f"Occurred during processing of custom run save: {line}")
					utility.log_error(e)
	except OSError:
		pass

	get_button_font()

	LIST = game_structures.ListHolder(
		pygame.rect.Rect(0, 0, game_states.WIDTH, game_states.HEIGHT),
		10,
		20,
		game_states.HEIGHT,
		game_states.HEIGHT
	)

	for custom_run in previous_custom_runs:
		add_from_custom_run(custom_run, False)

	add_button = game_structures.Button.make_img_button(
		add_new_custom_run,
		button_font.render("  +  ", False, (255, 255, 255), (0, 0, 0)),
		(0, 0),
		"add new area"
	)
	add_button.outline_width = 5
	add_button.outline_color = (255, 255, 255)

	LIST.add_button(add_button)


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


def save_custom_runs(*_):
	try:
		with open("custom_run_save.txt", "w") as custom_run_save:
			for custom_run in custom_run_list:
				try:
					text = custom_run_to_string(custom_run)
				except Exception as e:
					game_structures.ALERTS.add_alert("Custom run could not be encoded!  Check log for more details.")
					utility.log_error(e)
					continue
				custom_run_save.write(text + "\n")
	except OSError as e:
		game_structures.ALERTS.add_alert("Custom runs could not be saved!  Check log for more details.")
		utility.log_error(e)


custom_runs_screen = game_structures.Place(
	tick=utility.passing,
	enter=setup_custom_run_screen,
	end=save_custom_runs,
	exit_on=save_custom_runs,
	crash_on=save_custom_runs
)
