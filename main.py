import os, sys
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (100,30)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import math
import random
import json
import re
from functools import partial
from enum import Enum
from copy import copy, deepcopy

import debug
from util import InputState, last_index, is_positive_index, in_range
import util
from harm_math import Vec, Rect
from harm_animation import Tween, Animation
from harm_draw import Surface, draw_surface, darken_color, draw_line, draw_rect, draw_text, AlignX, AlignY, draw_x, draw_text_wrapped
import constants as c

typeable_chars = 	  [chr(i) for i in range(ord('a'),ord('z')+1)] \
					+ [chr(i) for i in range(ord('A'),ord('Z')+1)] \
					+ [chr(i) for i in range(ord('0'),ord('9')+1)] \
					+ [' ', '.']

random.seed()

import pygame as pg
screen_width, screen_height = 1400,800
game = None

# -- State class template -- 

# class State:
# 	def __init__(self):
# 		pass
# 	def draw(self, game):
# 		pass
# 	def update(self, game):
# 		pass
# 	def key_pressed(self, game, key, mod, translated):
# 		pass
# 	def mouse_button_pressed(self, game, button):
#  		pass
#  	def enter(self):
#  		pass
#  	def exit(self):
#  		pass


pg.font.init()
main_font_10 = pg.font.Font("font.ttf", 28)
main_font_7 = pg.font.Font("font.ttf", 22)
main_font_5 = pg.font.Font("font.ttf", 18)
main_font_5_u = pg.font.Font("font.ttf", 18)
main_font_5_u.set_underline(True)
main_font_4 = pg.font.Font("font.ttf", 12)
main_font_2 = pg.font.Font("font.ttf", 8)

slot_width = 200
enemy_slot_positions = [600,800,1000,1200]
friendly_slot_positions = [200,400,600]
# [top of screen => trait bars, top of screen => enemy sprite, top of screen => action icons]
enemy_ui_paddings = [70, 100, 380, 380]
friendly_ui_paddings = [70, 100, 380, 380]

def get_slot_x_pos(team, slot):
	if team == 0:
		return friendly_slot_positions[slot]
	else:
		return enemy_slot_positions[slot]

def get_team_ui_padding(team, index):
	if team == 0:
		return friendly_ui_paddings[index]
	else:
		return enemy_ui_paddings[index]

# Trait enum:
# T.Vigor, T.Armor, T.Focus
class T(Enum):
	Vigor = 0
	Armor = 1
	Focus = 2

trait_count = 3
trait_colors = {T.Vigor: c.red, T.Armor:c.yellow, T.Focus: c.ltblue}
trait_strings = {T.Vigor: "Vigor", T.Armor: "Armor", T.Focus: "Focus"}

pointer_cursor_surface = Surface.from_file("Cursor.png")

edit_cursor_surface = Surface.from_file("CursorEdit.png")
edit_cursor_surface.set_anchor(Vec(6,10))

sword_surfaces = {	T.Vigor: Surface.from_file("RedSword.png"),
					T.Armor: Surface.from_file("YellowSword.png"),
					T.Focus: Surface.from_file("BlueSword.png")}
# red_sword_surface = Surface.from_file("RedSword.png")
# blue_sword_surface = Surface.from_file("BlueSword.png")
# yellow_sword_surface = Surface.from_file("YellowSword.png")
focus_symbol_surface = Surface.from_file("ConcentrationSymbol.png")
armor_symbol_surface = Surface.from_file("ArmorSymbol.png")
vigor_symbol_surface = Surface.from_file("VigorSymbol.png")

require_surfaces = {T.Vigor: Surface.from_file("RedRequire.png"),
					T.Armor: Surface.from_file("YellowRequire.png"),
					T.Focus: Surface.from_file("BlueRequire.png")}

character_surface = Surface.from_file("Character.png")
character_highlighted_surface = Surface.from_file("CharacterHighlighted.png")

human_surface = Surface.from_file("HumanIdle.png")
human_highlighted_surface = Surface.from_file("HumanIdle.png")

wolf_enemy_surface = Surface.from_file("WolfIdle.png")
wolf_enemy_highlighted_surface = Surface.from_file("WolfIdle.png")
wolf_enemy_howl_surface = Surface.from_file("WolfEnemyHowl.png")

vigor_damage_animation = Animation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.width/2, vigor_symbol_surface.height/2)])
armor_damage_animation = Animation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.width/2, armor_symbol_surface.height/2)])
focus_damage_animation = Animation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.width/2, focus_symbol_surface.height/2)])

vigor_heal_animation = Animation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.width/2, vigor_symbol_surface.height/2)])
armor_heal_animation = Animation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.width/2, armor_symbol_surface.height/2)])
focus_heal_animation = Animation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.width/2, focus_symbol_surface.height/2)])


healthbar_width = 100
healthbar_height = 32
def draw_healthbar(game, color, pos, value, max_value, preview_damage=0):
	bar_values_x_padding = 4
	value_width, value_height = main_font_5.size(str(999))
	surface_width = vigor_symbol_surface.width + healthbar_width + value_width + bar_values_x_padding
	surface_height = max(vigor_symbol_surface.height, healthbar_height, value_height)
	surface = Surface(size=Vec(surface_width, surface_height))
	surface.set_colorkey(c.black)
	surface.fill(c.black)

	prev = Rect(Vec(0,0), Vec(0,0))
	if color == c.red:
		prev = draw_surface(target=surface, pos=Vec(0,0), surface=vigor_symbol_surface)
	elif color == c.ltblue:
		prev = draw_surface(target=surface, pos=Vec(0,0), surface=focus_symbol_surface)
	elif color == c.yellow:
		prev = draw_surface(target=surface, pos=Vec(0,0), surface=armor_symbol_surface)

	if value > 0:
		# Draw colored part of bar, capped at size of healthbar (extra points won't draw it past the bar)
		max_value = max(1, max_value)
		colored_bar_width = min(healthbar_width, healthbar_width * (value/max_value))
		if preview_damage >= value:
			# Preview damage will cover the entire normal bar, so skip drawing it and just draw the preview bar
			draw_rect(	target=surface,
						color=darken_color(color,0.5),
						pos=prev.top_right,
						size=Vec(colored_bar_width, healthbar_height))
		else:
			draw_rect(	target=surface,
						color=color,
						pos=prev.top_right,
						size=Vec(colored_bar_width, healthbar_height))

			if preview_damage != 0 and value <= max_value: # TODO: This is glitchy when value > max_value, so we just don't draw anything for now
				# Draw darker colored previewed damage section of bar.
				preview_bar_start = prev.top_right + Vec(healthbar_width * ((value-preview_damage)/max_value), 0)
				preview_bar_size = Vec(healthbar_width * (preview_damage/max_value), healthbar_height)
				draw_rect(	target=surface,
							color=darken_color(color, 0.5),
							pos=preview_bar_start,
							size=preview_bar_size)

	# Draw white outline of bar
	prev = draw_rect(	target=surface,
						color=c.white,
						pos=prev.top_right,
						size=Vec(healthbar_width, healthbar_height),
						width=1)

	amount_text_color = c.white
	if preview_damage != 0:
		# Draw the amount color darker if it will change due to damage preview
		amount_text_color = darken_color(c.white, 0.5)
	# Draw trait value text next to bar
	draw_text(	target=surface,
				color=amount_text_color,
				font=main_font_5,
				pos=Vec(prev.right + bar_values_x_padding, prev.top + healthbar_height/2),
				text="{}".format(max(0, value-preview_damage)), x_center=False)

	game.queue_surface(surface=surface, pos=pos, depth=50)

	return Rect(pos, Vec(healthbar_width, healthbar_height))

# duration - length of timer measured in frames
# action - optional function to execute once the timer finishes
class Timer:
	"""Tracks ticks and when the timer has elapsed.
	(optional) Automatically executes function once timer elapses"""
	def __init__(self, duration, action=None):
		self.duration = duration
		self.current_frame = 0
		self.action = action
	def tick(self):
		self.current_frame += 1
		if self.current_frame >= self.duration:
			if self.action:
				self.action()
			return True
		else:
			return False
	@property
	# Returns time remaining in seconds, assuming 60FPS
	def time_remaining(self):
		return (self.duration - self.current_frame) * 1/60	

def get_sprite_slot_pos(slot, team):
	x,y = 0,0 
	if team == 0:
		x = friendly_slot_positions[slot]
		y = friendly_ui_paddings[2]
	else:
		x = enemy_slot_positions[slot]
		y = enemy_ui_paddings[2]

	return Vec(x,y)



# class Friendly:
# 	def __init__(self, slot, traits, idle_animation, hover_idle_animation):
# 		self.max_traits = copy(traits)
# 		self.cur_traits = copy(self.max_traits)
# 		self.slot = slot
# 		self.team = 0
# 		self.actions = []
# 		self.action_points = 1

# 		self.idle_animation = copy(idle_animation)
# 		self.hover_idle_animation = copy(hover_idle_animation)

# 		self.action_animations = [] # Concurrent array to self.actions
# 		self.action_buttons = [] # Concurrent array to self.actions

# 		self.current_action_index = None
# 	def __deepcopy__(self, memo):
# 		other = Friendly(	slot=self.slot,
# 							traits=self.max_traits,
# 							idle_animation=self.idle_animation,
# 							hover_idle_animation=self.hover_idle_animation)

# 		other.actions = deepcopy(self.actions)
# 		other.action_animations = deepcopy(self.action_animations)
# 		other.action_buttons 
# 	def add_action(self, action):
# 		action.owner = self
# 		self.actions.append(deepcopy(action))
# 		self.action_animations.append(self.idle_animation)
# 		self.action_buttons.append(ActionButton(pos=Vec(x=friendly_slot_positions[self.slot],
# 														y=friendly_ui_paddings[3] + (len(self.actions)-1)*action_button_size.y),
# 												linked_action=action))
# 	def set_animation(self, action_index, animation):
# 		if action_index > len(self.action_animations)-1:
# 			return

# 		self.action_animations[action_index] = animation
# 	@property
# 	def rect(self):
# 		rect = self.current_animation.rect
# 		rect.pos += get_sprite_slot_pos(slot=self.slot, team=self.team)
# 		return rect
# 	@property
# 	def alive(self):
# 		if self.cur_traits[T.Vigor] > 0:
# 			return True
# 		else:
# 			return False		
# 	@property
# 	def current_animation(self):
# 		if self.current_action_index is None:
# 			return self.idle_animation
# 		else:
# 			return self.action_animations[self.current_action_index]
# 	@property
# 	def action_finished(self):
# 		if self.current_animation.finished:
# 			return True
# 		else:
# 			return False
# 	def start_action(self, action_index):
# 		if self.alive:
# 			self.current_action_index = action_index
# 	@property
# 	def action_points(self):
# 		return self._action_points
# 	@action_points.setter
# 	def action_points(self, value):
# 		self._action_points = value
# 		surface_size = main_font_5.size(str(value))
# 		self.action_points_surface = Surface(Vec.fromtuple(surface_size))

# 		# Draws action point text
# 		if self.action_points == 0:
# 			text_color = c.grey
# 		else:
# 			text_color = c.white
# 		draw_text(	target=self.action_points_surface,
# 					color=text_color,
# 					pos=Vec(0,0),
# 					text=str(self.action_points),
# 					font=main_font_5,
# 					x_center=False,
# 					y_center=False)
# 	def draw(self, target, mouse_pos, preview_action=None):
# 		if self.alive:
# 			x_pos = friendly_slot_positions[self.slot]

# 			# Draw trait bars
# 			cur_y_offset = 0 # Tracks y offset for consecutive stacked trait bars
# 			for trait, max_value in self.max_traits.items():
# 				cur_trait = self.cur_traits[trait]
# 				preview_damage = 0
# 				if preview_action is not None:
# 					preview_damage = preview_action.damages[trait]

# 				draw_healthbar(	target, trait_colors[trait],
# 								Vec(x_pos, friendly_ui_paddings[1] + cur_y_offset),
# 								cur_trait, max_value, preview_damage)

# 				cur_y_offset += healthbar_height

# 			# Draws action buttons
# 			if self.action_points > 0:
# 				for button in self.action_buttons:
# 					button.draw(target=target, mouse_pos=mouse_pos)
# 			else:
# 				for button in self.action_buttons:
# 					button.draw(target=target, mouse_pos=mouse_pos)

def play_animation(kwargs):
	game = kwargs['game']
	animation = kwargs['animation']
	pos = kwargs['pos']
	source = kwargs['source']

	if(pos == 'SelfPos'):
		game.start_animation(animation=animation, pos=	source.rect.center
														+ Vec(friendly_slot_positions[source.slot], friendly_ui_paddings[1]))

def deal_damage(kwargs):
	source = kwargs['source']
	targets = kwargs['targets']
	damages = kwargs['damages']

	global game

	if targets == TargetSet.Self:
		targets = [source]

	for target in targets:
		for trait, amount in damages.items():
			icon_pos = get_sprite_slot_pos(slot=target.slot, team=target.team) + Vec(100, -100)
			if trait == T.Vigor and amount != 0:
				# Account for armor in any vigor damage.
				armor = target.cur_traits[T.Armor]
				if amount > 0:
					target.cur_traits[trait] -= max(1, amount - armor)
				else:
					target.cur_traits[trait] -= amount

				if amount > 0:
					game.start_animation(	animation=vigor_damage_animation,
											pos=icon_pos,
											owner=source)
				else:
					game.start_animation(	animation=vigor_heal_animation,
											pos=icon_pos,
											owner=source)
			elif trait == T.Armor and amount != 0:
				target.cur_traits[trait] -= amount
				if amount > 0:
					game.start_animation(	animation=armor_damage_animation,
											pos=icon_pos,
											owner=source)
				else:
					game.start_animation(	animation=armor_heal_animation,
											pos=icon_pos,
											owner=source)
			elif trait == T.Focus and amount != 0:
				target.cur_traits[trait] -= amount
				if amount > 0:
					game.start_animation(	animation=focus_damage_animation,
											pos=icon_pos,
											owner=source)
				else:
					game.start_animation(	animation=focus_heal_animation,
											pos=icon_pos,
											owner=source)
			if target.cur_traits[trait] < 0:
				target.cur_traits[trait] = 0
				

class TargetSet(Enum):
	Nothing = 0
	All = 1
	Self = 2
	SingleAlly = 3
	OtherAlly = 4
	AllAllies = 5
	SingleEnemy = 6
	AllEnemies = 7

target_set_strings = {	TargetSet.All: "All",
						TargetSet.Self: "Self",
						TargetSet.SingleAlly: "Single Ally",
						TargetSet.OtherAlly: "Other Ally",
						TargetSet.SingleEnemy: "Single Enemy",
						TargetSet.AllEnemies: "All Enemies",
						TargetSet.AllAllies: "All Allies"}

class ActionSchematic:
	def __init__(self, name, target_set, required, damages, description=""):
		self.sub_actions = []
		self.name = name
		self.description = description
		self.target_set = target_set
		self.required = required
		self.damages = damages
	@classmethod
	def from_string(cls, s):
		name = "<PLACEHOLDER NAME>"
		description = "<PLACEHOLDER DESCRIPTION>"
		target_set = None
		required = {T.Vigor: 0, T.Armor: 0, T.Focus: 0}
		damages = {T.Vigor: 0, T.Armor: 0, T.Focus: 0}

		for line in s.splitlines():
			match = re.search('^name is (.*)', line.rstrip())
			if match:
				name = match.group(1)
				continue

			line_match = re.search('\t(has description) (.*)', line.rstrip())
			if line_match:
				arg_match = re.search('"(.*)"', line_match[2])
				if arg_match:
					description = arg_match[1]
				continue
			line_match = re.search('\t(targets) (.*)', line.rstrip())
			if line_match:
				target_set = next(key for key, value in target_set_strings.items() if value == line_match[2])
				continue
			line_match = re.search('\t(heals) (.*)', line.rstrip())
			if line_match:
				# ex "(heals) 3 Focus damage"
				match = re.search('([0-9]*) ([a-zA-Z]*)', line_match[2])
				if match:
					value = int(match[1])
					trait = next(key for key, value in trait_strings.items() if value == match[2])
					damages[trait] = -value # Negative for healing
				continue
			line_match = re.search('\t(deals) (.*)', line.rstrip())
			if line_match:
				# ex: "(deals) 5 Vigor damage"
				# TODO: "damage" optional? i.e., allow "(deals) 5 Vigor"?
				match = re.search('([0-9]*) ([a-zA-Z]*) damage', line_match[2])
				if match:
					value = int(match[1])
					trait = next(key for key, value in trait_strings.items() if value == match[2])
					damages[trait] = value				
				continue
			line_match = re.search('\t(requires) (.*)', line.rstrip())
			if line_match:
				# "(requires) 1 Focus"
				match = re.search('([0-9]*) ([a-zA-Z]*)', line_match[2])
				if match:
					value = int(match[1])
					trait = next(key for key, value in trait_strings.items() if value == match[2])
					required[trait] = value				
				continue
		return cls(	name=name,
					description=description,
					target_set=target_set,
					required=required,
					damages=damages)
	def generate_action(self, owner):
		return Action(schematic=self, owner=owner)
	def add_sub_action(self, sub_action):
		self.sub_actions.append(sub_action)
	def serialize(self):
		s = ""
		s += "name is {}\n".format(self.name)
		s += "\thas description \"{}\"\n".format(self.description)
		s += "\ttargets {}\n".format(target_set_strings[self.target_set])
		for trait, value in self.damages.items():
			if value == 0: continue
			s += "\tdeals {} {} damage\n".format(value, trait_strings[trait])
		for trait, value in self.required.items():
			if value == 0: continue
			s += "\trequires {} {}\n".format(value, trait_strings[trait])

		return s
class Action:
	def __init__(self, schematic, owner):
		self.name = schematic.name
		self.description = schematic.description
		self.target_set = schematic.target_set
		self.required = copy(schematic.required)
		self.damages = copy(schematic.damages)

		self.owner = owner

		self.sub_actions = []
		self.sub_actions.append(lambda source, targets: deal_damage(kwargs={'source': source,
																			'targets': targets, 
																			'damages': self.damages}))
	def execute(self, kwargs={}):
		if self.usable is True:
			for sub_action in self.sub_actions:
				sub_action(**kwargs)
			return True
		else:
			return False
	@property
	def usable(self):
		valid_target = False

		if self.target_set == TargetSet.OtherAlly:
			for ally in game.active_state.get_allies(team=self.owner.team):
				if ally.alive == True and ally != self.owner:
					valid_target = True
		else:
			valid_target = True

		if valid_target == False:
			return False
		for trait, value in self.owner.cur_traits.items():
			if value < self.required[trait]:
				return False
		return True
class ActionSchematicDatabase:
	def __init__(self, action_data_filepath):
		self.schematics = []

		with open(action_data_filepath) as f:
			in_action = False
			action_string = ""
			for line in f:
				if in_action == False:
					match = re.match('name is', line)
					if match:
						in_action = True
						action_string += line
						continue
				else:
					match = re.match('name is', line)
					if not match:
						action_string += line
						continue
					if match:
						# We found the beginning of the next action, so we stop here,
						# and parse everything we've found so far as an action,
						# and add it to our schematics list
						action = ActionSchematic.from_string(action_string)
						self.schematics.append(action)

						# Set next action string to begin with "name is ..."
						# and repeat the process for all lines in the data file
						action_string = line
						continue

			# If we're still in an action after end of file, we need to complete
			# adding the last action
			if in_action:
				action = ActionSchematic.from_string(action_string)
				self.schematics.append(action)
	def get_schematic_by_name(self, name):
		return next(s for s in self.schematics if s.name == name)
	def generate_action(self, name, owner):
		schematic = next(s for s in self.schematics if s.name == name)
		return schematic.generate_action(owner=owner)
		
class UnitSchematic:
	def __init__(self, name, description, traits, idle_animation, hover_idle_animation):
		self.name = name
		self.description = description
		self.traits = copy(traits)
		self.idle_animation = copy(idle_animation)
		self.hover_idle_animation = copy(hover_idle_animation)

		self.action_schematics = []
		self.action_animations = [] # Concurrent array to self.actions
	@classmethod
	def from_string(cls, s):
		name = "<PLACEHOLDER NAME>"
		description = "<PLACEHOLDER DESCRIPTION>"
		traits = {T.Vigor: 0, T.Armor: 0, T.Focus: 0}
		idle_animation = None
		hover_idle_animation = None
		action_schematics = []

		for line in s.splitlines():
			match = re.search('^name is (.*)', line.rstrip())
			if match:
				name = match.group(1)
				continue

			line_match = re.search('\t(has description) (.*)', line.rstrip())
			if line_match:
				arg_match = re.search('"(.*)"', line_match[2])
				if arg_match:
					description = arg_match[1]
				continue
			line_match = re.search('\t(uses sprite) (.*)', line.rstrip())
			if line_match:
				arg_match = re.search('"(.*)"', line_match[2])
				if arg_match:
					sprite_path = arg_match[1]
					idle_surface = Surface.from_file(filepath=sprite_path)
					idle_animation = Animation(	sprites=[idle_surface],
													duration=60,
													sprite_lengths=[60],
													anchor_points=[Vec(0,idle_surface.height)])
					hover_idle_animation = idle_animation
				continue			
			line_match = re.search('\thas (.*)', line.rstrip())
			if line_match:
				# ex: "(has) 50 Vigor"
				# or: "(has) action Rest"
				match = re.search('([0-9]+) ([a-zA-Z]*)', line_match[1])
				if match:
					value = int(match[1])
					trait = next(key for key, value in trait_strings.items() if value == match[2])
					traits[trait] = value
					continue
				match = re.search('action (.*)', line_match[1])					
				if match:
					action_name = match[1]
					schematic = game.action_db.get_schematic_by_name(action_name)
					action_schematics.append(schematic)
					continue

		# Generate unit schematic
		new = cls(	name=name,
					description=description,
					traits=traits,
					idle_animation=idle_animation,
					hover_idle_animation=hover_idle_animation)
		new.action_schematics = action_schematics
		# Just fill the action_animations list with our idle animations.
		# They'll be replaced later when the animations are read from
		# data files
		new.action_animations = [idle_animation]*len(action_schematics) 

		return new
	def generate_unit(self, team, slot):
		return Unit(schematic=self, team=team, slot=slot)
	# def set_animation(self, action_index, animation):
	# 	if action_index > len(self.action_animations)-1:
	# 		return

	# 	self.action_animations[action_index] = animation
	def serialize(self):
		s = ""
		s += "name is {}\n".format(self.name)
		for trait, value in self.max_traits.items():
			if value == 0: continue
			s += "\thas {} {}\n".format(value, trait_strings[trait])
		for action in self.actions:
			s += "\thas action {}\n".format(action.name)

		return s
class Unit:
	def __init__(self, team, slot, schematic):
		self.team = team
		self.slot = slot
		self.max_traits = copy(schematic.traits)
		self.cur_traits = copy(schematic.traits)
		self.idle_animation = deepcopy(schematic.idle_animation)
		self.hover_idle_animation = deepcopy(schematic.hover_idle_animation)
		self.actions = [schematic.generate_action(owner=self) for schematic in schematic.action_schematics]
		self.action_animations = deepcopy(schematic.action_animations)#deepcopy(schematic.action_animations) # Concurrent array to self.actions

		for action in self.actions:
			action.owner = self	
		self.action_buttons = [ActionButton(pos=Vec(x=get_slot_x_pos(team=self.team, slot=self.slot),
													y=get_team_ui_padding(team=self.team, index=3) + i*action_button_size.y),
												linked_action=action) for i, action in enumerate(self.actions)]
		
		self.action_points = 1
		self.current_action_index = None
		self.current_action_targets = None
	@property
	def current_animation(self):
		if self.current_action_index is None:
			return self.idle_animation
		else:
			if len(self.action_animations) != 0:
				return self.action_animations[self.current_action_index]
			else:
				return self.idle_animation
	@property 
	def action_finished(self):
		if self.current_action_index == None or self.alive == False:
			return True
		else:
			return False
	@property
	def current_action(self):
		if self.current_action_index != None:
			return self.actions[self.current_action_index]
		else:
			return None
	@property
	def rect(self):
		rect = self.current_animation.rect
		rect.pos += get_sprite_slot_pos(slot=self.slot, team=self.team)
		return rect
	def start_action(self, action, targeted, valid_targets):
		if self.alive:
			self.current_action_index = next(i for i,a in enumerate(self.actions) if a==action)
			targets = valid_targets
			if action.target_set is TargetSet.SingleAlly:
				targets = [targeted]
			elif action.target_set == TargetSet.Self and targeted == self:
				targets = [self]
			elif action.target_set is TargetSet.SingleEnemy:
				targets = [targeted]

			self.current_action_targets = targets
			self.current_action.execute(kwargs={'source': self,
												'targets': targets})				
			self.action_points -= 1
	def start_random_action(self, allies, enemies):
		if self.alive:
			possible_actions_indices = [] # Actions which have their pre-reqs fulfilled
			# Check each of our actions, and add them to the list of possible random actions
			for i,action in enumerate(self.actions):
				if action.usable:

					possible_actions_indices.append(i)

			if len(possible_actions_indices) == 0:
				# We have no valid actions. Return and do nothing.
				return

			self.current_action_index = random.choice(possible_actions_indices)
			self.current_action_targets = []

			action = self.actions[self.current_action_index]	
			if action.target_set == TargetSet.Self:
				self.current_action_targets = [self]
			elif action.target_set == TargetSet.SingleAlly:
				non_dead_allies = [e for e in allies if e.alive == True]
				if len(non_dead_allies) > 0:
					self.current_action_targets = [random.choice(non_dead_allies)]
			elif action.target_set == TargetSet.OtherAlly:
				non_self_non_dead_allies = [e for e in allies if e != self and e.alive == True]
				if len(non_self_non_dead_allies) > 0:
					self.current_action_targets = [random.choice(non_self_non_dead_allies)]
			elif action.target_set == TargetSet.AllAllies:
				non_dead_allies = [e for e in allies if e.alive == True]				
				if len(non_dead_allies) > 0:
					self.current_action_targets = non_dead_allies
			elif action.target_set == TargetSet.SingleEnemy:
				if len(enemies) > 0:
					self.current_action_targets = [random.choice(enemies)]
			elif action.target_set == TargetSet.AllEnemies:
				if len(enemies) > 0:
					self.current_action_targets = enemies

			if self.current_action_index != None and self.current_action_targets != None:
				self.current_animation.restart()

			self.actions[self.current_action_index].execute(kwargs={'source': self,
																	'targets':self.current_action_targets})

	def update(self, frame_count=1):
		if self.current_action_index is not None:
			self.current_animation.update(frame_count)

			# Switch back to animation-less sprite once animation is finished
			if self.current_animation.finished is True:
				self.current_action_index = None
				self.current_action_targets = None
	def draw(self, target, mouse_pos, preview_action=None):
		if self.check_hover(mouse_pos=mouse_pos) == True:
			hover = True
		else:
			hover = False
		if self.alive:
			x_pos = get_slot_x_pos(team=self.team, slot=self.slot)

			y_offset = 0
			prev = Rect(Vec(0,0),Vec(0,0))
			for trait, max_value in self.max_traits.items():
				cur_trait = self.cur_traits[trait]
				preview_damage = 0
				if preview_action is not None:
					if trait == T.Vigor and preview_action.damages[T.Vigor] > 0:
						# Account for armor in preview damage
						armor = self.cur_traits[T.Armor]
						preview_damage = max(1, preview_action.damages[trait] - armor)
					else:
						preview_damage = preview_action.damages[trait]

				# Draws trait bars
				draw_healthbar(	game=game,
								color=trait_colors[trait],
								pos=Vec(x_pos, get_team_ui_padding(team=self.team, index=1) + y_offset),
								value=cur_trait,
								max_value=max_value,
								preview_damage=preview_damage)

				y_offset += healthbar_height

			# Draws unit sprite
			if hover:
				self.current_animation.draw(game=game,
											pos=Vec(x_pos, get_team_ui_padding(team=self.team, index=2)))
			else:
				self.current_animation.draw(game=game,
											pos=Vec(x_pos, get_team_ui_padding(team=self.team, index=2)))

			# Draws action buttons
			for button in self.action_buttons:
				#if button.linked_action == self.current_action:
				if button.linked_action == preview_action:
					force_highlight = True
				else:
					force_highlight = False

				button.draw(game=game, mouse_pos=mouse_pos, force_highlight=force_highlight)

	@property
	def alive(self):
		if self.cur_traits[T.Vigor] > 0:
			return True
		else:
			return False
	def check_hover(self, mouse_pos):
		if(
				mouse_pos.x >= enemy_slot_positions[self.slot]
			and mouse_pos.x <  enemy_slot_positions[self.slot] + 200
			and mouse_pos.y >= 0
			and mouse_pos.y <  screen_height
		):
			return True
		else:
			return False		
class UnitSchematicDatabase:
	def __init__(self, unit_data, animation_data):
		self.schematics = []
		with open(unit_data) as f:
			in_unit = False
			unit_string = ""
			for line in f:
				if in_unit == False:
					match = re.match('name is', line)
					if match:
						in_unit = True
						unit_string += line
						continue
				else:
					match = re.match('name is', line)
					if not match:
						unit_string += line
						continue
					if match:
						# We found the beginning of the next unit, so we stop here,
						# and parse everything we've found so far as an unit,
						# and add it to our schematics list
						unit = UnitSchematic.from_string(unit_string)
						self.schematics.append(unit)

						# Set next unit string to begin with "name is ..."
						# and repeat the process for all lines in the data file
						unit_string = line
						continue

			# If we're still in an unit after end of file, we need to complete
			# adding the last unit
			if in_unit:
				unit = UnitSchematic.from_string(unit_string)
				self.schematics.append(unit)

		# Fetch animations for all the units from animations data file
		with open(animation_data) as f:
			in_schematic = False
			unit_index = None
			action_index = None			
			string = ""
			while line:
				match = re.search('^([a-zA-Z]*)\'s (.*)', line.rstrip())
				if match:
					if unit_index == None:
						# This is the beginning of an animation
						unit_index, unit_schematic = next((i,s) for i,s in enumerate(self.schematics) if s.name == match[1])
						action_index = next(i for i,a in enumerate(unit_schematic.action_schematics) if a.name == match[2])
						string += line
					else:
						# This is the beginning of an animation, and
						# we've reached the end of the previous animation string
						anim = Animation.from_string(string)
						self.schematics[unit_index].action_animations[action_index] = anim
						unit_index, unit_schematic = next((i,s) for i,s in enumerate(self.schematics) if s.name == match[1])
						action_index = next(i for i,a in enumerate(unit_schematic.action_schematics) if a.name == match[2])
						string = line
				else:
					string += line

				line = f.readline()

			if string:
				# If there's still an animation, add it
				anim = Animation.from_string(string)
				self.schematics[unit_index].action_animations[action_index] = anim


	def get_list_of_schematic_names(self):
		return [s.name for s in self.schematics]
	def get_schematic_by_name(self, name):
		return next(s for s in self.schematics if s.name == name)				
	def generate_unit(self, name, team, slot):
		schematic = next(s for s in self.schematics if s.name == name)
		return schematic.generate_unit(team=team, slot=slot)

action_button_size =  Vec(150,60)
action_info_size = Vec(200,70)
class ActionButton:
	def __init__(self, pos, linked_action):
		self.pos = pos
		self.size = action_button_size
		self.linked_action = linked_action

		self.surface = None
		self.hover_surface = None
		self.unable_surface = None # Surface if action requirements aren't mean
		self.info_box_surface = None
		self.refresh_surfaces()
	@property
	def owner(self):
		return self.linked_action.owner
	def refresh_surfaces(self):
		# Non-hovered surface
		back_color = c.dkgrey
		border_color = c.grey
		text_color = c.grey

		self.surface = Surface(self.size)

		# Button background and border
		draw_rect(target=self.surface, color=back_color, pos=Vec(0,0), size=self.size, width=0)
		draw_rect(target=self.surface, color=border_color, pos=Vec(0,0), size=self.size, width=1)

		# Action name text
		prev_line = draw_text(	target=self.surface, color=text_color, pos=Vec(action_button_size.x/2, 0),
								text=self.linked_action.name, x_center=True, y_center=False, font=main_font_5_u)
		prev = prev_line
		for trait, required in self.linked_action.required.items():
			if required != 0:
				pass
				#s = require_surfaces[trait]
				# Required trait image next to skill name
				# prev = draw_surface(target=self.surface, pos=prev.center_right+Vec(s.get_width()/2 + 8, 0), surface=require_surfaces[trait],
				# 					x_align=AlignX.Center, y_align=AlignY.Center)
				# Required trait text (i.e., amount required) on top of each req. trait image
				# draw_text(	target=self.surface, color=c.white, pos=prev.center,
				# 			text=str(required), x_center=True, y_center=True, font=main_font_10)

				# X out the trait if the owner doesn't fulfill that requirement
				# if(self.linked_action.owner.cur_traits[trait] < required):
				# 	draw_x(target=self.surface, color=c.grey, rect=prev)

		# Target set text
		# prev = draw_text(	target=self.surface, color=text_color, pos=prev_line.bottom_left, text=target_set_strings[self.linked_action.target_set],
		# 					x_center=False, y_center=False, font=main_font_4)

		# Trait sword icons and overlay'd damage text for the action
		for trait, damage in self.linked_action.damages.items():
			if damage != 0:
				prev = draw_surface(target=self.surface, pos=prev.center_bottom, surface=sword_surfaces[trait], x_align=AlignX.Center)
				draw_text(target=self.surface, color=c.white, pos=prev.center, text=str(self.linked_action.damages[trait]), font=main_font_7)

		# Hovered surface
		hover_back_color = c.ltgrey
		hover_border_color = c.red
		hover_text_color = c.white	

		self.hover_surface = Surface(self.size)

		# Button background and border
		draw_rect(target=self.hover_surface, color=hover_back_color, pos=Vec(0,0), size=self.size, width=0)
		draw_rect(target=self.hover_surface, color=hover_border_color, pos=Vec(0,0), size=self.size, width=1)

		# Action name text
		prev_line = draw_text(	target=self.hover_surface, color=hover_text_color, pos=Vec(action_button_size.x/2, 0),
								text=self.linked_action.name, x_center=True, y_center=False, font=main_font_5_u)
		prev = prev_line
		for trait, required in self.linked_action.required.items():
			if required != 0:
				pass
				#s = require_surfaces[trait]
				# Required trait image next to skill name
				# prev = draw_surface(target=self.hover_surface, pos=prev.center_right+Vec(s.get_width()/2 + 8, 0), surface=require_surfaces[trait],
				# 					x_align=AlignX.Center, y_align=AlignY.Center)
				# Required trait text (i.e., amount required) on top of each req. trait image
				# draw_text(	target=self.hover_surface, color=hover_c.white, pos=prev.center,
				# 			text=str(required), x_center=True, y_center=True, font=main_font_10)

				# X out the trait if the owner doesn't fulfill that requirement
				# if(self.linked_action.owner.cur_traits[trait] < required):
				# 	draw_x(target=self.hover_surface, color=hover_c.grey, rect=prev)

		# Target set text
		# prev = draw_text(	target=self.hover_surface, color=hover_text_color, pos=prev_line.bottom_left, text=target_set_strings[self.linked_action.target_set],
		# 					x_center=False, y_center=False, font=main_font_4)

		# Trait sword icons and overlay'd damage text for the action
		for trait, damage in self.linked_action.damages.items():
			if damage != 0:
				prev = draw_surface(target=self.hover_surface, pos=prev.center_bottom, surface=sword_surfaces[trait], x_align=AlignX.Center)
				draw_text(target=self.hover_surface, color=c.white, pos=prev.center, text=str(self.linked_action.damages[trait]), font=main_font_7)

		# Info box surface
		self.info_box_surface = Surface(action_info_size)

		# Background box and border
		draw_rect(target=self.info_box_surface, color=[50]*3, pos=Vec(0,0), size=action_info_size, width=0)
		draw_rect(target=self.info_box_surface, color=c.white, pos=Vec(0,0), size=action_info_size, width=1)
		prev=draw_text(	target=self.info_box_surface, color=c.white, pos=Vec(action_info_size.x/2, 0),
						text=self.linked_action.name, font=main_font_5_u, x_center=True, y_center=False)
		#target, text, pos, font, color=c.white, word_wrap_width=None):
		prev=draw_text_wrapped(	target=self.info_box_surface, color=c.white, pos=Vec(action_info_size.x*0.1, prev.bottom),
								text=self.linked_action.description, font=main_font_4, word_wrap_width=action_info_size.x*0.9)

		# Unable Surface
		self.unable_surface = copy(self.surface)
		draw_x(target=self.unable_surface, color=c.red, rect=Rect(pos=Vec(0,0), size=action_button_size))

	def draw_info_box(self, mouse_pos):
		game.queue_surface(surface=self.info_box_surface, depth=10, pos=mouse_pos)
	def draw(self, game, mouse_pos, force_highlight=False):
		if self.linked_action.usable == False:
			game.queue_surface(depth=20, surface=self.unable_surface, pos=self.pos)
		elif self.check_hover(mouse_pos=mouse_pos) == True or force_highlight == True:
			game.queue_surface(depth=20, surface=self.hover_surface, pos=self.pos)
			if self.owner.team == 0:
				self.draw_info_box(mouse_pos=mouse_pos)
		else:
			game.queue_surface(depth=20, surface=self.surface, pos=self.pos)			

		# Return extent of drawn button
		return self.rect
	def check_hover(self, mouse_pos):
		if(
				mouse_pos.x >= self.pos.x
			and mouse_pos.x <  self.pos.x + self.size.x
			and mouse_pos.y >= self.pos.y
			and mouse_pos.y <  self.pos.y + self.size.y
		):
			return True
		else:
			return False

	@property
	def rect(self):
		return Rect(self.pos, self.size)

	def __deepcopy__(self, memo):
		# TODO: Should action buttons ever really be copy'd or deepcopy'd? Almost everything
		# 		has to be changed anyway.
		# self.pos = pos
		# self.size = action_button_size
		# self.linked_action = linked_action
		# self.surface = None
		# self.hover_surface = None
		# self.refresh_surfaces()
		other = ActionButton(	pos=self.pos,
								linked_action=self.linked_action)


	

class Turn:
	def __init__(self, initial_active=True):
		self.player_active = initial_active
		self.current_enemy = None
	def end_turn(self, friendlies, enemies):
		if self.player_active is True:
			# Switch from player's turn to enemy's turn
			self.player_active = False
			self.current_enemy = 0
			enemies[self.current_enemy].start_random_action(allies=enemies, enemies=friendlies) # Opposite from perspective of enemies
		else:
			# Switch back from enemy's turn to player's turn
			for friendly in friendlies:
				friendly.action_points = 1
			self.player_active = True
			self.current_enemy = None

	def update(self, friendlies, enemies):
		# If enemy is no longer animating, move on to the next enemy.
		# If last enemy is finished, turn goes back to player
		if self.current_enemy != None and self.player_active == False:
			if enemies[self.current_enemy].action_finished:
				self.current_enemy += 1

				if(self.current_enemy >= len(enemies)):
					self.end_turn(friendlies=friendlies, enemies=enemies)
				else:
					enemies[self.current_enemy].start_random_action(allies=enemies, enemies=friendlies)
		if self.current_enemy == None and self.player_active == False:
			self.end_turn(friendlies=friendlies, enemies=enemies)

def friendly_slot_intersect(pos, slot):
	"""Returns True if [pos] is within the bounds of friendly slot [slot]"""

	if 	(		pos.x >= friendly_slot_positions[slot]
			and pos.x < friendly_slot_positions[slot]+200
			and pos.y >= 0
			and pos.y < screen_height):
		return True
	else:
		return False

def enemy_slot_intersect(pos, slot):
	"""Returns True if [pos] is within the bounds of enemy slot [slot]"""

	if 	(		pos.x >= enemy_slot_positions[slot]
			and pos.x < enemy_slot_positions[slot]+200
			and pos.y >= 0
			and pos.y < screen_height):
		return True
	else:
		return False

def slot_intersect(pos, team, slot):
	if team == 0:
		return friendly_slot_intersect(pos=pos, slot=slot)
	elif team == 1:
		return enemy_slot_intersect(pos=pos, slot=slot)


def friendly_is_valid_target(action, target):
	if action.target_set == TargetSet.All:
		return True
	if action.target_set == TargetSet.SingleAlly:
		return True
	if action.target_set == TargetSet.AllAllies:
		return True
	if action.target_set == TargetSet.Self and action.owner == target:
		return True

	return False

def enemy_is_valid_target(action, target):
	if action.target_set == TargetSet.All:
		return True
	if action.target_set == TargetSet.SingleEnemy:
		return True
	if action.target_set == TargetSet.AllEnemies:
		return True

	return False



class MainMenuState:
	def __init__(self):
		self.buttons = []
		self.buttons.append(Button(	pos=Vec(100,100),
									size=Vec(150,70),
									text="Start Campaign",
									function=lambda: game.start_campaign()))		
		self.buttons.append(Button(	pos=Vec(100,170),
									size=Vec(150,70),
									text="Test Battle",
									function=lambda: game.start_battle()))
		self.buttons.append(Button(	pos=Vec(100,240),
									size=Vec(150,70),
									text="Editor",
									function=lambda: game.start_editor()))
		self.buttons.append(Button(	pos=Vec(100,310),
									size=Vec(150,70),
									text="Exit",
									function=lambda: sys.exit()))		

	def enter(self):
		pass
	def exit(self):
		sys.exit()
	def draw(self, game):
		for button in self.buttons:
			button.draw(game=game)

		game.queue_surface(surface=pointer_cursor_surface, depth=-100, pos=game.mouse_pos)

	def update(self, game):
		for button in self.buttons:
			button.update(game=game)

	def mouse_button_pressed(self, game, button, mouse_pos):
		pass
	def key_pressed(self, game, key, mod, translated):
		pass

# class Button:
# 	def __init__(self, rect, font, text):
# 		self.rect = rect		
# 		self.font = font
# 		self.text = text

# 	def draw(self, game):
# 		# Button background color
# 		game.queue_drawrect(pos=self.rect.top_left,
# 							size=self.rect.size,
# 							color=c.ltgrey,
# 							width=0,
# 							depth=-2)		
# 		# Button border
# 		game.queue_drawrect(pos=self.rect.top_left,
# 							size=self.rect.size,
# 							color=c.white,
# 							width=1,
# 							depth=-1)

class Button:
	def __init__(self, pos, size, text, function):
		self.pos = pos
		self.size = size
		self.text = text
		self.function = function

		self.surface = Surface(size=self.size)
		self.surface.fill(c.dkgrey)
		draw_rect(	target=self.surface,
					color=c.white,
					pos=Vec(0,0),
					size=size,
						width=1)
		draw_text(	target=self.surface,
					color=c.white,
					pos=Vec(size.x/2, size.y/2),
					text=self.text,
					font=main_font_5,
					x_center=True,
					y_center=True)

		self.hover_surface = Surface(size=self.size)
		self.hover_surface.fill(c.ltgrey)
		draw_rect(	target=self.hover_surface,
					color=c.white,
					pos=Vec(0,0),
					size=size,
					width=1)
		draw_text(	target=self.hover_surface,
					color=c.white,
					pos=Vec(size.x/2, size.y/2),
					text=self.text,
					font=main_font_5,
					x_center=True,
					y_center=True)

		self.hovered = False
	@property
	def rect(self):
		return Rect(self.pos, self.size)
	
	def update(self, game):
		if self.intersect(pos=game.mouse_pos):
			self.hovered = True
		else:
			self.hovered = False

		if game.input.pressed(button=0) and self.hovered:
			self.function()
	def draw(self, game):
		if self.hovered == True:
			game.queue_surface(	surface=self.hover_surface,
								pos=self.pos,
								depth=0)
		else:
			game.queue_surface(	surface=self.surface,
								pos=self.pos,
								depth=0)			
	def intersect(self, pos):
		if (	pos.x > self.rect.left
			and pos.x < self.rect.right
			and pos.y > self.rect.top
			and pos.y < self.rect.bottom
		):
			return True

		return False

class TextBox:
	def __init__(self, rect, font, initial_text=''):
		self.rect = rect		
		self.font = font
		self.text = initial_text

		self.char_rects = []
		self.refresh_char_rects()

		self.focused = False
		self._cursor_pos = 0

		self.highlight_start = None
		self.highlight = [0,0] # Indices of the start and end of the text highlight

		# Controls the blinking of the edit cursor.
		# blink_timer is the frame counter
		# Toggles visibility every time blink_period frames have elapsed
		self.blink_visible = True
		self.blink_timer = 0
		self.blink_period = 30
	@property
	def text(self):
		return self._text
	@text.setter
	def text(self, text):
		self._text = text
		self.refresh_char_rects()
		self.blink_visible = True
		self.blink_timer = 0		

	@property
	def cursor_pos(self):
		return self._cursor_pos
	@cursor_pos.setter
	def cursor_pos(self, cursor_pos):
		self._cursor_pos = cursor_pos
		self.blink_visible = True
		self.blink_timer = 0
	
	
	def refresh_char_rects(self, start_index=0):
		'''Calculate the positions of each character in self.text,
		to use to place the edit cursor.

		start_pos tells the function to start at a specific index of
		self.text, so we don't have to calculate all char_x_positions
		when only some of them at the end of the string changed.'''
		self.char_rects = []
		for i in range(start_index, len(self.text)):
			sub_string = self.text[0:i]
			sub_string_width, _ = self.font.size(sub_string)
			char_width, _ = self.font.size(self.text[i])

			pos = Vec(sub_string_width, 0)
			size = Vec(char_width, self.rect.height)
			self.char_rects.append(Rect(pos=pos, size=size))
			#self.char_x_positions.append(w)

		string_width, _ = self.font.size(self.text)
		self.char_rects.append(Rect(pos=Vec(string_width, 0), size=Vec(0,0)))

	def pos_to_char_index(self, pos):
		rel_x, _ = pos - self.rect.top_left

		char_index = 0

		if len(self.text) == 0:
			# Empty string should return left-most pos in textbox (index 0)
			return char_index

		# TODO: A binary search would probably be faster here, if it's necessary		
		for i, r in enumerate(self.char_rects):
			if rel_x < r.center.x:
				char_index = i
				break

		if rel_x >= self.char_rects[-1].center.x:
			char_index = last_index(self.char_rects)

		return char_index

	def highlight_all(self):
		self.cursor_pos = last_index(self.char_rects)
		self.highlight = [0, last_index(self.char_rects)]

	def focus(self, mouse_pos=None):
		'''Set this textbox to edit mode with the cursor at the correct pos'''
		self.focused = True

		if mouse_pos != None:
			rel_pos = mouse_pos - self.rect.top_left
			self.cursor_pos = self.pos_to_char_index(pos=mouse_pos)

			self.highlight_start = self.cursor_pos
		else:
			self.cursor_pos = 0
	

	def unfocus(self):
		self.focused = False
		self.highlight = [0,0]

	def _backspace(self):
		if self.highlight[0] == self.highlight[1]:
			if self.cursor_pos == 0:
				# Backspace does nothing if cursor is completely to the left.
				return			
			self.text = self.text[0:self.cursor_pos-1] + self.text[self.cursor_pos:]
			self.cursor_pos = max(0, self.cursor_pos-1)
		else:
			start = self.highlight[0]
			end = self.highlight[1]
			self.text = self.text[0:start] + self.text[end:]

			self.cursor_pos = start

		self.highlight = [self.cursor_pos, self.cursor_pos]

	def _delete(self):
		if self.cursor_pos == last_index(self.char_rects):
			# Delete does nothing if cursor is completely to the right.
			return

		i = self.cursor_pos
		self.text = self.text[0:i] + self.text[i+1:]

	def _cursor_left(self, highlight=False):
		start_pos = self.cursor_pos

		if highlight == True:
			self.cursor_pos = max(self.cursor_pos-1, 0)			
			if start_pos == self.highlight[0]:
				self.highlight[0] = self.cursor_pos
			elif start_pos == self.highlight[1]:
				self.highlight[1] = self.cursor_pos
			else:
				print("self.cursor_pos is not equal to either highlight[0] nor highlight[1]. Something went wrong.")
		elif highlight == False:
			if self.highlight[0] != self.highlight[1]:
				self.cursor_pos = self.highlight[0]
			else:
				self.cursor_pos = max(self.cursor_pos-1, 0)

			self.highlight = [self.cursor_pos, self.cursor_pos]

		if self.highlight[0] > self.highlight[1]:
			buf = self.highlight[0]
			self.highlight[0] = self.highlight[1]
			self.highlight[1] = buf

	def _cursor_right(self, highlight=False):
		start_pos = self.cursor_pos

		if highlight == True:
			self.cursor_pos = min(self.cursor_pos+1, len(self.char_rects)-1)				
			if start_pos == self.highlight[0]:
				self.highlight[0] = self.cursor_pos
			elif start_pos == self.highlight[1]:
				self.highlight[1] = self.cursor_pos
			else:
				print("self.cursor_pos is not equal to either highlight[0] nor highlight[1]. Something went wrong.")
		elif highlight == False:
			if self.highlight[0] != self.highlight[1]:
				self.cursor_pos = self.highlight[1]
			else:
				self.cursor_pos = min(self.cursor_pos+1, len(self.char_rects)-1)	

			self.highlight = [self.cursor_pos, self.cursor_pos]

		if self.highlight[0] > self.highlight[1]:
			buf = self.highlight[0]
			self.highlight[0] = self.highlight[1]
			self.highlight[1] = buf			

	def update(self, game):
		self.blink_timer += 1
		if self.blink_timer >= self.blink_period:
			self.blink_timer = 0			
			self.blink_visible = not self.blink_visible

	def draw(self, game, debug=False):
		w, h = main_font_10.size(self.text)		

		# Textbox outline
		game.queue_drawrect(pos=self.rect.top_left,
							size=self.rect.size,
							color=c.ltgrey,
							width=1,
							depth=-1)
		# Highlight background
		if self.highlight[0] != self.highlight[1]:
			start_rect = self.char_rects[self.highlight[0]]
			end_rect = self.char_rects[self.highlight[1]]
			game.queue_drawrect(pos=self.rect.top_left + start_rect.top_left,
								size=Vec(end_rect.left - start_rect.left, self.rect.height),
								color=c.grey,
								width=0,
								depth=10)
		# Text
		game.queue_drawtext(color=c.white,
							pos=self.rect.bottom_left-Vec(0,main_font_10.get_linesize()),
							text=self.text,
							font=self.font,
							x_center=False,
							y_center=False,
							depth=5)

		if self.focused:
			if self.blink_visible:
				x_pos = self.char_rects[self.cursor_pos].left
				game.queue_drawline(start=Vec(self.rect.left+x_pos, self.rect.top),
									end=Vec(self.rect.left+x_pos, self.rect.bottom),
									color=c.red,
									width=1,
									depth=-50)

		if debug:
			for x_pos in self.char_rects[self.cursor_pos].left:
				game.queue_drawline(start=Vec(self.rect.left+x_pos, self.rect.top),
									end=Vec(self.rect.left+x_pos, self.rect.bottom),
									color=c.red,
									width=1,
									depth=-50)

	def key_pressed(self, game, key, mod, translated):
		if self.focused:
			if key == pg.K_LEFT:
				highlight = game.input.down(key=pg.K_LSHIFT) or game.input.down(key=pg.K_RSHIFT)
				self._cursor_left(highlight=highlight)
			if key == pg.K_RIGHT:
				highlight = game.input.down(key=pg.K_LSHIFT) or game.input.down(key=pg.K_RSHIFT)
				self._cursor_right(highlight=highlight)
			if key == pg.K_BACKSPACE:
				self._backspace()
			if key == pg.K_DELETE:
				self._delete()
			if key == pg.K_END:
				self.cursor_pos = last_index(self.char_rects)
				self.highlight = [self.cursor_pos, self.cursor_pos]
			if key == pg.K_HOME:
				self.cursor_pos = 0
				self.highlight = [self.cursor_pos, self.cursor_pos]				

			if game.input.down(button=0) and self.highlight_start != None:
				i = self.pos_to_char_index(pos=game.mouse_pos)
				self.cursor_pos = i
				if i >= self.highlight_start:
					self.highlight[0] = self.highlight_start
					self.highlight[1] = i
				else:
					self.highlight[0] = i
					self.highlight[1] = self.highlight_start

		if translated in typeable_chars:
			if self.highlight[0] == self.highlight[1]:
				i = self.cursor_pos
				self.text = self.text[0:i] + translated + self.text[i:]
				self.cursor_pos += 1
			else:
				start = self.highlight[0]
				end = self.highlight[1]
				self.text = self.text[0:start] + translated + self.text[end:]

				self.cursor_pos = start + 1

			self.highlight = [self.cursor_pos, self.cursor_pos]


class EditorState:
	def __init__(self):
		self.entry_list_start = Vec(0, 100)
		self.entry_height = 50
		self.left_pane_width = 400

		self.selected_entry = None
		self.focused_index = None
		self.ui_elements = [None] * len(c.unit_ui_indices)
		# Name textbox
		for i, property_string in enumerate(c.unit_ui_indices):
			self.ui_elements[i] = TextBox(	rect=Rect(	pos=Vec(self.left_pane_width + 20, 50+i*50),
														size=Vec(150, 50)),
											font=main_font_10,
											initial_text="<{}>".format(property_string))

		# self.ui_elements[unit_name_ui_index] = 	TextBox(rect=Rect(	pos=Vec(self.left_pane_width + 20, 50),
		# 															size=Vec(150, 50)),
		# 												font=main_font_10,
		# 												initial_text="<NAME>")

		# # Description textbox
		# self.ui_elements[unit_description_ui_index] =	TextBox(rect=Rect(	pos=Vec(self.left_pane_width + 20, 100),
		# 																	size=Vec(150, 50)),
		# 														font=main_font_5,
		# 														initial_text="<DESCRIPTION>")

		# # Trait value textboxes
		# self.ui_elements[] =	TextBox(rect=Rect(	pos=Vec(self.left_pane_width + 20, 150),
		# 											size=Vec(150, 50)),
		# 								font=main_font_5,
		# 								initial_text="<VIGOR>")
		# self.ui_elements[] =	TextBox(rect=Rect(	pos=Vec(self.left_pane_width + 20, 200),
		# 											size=Vec(150, 50)),
		# 								font=main_font_5,
		# 								initial_text="<ARMOR>")
		# self.ui_elements[] =	TextBox(rect=Rect(	pos=Vec(self.left_pane_width + 20, 250),
		# 											size=Vec(150, 50)),
		# 								font=main_font_5,
		# 								initial_text="<FOCUS>")	
	def enter(self):
		pass
	def exit(self):
		pass								
	def update(self, game):
		# Left Pane

		# Index of entry in the left pane which is currently hovered.
		entry_hover_index = math.floor(float(game.mouse_pos.y - self.entry_list_start.y) / float(self.entry_height))

		x, y = self.entry_list_start
		unit_names = game.unit_db.get_list_of_schematic_names()
		# Draw entries in left pane
		for i, name in enumerate(unit_names):
			game.queue_drawline(start=Vec(0,y),
								end=Vec(self.left_pane_width,y),
								color=c.grey,
								depth=-1)
			game.queue_drawtext(color=c.white,
								pos=Vec(x,y),
								text=name,
								font=main_font_10,
								x_center=False,
								y_center=False,
								depth=10)
			y += 50

		if game.input.pressed(button=0):
			if self.focused_index != None:
				self.ui_elements[self.focused_index].unfocus()
				self.focused_index = None

		if len(self.ui_elements) > 0:
			if game.input.pressed(key=pg.K_TAB):
				if self.focused_index == None:
					self.focused_index = 0
				else:
					self.ui_elements[self.focused_index].unfocus()
					
					self.focused_index += 1
					if self.focused_index > last_index(self.ui_elements):
						self.focused_index = 0

				self.ui_elements[self.focused_index].focus()
				self.ui_elements[self.focused_index].highlight_all()


		if in_range(entry_hover_index, 0, len(unit_names)) and game.mouse_pos.x <= self.left_pane_width:
			game.queue_drawrect(color=c.ltgrey,
								pos=Vec(0,self.entry_list_start.y+entry_hover_index*self.entry_height),
								size=Vec(self.left_pane_width, self.entry_height),
								depth=50)

			if game.input.pressed(button=0):
				self.selected_entry = game.unit_db.get_schematic_by_name(name=unit_names[entry_hover_index])
				self.ui_elements[c.unit_ui_indices.index('name')].text = self.selected_entry.name
				self.ui_elements[c.unit_ui_indices.index('description')].text = self.selected_entry.description
				self.ui_elements[c.unit_ui_indices.index('vigor')].text = str(self.selected_entry.traits[T.Vigor])
				self.ui_elements[c.unit_ui_indices.index('armor')].text = str(self.selected_entry.traits[T.Armor])
				self.ui_elements[c.unit_ui_indices.index('focus')].text = str(self.selected_entry.traits[T.Focus])




		# Right pane

		textbox_hovered = False
		if self.selected_entry != None:
			for i, t in enumerate(self.ui_elements):
				t.draw(game=game, debug=False)

				if t.rect.intersect(point=game.mouse_pos):
					textbox_hovered = True					
					if game.input.pressed(button=0):
						# Left mouse pressed while hovering a textbox
						if self.focused_index != None:
							self.ui_elements[self.focused_index].unfocus()
						t.focus(mouse_pos=game.mouse_pos)
						self.focused_index = i

		if self.focused_index != None:
			# Stuff to check if there's a currently focused UI element
			pass


		if textbox_hovered:
			game.queue_surface(surface=edit_cursor_surface, depth=-100, pos=game.mouse_pos)
		else:
			game.queue_surface(surface=pointer_cursor_surface, depth=-100, pos=game.mouse_pos)

		for t in self.ui_elements:
			t.update(game=game)

	def draw(self, game):
		# Separator line between left and right pane
		game.queue_drawline(	start=Vec(self.left_pane_width, 0),
								end=Vec(self.left_pane_width, screen_height),
								color=c.green,
								depth=-1)
	def mouse_button_pressed(self, game, button, mouse_pos):
		pass
	def key_pressed(self, game, key, mod, translated):
		if self.focused_index != None:
			self.ui_elements[self.focused_index].key_pressed(game=game, key=key, mod=mod, translated=translated)

class ShopState:
	def __init__(self):
		pass
	def draw(self, game):
		game.queue_surface(	surface=pointer_cursor_surface,
							pos=game.mouse_pos,
							depth=-1)
		game.queue_drawtext(color=c.light_red,
							text="Shop",
							font=main_font_10,
							pos=Vec(screen_width/2, 100),
							depth=0)
	def update(self, game):
		pass
	def key_pressed(self, game, key, mod, translated):
		pass
	def mouse_button_pressed(self, game, button):
		pass
	def enter(self):
		pass
	def exit(self):
		pass

class BattleState:
	def __init__(self):
		#self.turn = Turn(initial_active=True)
		self.is_player_turn = True
		self.active_subturn_slot = 0 # The slot which has the enemy currently doing its own subturn
		# action_state represents what action the play is currently doing (after clicking a card, it might be "targeting")
		self.action_state = "Action Select"
		self.target_start_pos = Vec(0,0)
		#self.selected_action = None
		self.selected_action_button = None

		self.friendlies = []
		self.enemies = []

		# Set up warrior and put in slot 0, usw.
		warrior_unit = game.unit_db.generate_unit(name="Warrior", team=0, slot=0)
		rogue_unit = game.unit_db.generate_unit(name="Rogue", team=0, slot=1)
		self.friendlies.append(warrior_unit)
		self.friendlies.append(rogue_unit)

		wolf_unit = game.unit_db.generate_unit(name="Wolf", team=1, slot=0)
		wolf2_unit = game.unit_db.generate_unit(name="Wolf", team=1, slot=1)
		human_unit = game.unit_db.generate_unit(name="Human", team=1, slot=2)
		human2_unit = game.unit_db.generate_unit(name="Human", team=1, slot=3)
		self.enemies.append(wolf_unit)
		self.enemies.append(wolf2_unit)
		self.enemies.append(human_unit)
		self.enemies.append(human2_unit)
	def enter(self):
		pass
	def exit(self):
		pass		
	def get_valid_targets(self, source_unit, target_set):
		if target_set == TargetSet.All:
			return self.friendlies+self.enemies
		elif target_set == TargetSet.Self:
			return [source_unit]
		elif target_set == TargetSet.OtherAlly:
			if source_unit.team == 0:
				return [u for u in self.friendlies if u != source_unit]
			elif source_unit.team == 1:
				return [u for u in self.enemies if u != source_unit]
		elif target_set == TargetSet.SingleAlly or target_set == TargetSet.AllAllies:
			if source_unit.team == 0:
				return self.friendlies
			elif source_unit.team == 1:
				return self.enemies
		elif target_set == TargetSet.SingleEnemy or target_set == TargetSet.AllEnemies:
			if source_unit.team == 0:
				return self.enemies
			elif source_unit.team == 1:
				return self.friendlies
	def end_turn(self):
		if self.is_player_turn:
			# Perform cleanup associated with ending PLAYER turn
			# and starting ENEMY turn
			self.is_player_turn = False
			self.active_subturn_slot = 0
			self.enemies[self.active_subturn_slot].start_random_action(allies=self.enemies, enemies=self.friendlies)
		else:
			# Perform cleanup associated with ending ENEMY turn
			# and starting player turn
			self.is_player_turn = True
			for f in self.friendlies:
				f.action_points = 1			
	def update(self, game):


		if self.is_player_turn:
			# End turn if player presses Q
			if game.input.pressed(key=pg.K_q):
				self.end_turn()
			# End turn if action points are at 0 for all allies
			if len([e for e in self.friendlies if e.action_points > 0]) == 0:
				self.end_turn()
			# Handle left mouse button press
			# 	* Select the hovered action if no action is selected
			# 	* Select the hovered target if an action has already been selected
			if game.input.pressed(button=0):
				if self.action_state == "Action Select":
					for friendly in self.friendlies:
						if friendly.action_points > 0:
							for button in friendly.action_buttons:
								if button.check_hover(mouse_pos=game.mouse_pos) == True:
									self.action_state = "Target Select"
									self.selected_action_button = button

				elif self.action_state == "Target Select":
					action = self.selected_action_button.linked_action
					owner = self.selected_action_button.linked_action.owner
					valid_targets = self.get_valid_targets(source_unit=owner, target_set=action.target_set)
					for target in [e for e in self.friendlies+self.enemies if e in valid_targets]:
						if target.alive is False:
							continue

						if slot_intersect(pos=game.mouse_pos, team=target.team, slot=target.slot):
							owner.start_action(action=action, targeted=target, valid_targets=valid_targets)

					self.action_state = "Action Select"

			# Handle right mouse button press
			#	* If an action has been selected, deselect it so another one can be selected.
			if game.input.pressed(button=2):
				if self.action_state == "Target Select":
					self.action_state = "Action Select"
		else: # (if it is NOT the player's turn)
			if self.enemies[self.active_subturn_slot].action_finished == True:
				self.active_subturn_slot += 1
				if self.active_subturn_slot > last_index(self.enemies):
					# All enemies have done their subturns, so it is now the player's turn
					self.end_turn()
				else:
					self.enemies[self.active_subturn_slot].start_random_action(allies=self.enemies, enemies=self.friendlies)



		#self.turn.update(friendlies=self.friendlies, enemies=self.enemies)
		for friendly in self.friendlies:
			friendly.update()
		for enemy in self.enemies:
			enemy.update()

		previewed_target_set = []
		if self.action_state == "Target Select":
			action = self.selected_action_button.linked_action

			if action.target_set == TargetSet.All:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies+self.enemies # All
						break
				if previewed_target_set == []: # If we found something in friendlies, we don't need to check enemies
					for enemy in self.enemies:
						if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
							previewed_target_set = self.friendlies+self.enemies # All
			elif action.target_set == TargetSet.AllEnemies:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
						previewed_target_set = self.enemies
						break
			elif action.target_set == TargetSet.AllAllies:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies
						break
			elif action.target_set == TargetSet.SingleEnemy:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
						previewed_target_set = [enemy]
						break
			elif action.target_set == TargetSet.SingleAlly:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = [friendly]
						break
			elif action.target_set == TargetSet.Self:
				if action.owner.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=action.owner.slot):
					previewed_target_set = [action.owner]

		# Draw friendlies
		for friendly in self.friendlies:
			if friendly in previewed_target_set and self.action_state == "Target Select":
				friendly.draw(target=game.screen, mouse_pos=game.mouse_pos, preview_action=action)
				highlight_surface = Surface(Vec(200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				game.queue_surface(	surface=highlight_surface,
									pos=Vec(friendly_slot_positions[friendly.slot], 0),
									depth=1000)
			else:
				back_surface = Surface(Vec(200,screen_height))
				back_surface.set_alpha(20)
				back_surface.fill(c.white)

				if self.is_player_turn == True:
					highlight_surface = Surface(Vec(200,screen_height))
					highlight_surface.set_alpha(30)
					if friendly.action_points == 0:
						highlight_surface.fill(c.red)
					else:
						highlight_surface.fill(c.green)

					game.queue_surface(	surface=highlight_surface,
										pos=Vec(friendly_slot_positions[friendly.slot], 0),
										depth=-1)

				if self.action_state == "Target Select":
					preview_action = self.selected_action_button.linked_action
				else:
					preview_action = None

				friendly.draw(target=game.screen, mouse_pos=game.mouse_pos, preview_action=preview_action)

		# Draw enemies
		for enemy in self.enemies:
			if enemy.alive == False:
				continue
			if enemy in previewed_target_set and self.action_state == "Target Select":
				enemy.draw(target=game.screen, mouse_pos=game.mouse_pos, preview_action=action)
				highlight_surface = Surface(Vec(200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				game.queue_surface(	surface=highlight_surface,
									pos=Vec(enemy_slot_positions[enemy.slot], 0),
									depth=-1)
			else:
				enemy.draw(target=game.screen, mouse_pos=game.mouse_pos)

		if self.action_state == "Target Select":
			# Targeting line/arrow
			# width = abs(game.mouse_pos.x - self.selected_action_button.rect.center_right.x)
			# height = abs(game.mouse_pos.y - self.selected_action_button.rect.center_right.y)
			surface = Surface(size=Vec(screen_width, screen_height))
			surface.set_colorkey(c.pink)
			surface.fill(c.pink)
			draw_line(	target=surface,
						color=c.white,
						start=self.selected_action_button.rect.center_right,
						end=game.mouse_pos)

			game.queue_surface(surface=surface, depth=-10, pos=Vec(0,0))				
	def draw(self, game):
		game.queue_surface(surface=pointer_cursor_surface, depth=-100, pos=game.mouse_pos)		
	def mouse_button_pressed(self, game, button, mouse_pos):
		pass		
	def key_pressed(self, game, key, mod, translated):
		pass		
	def get_allies(self, team):
		if team == 0:
			return self.friendlies
		if team == 1:
			return self.enemies
	def get_enemies(self, team):
		if team == 0:
			return self.enemies
		if team == 1:
			return self.friendlies	

class RoomType(Enum):
	Battle = 0
	Shop = 1

class Room:
	def __init__(self, room_type):
		self.room_type = room_type
	def enter(self):
		if self.room_type == RoomType.Battle:
			return BattleState()
		elif self.room_type == RoomType.Shop:
			return ShopState()

class CampaignState:
	def __init__(self):
		self.rooms = [Room(room_type=RoomType.Battle) for i in range(4)]
		self.rooms.append(Room(room_type=RoomType.Shop))
	def room_index_to_rect(self, i):
		return Rect(	pos=Vec(100+100*i,screen_height/2),
						size=Vec(50,50))

	def enter_room(self, index):
		return self.rooms[index].enter()
	def enter(self):
		pass
	def exit(self):
		pass
	def update(self, game):
		pass


	def draw(self, game):
		game.queue_surface(surface=pointer_cursor_surface, depth=-100, pos=game.mouse_pos)
		game.queue_drawtext(color=c.white,
							pos=Vec(50,50),
							text="Campaign",
							font=main_font_10,
							depth=0,
							x_center=False,
							y_center=False)
	
		for i, room in enumerate(self.rooms):
			room_rect = self.room_index_to_rect(i)
			if room_rect.intersect(point=game.mouse_pos):
				color = c.white
			else:
				color = c.ltgrey

			game.queue_drawrect(color=color,
								pos=room_rect.pos,
								size=room_rect.size,
								depth=5,
								width=-3)

			if room.room_type == RoomType.Battle:
				text = 'B'
			elif room.room_type == RoomType.Shop:
				text = 'S'

			game.queue_drawtext(color=color,
								text=text,
								pos=room_rect.center,
								font=main_font_7,
								depth=4)

		for i, r in enumerate(zip(self.rooms, self.rooms[1:])):
			start = self.room_index_to_rect(i).center_right
			end = 	self.room_index_to_rect(i+1).center_left
			game.queue_drawline(start=start,
								end=end,
								color=c.grey,
								depth=10,
								width=5)

	def mouse_button_pressed(self, game, button, mouse_pos):
		if button == 1: # Left mouse button
			for i, room in enumerate(self.rooms):
				room_rect = self.room_index_to_rect(i)

				if room_rect.intersect(point=mouse_pos):
					game.enter_state(room.enter())


	def key_pressed(self, game, key, mod, translated):
		pass

class Game:
	def __init__(self):
		global game
		game = self

		pg.init()
		self.screen = Surface.from_pgsurface(pg.display.set_mode((screen_width, screen_height)))
		pg.mouse.set_visible(False)		
		pg.key.set_repeat(250, 32)

		self.action_db = ActionSchematicDatabase(action_data_filepath="actions.dat")
		self.unit_db = UnitSchematicDatabase(unit_data="units.dat", animation_data="animations.dat")

		self.state_stack = []
		self.enter_state(MainMenuState())
		self.active_animations = []
		self.draw_queue = []
		self.game_clock = pg.time.Clock()
		self.input = InputState(	p_keys=None, keys=None,
									p_buttons=None, buttons=None,
									keypress_delay_interval=15, keypress_repeat_interval=2)

		# Activate debug mode if terminal line flag '-d' is given
		if len(sys.argv) >= 2 and sys.argv[1] == '-d':
			debug.debugger = debug.DebugUI(game=self, active=True)
		if len(sys.argv) >= 2 and sys.argv[1] == '-e':
			self.enter_state(EditorState())

	@property
	def active_state(self):
		return self.state_stack[-1]

	def enter_state(self, state):
		state.enter()
		self.state_stack.append(state)

	def exit_state(self):
		self.active_state.exit()
		self.state_stack = self.state_stack[:-1]

		# Clear all queue'd draw calls, otherwise there are
		# phantom animations that carry over between states.
		self.draw_queue = []
		self.active_animations = []
	
	def draw(self):
		# Clear screen
		self.screen.fill(c.dkgrey)

		self.active_state.draw(game=self)

		# Draw each animation in active_animation at its position
		for data in self.active_animations:
			data['animation'].draw(game=game, pos=data['pos'])

		# Sort drawing queue by depth
		self.draw_queue.sort(key=lambda x: x[0], reverse=True)

		# Draw each surface in draw_queue at its position
		for e in self.draw_queue:
			e[1]()
			# surface = e[1]
			# pos = e[2]
			# draw_surface(	target=self.screen,
			# 				surface=surface,
			# 				pos=pos)


		# Draw FPS text in top left corner
		draw_text(	target=self.screen, color=c.green,
					pos=Vec(4,4), text="{:.0f}".format(self.game_clock.get_fps()),
					font=main_font_5, x_center=False, y_center=False)

		# Flip buffer to display
		# If debugger is active, let it draw its stuff and then flip the display itself		
		if debug.debugger == None:
			pg.display.flip()

	def any_key_pressed(self, input_state):
		pass
	def update(self, df=1, mouse_pos=(0,0)): # TODO: mouse_pos, esp. with default arg, doesn't need to be here
		# Handle window events
		for event in pg.event.get():
			if event.type == pg.QUIT:
				sys.exit()
			elif event.type == pg.KEYDOWN:
				#self.input.set_repeat_key(event.key)
				self.active_state.key_pressed(game=self, key=event.key, mod=event.mod, translated=event.unicode)
			elif event.type == pg.KEYUP:
				self.input.unset_repeat_key(event.key)
			elif event.type == pg.MOUSEBUTTONDOWN:
				mouse_pos = Vec.fromtuple(event.pos)
				self.active_state.mouse_button_pressed(game=self, button=event.button, mouse_pos=mouse_pos)

		# Clear draw queue for this frame
		self.draw_queue = []		

		# Tick all animations in active_animations
		# If any animation finishes, notify its owner that it has (by setting animation_finished)
		# Remove all animations that finished from active_animations
		for data in self.active_animations:
			if(data['animation'].update() == True):
				data['owner'].animation_finished = True
		self.active_animations = [e for e in self.active_animations if e['animation'].finished == False]

		# Refresh input state
		self.input.next_state(new_keys=pg.key.get_pressed(), new_buttons=pg.mouse.get_pressed())
		self.input.update(df=1)
		self.any_key_pressed(input_state=self.input)
		mouse_x, mouse_y = pg.mouse.get_pos()
		self.mouse_pos = Vec(mouse_x, mouse_y)

		if self.input.pressed(key=pg.K_ESCAPE):
			self.exit_state()

		# Update our active state
		self.active_state.update(game=self)

		# Draw all our queue'd up surfaces and animations
		self.draw()

		# Tick and frame limit to 60
		self.game_clock.tick(60)
	def queue_drawline(self, start, end, color, depth, width=1):
		self.draw_queue.append( (depth,
								 lambda: draw_line(	target=self.screen,
								 					color=color,
								 					start=start,
								 					end=end,
								 					width=width)))
	def queue_drawrect(self, color, pos, size, depth, width=0):
		self.draw_queue.append( (depth,
								 lambda: draw_rect(	target=self.screen,
								 					color=color,
								 					pos=pos,
								 					size=size,
								 					width=width)))
	def queue_drawtext(self, color, pos, text, font, depth, x_center=True, y_center=True):
		self.draw_queue.append( (depth,
								 lambda: draw_text(	target=self.screen,
								 					color=color,
								 					pos=pos,
								 					text=text,
								 					font=font,
								 					x_center=x_center,
								 					y_center=y_center)))
	def queue_surface(self, surface, depth, pos):
		self.draw_queue.append(	(depth,
								 lambda: draw_surface(	target=self.screen,
														surface=surface,
														pos=pos)))
		#self.draw_queue.append((depth, surface, pos))
	def start_animation(self, animation, pos, owner):
		self.active_animations.append({ 'animation': deepcopy(animation),
										'pos': pos,
										'owner': owner})
	def start_battle(self):
		self.enter_state(BattleState())
	def start_campaign(self):
		self.enter_state(CampaignState())
	def start_editor(self):
		self.enter_state(EditorState())

def main():
	game = Game()
	while True:
		game.update(df=1, mouse_pos=(0,0))
main()