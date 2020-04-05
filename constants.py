from harm_math import Vec
from enum import Enum

# Colors
black = (0,0,0)
grey = (100,100,100)
light_grey = (200,200,200)
white = (255,255,255)
red = (255,0,0)
yellow = (255,255,0)
light_red = (255,100,100)
dark_red = (70,0,0)
very_dark_red = (40,0,0)
green = (0,255,0)
light_green = (0,150,0)
dark_green = (0,70,0)
very_dark_green = (0,40,0)
blue = (0,0,255)
ltblue = (50,50,255)
dark_grey = (50,50,50)
dkgrey = (30,30,30)
ltgrey = (150,150,150)
very_dark_blue = (0,0,40)
purple = (128,0,128)
gold = (255,215,0)
pink = (255,200,200)
blue_green = (0,150,150)

# Game parameters

# Editor layout parameters

general_ui_layout = {
	'tabs_origin': 	Vec(0,0),
	'tab_size': 	Vec(100,50),

}

class EditableType(Enum):
	Unit = 0
	Action = 1
	Battle = 2

editable_type_strings = ["Unit", "Skill", "Battle"]

# We could probably do full layout information here.
# a dict that maps property names to a rect, which positions
# the element.

# TODO: Make these *_ui_indices arrays a dict that maps a
# 		EditableType to the index dict

unit_ui_indices = {	'name': 0,
					'description': 1,
					'vigor': 2,
					'armor': 3,
					'focus': 4}

action_ui_indices = { 	'name': 0,
						'description': 1,
						'target set': 2,
						'vigor requirement': 3,
						'armor requirement': 4,
						'focus requirement': 5,
						'vigor damage': 6,
						'armor damage': 7,
						'focus damage': 8}

battle_ui_indices = {	'Team 0, Slot 0': 0,
						'Team 0, Slot 1': 1,
						'Team 0, Slot 2': 2,
						'Team 0, Slot 3': 3,
						'Team 1, Slot 0': 4,
						'Team 1, Slot 1': 5,
						'Team 1, Slot 2': 6,
						'Team 1, Slot 3': 7}

ui_indices = {
	EditableType.Unit: unit_ui_indices,
	EditableType.Action: action_ui_indices,
	EditableType.Battle: battle_ui_indices
}

unit_ui_dropdowns = [
	Vec(400,300),
	Vec(600,300),
	Vec(800,300),
	Vec(1000,300)
]

ui_dropdowns = {
	EditableType.Unit: unit_ui_dropdowns,
	EditableType.Action: [],
	EditableType.Battle: []
}