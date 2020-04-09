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
skill_slots = 4

# Editor layout parameters

general_ui_layout = {
	'tabs_origin': 	Vec(0,0),
	'tab_size': 	Vec(100,50),

}

class EditableType(Enum):
	Unit = 0
	Skill = 1
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

skill_ui_indices = { 	'name': 0,
						'vigor requirement': 1,
						'armor requirement': 2,
						'focus requirement': 3}

battle_ui_indices = {}

ui_indices = {
	EditableType.Unit: unit_ui_indices,
	EditableType.Skill: skill_ui_indices,
	EditableType.Battle: battle_ui_indices
}

unit_ui_dropdowns = [
	Vec(400,300),
	Vec(600,300),
	Vec(800,300),
	Vec(1000,300)
]

skill_ui_dropdowns = [
	Vec(800,200)
]

battle_ui_dropdowns = \
	[Vec(400+200*y,100) for y in range(4)] + \
	[Vec(400+200*y,400) for y in range(4)]

ui_dropdowns = {
	EditableType.Unit: unit_ui_dropdowns,
	EditableType.Skill: skill_ui_dropdowns,
	EditableType.Battle: battle_ui_dropdowns
}