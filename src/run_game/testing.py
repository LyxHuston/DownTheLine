from run_game import game_areas, entities
from general_use import game_structures
from typing import Callable, Type
import enum


class EndTestingArea(game_areas.GameArea):

	def cross_boundary(self):
		game_structures.switch_to_place(game_structures.PLACES.won)


class OptionTypes(enum.Enum):
	List = 0
	Choice = type
	Entity = Choice(
		[typ for typ in game_structures.recursive_subclasses(entities.Entity) if typ.make is not entities.Entity.make]
	)


class AreaOptions:

	def __init__(
			self, area: Type[game_areas.GameArea], *arg_options_list: list[OptionTypes], verify_args: Callable = None
	):
		self.area = area
		self.arg_options_list = tuple(arg_options_list)
		self.verify_args = verify_args


options = [
	AreaOptions(EndTestingArea),
	AreaOptions(game_areas.BasicArea),
	AreaOptions(game_areas.BreakThroughArea),
	AreaOptions(game_areas.GiftArea),
	AreaOptions(game_areas.EnslaughtArea),
	AreaOptions(game_areas.MinigameArea)
]

