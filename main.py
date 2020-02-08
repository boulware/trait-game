import os, sys
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (100,30)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import math
import random
import json
from functools import partial
from enum import Enum
from copy import copy, deepcopy

import debug
from util import InputState
from harm_math import Vec, Rect
from harm_animation import Tween, FullAnimation
from harm_draw import Surface, draw_surface, darken_color, draw_line, draw_rect, draw_text, AlignX, AlignY, draw_x, draw_text_wrapped
import constants as c

random.seed()

import pygame as pg
screen_width, screen_height = 1400,800
game = None

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

# Trait enum:
# T.Vigor, T.Armor, T.Focus
class T(Enum):
	Vigor = 0
	Armor = 1
	Focus = 2

trait_count = 3
trait_colors = {T.Vigor: c.red, T.Armor:c.yellow, T.Focus: c.ltblue}
trait_strings = {T.Vigor: "Vigor", T.Armor: "Armor", T.Focus: "Focus"}

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

human_surface = Surface.from_file("Human.png")
human_highlighted_surface = Surface.from_file("Human.png")

wolf_enemy_surface = Surface.from_file("WolfEnemy.png")
wolf_enemy_highlighted_surface = Surface.from_file("WolfEnemyHighlighted.png")
wolf_enemy_howl_surface = Surface.from_file("WolfEnemyHowl.png")

vigor_damage_animation = FullAnimation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.width/2, vigor_symbol_surface.height/2)])
armor_damage_animation = FullAnimation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.width/2, armor_symbol_surface.height/2)])
focus_damage_animation = FullAnimation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.width/2, focus_symbol_surface.height/2)])

vigor_heal_animation = FullAnimation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.width/2, vigor_symbol_surface.height/2)])
armor_heal_animation = FullAnimation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.width/2, armor_symbol_surface.height/2)])
focus_heal_animation = FullAnimation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.width/2, focus_symbol_surface.height/2)])


healthbar_width = 100
healthbar_height = 32
def draw_healthbar(target, color, pos, value, max_value, preview_damage=0):
	bar_values_x_padding = 4

	prev = Rect(Vec(0,0), Vec(0,0))
	if color == c.red:
		prev = draw_surface(target=target, pos=pos, surface=vigor_symbol_surface)
	elif color == c.ltblue:
		prev = draw_surface(target=target, pos=pos, surface=focus_symbol_surface)
	elif color == c.yellow:
		prev = draw_surface(target=target, pos=pos, surface=armor_symbol_surface)

	if value > 0:
		# Draw colored part of bar, capped at size of healthbar (extra points won't draw it past the bar)
		max_value = max(1, max_value)
		colored_bar_width = min(healthbar_width, healthbar_width * (value/max_value))
		if preview_damage >= value:
			# Preview damage will cover the entire normal bar, so skip drawing it and just draw the preview bar
			draw_rect(target, darken_color(color,0.5), prev.top_right, Vec(colored_bar_width, healthbar_height))
		else:
			draw_rect(target, color, prev.top_right, Vec(colored_bar_width, healthbar_height))

			if preview_damage != 0 and value <= max_value: # TODO: This is glitchy when value > max_value, so we just don't draw anything for now
				# Draw darker colored previewed damage section of bar.
				preview_bar_start = prev.top_right + Vec(healthbar_width * ((value-preview_damage)/max_value), 0)
				preview_bar_size = Vec(healthbar_width * (preview_damage/max_value), healthbar_height)
				draw_rect(target, darken_color(color, 0.5), preview_bar_start, preview_bar_size)

	# Draw white outline of bar
	prev = draw_rect(target, c.white, prev.top_right, Vec(healthbar_width, healthbar_height), 1)

	amount_text_color = c.white
	if preview_damage != 0:
		# Draw the amount color darker if it will change due to damage preview
		amount_text_color = darken_color(c.white, 0.5)
	# Draw trait value text next to bar
	draw_text(	target=target,
				color=amount_text_color,
				font=main_font_5,
				pos=Vec(prev.right + bar_values_x_padding, prev.top + healthbar_height/2),
				text="{}".format(max(0, value-preview_damage)), x_center=False)

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



class UnitSchematic:
	def __init__(self, name, traits, idle_animation, hover_idle_animation):
		self.name = name
		self.max_traits = copy(traits)
		self.idle_animation = copy(idle_animation)
		self.hover_idle_animation = copy(hover_idle_animation)

		self.actions = []
		self.action_animations = [] # Concurrent array to self.actions
	def add_action(self, action):
		self.actions.append(deepcopy(action)) # TODO: is deepcopy(action) necessary?
		self.action_animations.append(self.idle_animation)
	def set_animation(self, action_index, animation):
		if action_index > len(self.action_animations)-1:
			print("Tried to set enemy animation for non-existent action.")
			return

		self.action_animations[action_index] = animation

	def serialize(self):
		s = ""
		s += "name is {}\n".format(self.name)
		for trait, value in self.max_traits.items():
			if value == 0: continue
			s += "\thas {} {}\n".format(value, trait_strings[trait])
		for action in self.actions:
			s += "\thas action {}\n".format(action.name)
			s += "\t\ttargets {}\n".format(target_set_strings[action.target_set])
			for trait, value in action.damages.items():
				if value == 0: continue
				s += "\t\tdeals {} {} damage\n".format(value, trait_strings[trait])
			for trait, value in action.required.items():
				if value == 0: continue
				s += "\t\trequires {} {}\n".format(value, trait_strings[trait])

		return s



class Unit:
	def __init__(self, team, slot, schematic):
		self.team = team
		self.slot = slot
		self.max_traits = copy(schematic.max_traits)
		self.cur_traits = copy(schematic.max_values)
		self.idle_animation = deepcopy(schematic.idle_animation)
		self.hover_idle_animation = deepcopy(schematic.hover_idle_animation)
		self.actions = deepcopy(schematic.actions)
		self.action_animations = deepcopy(schematic.action_animations) # Concurrent array to self.actions

		for action in self.actions:
			action.owner = self		
		self.action_buttons = [ActionButton(pos=Vec(x=enemy_slot_positions[self.slot],
														y=enemy_ui_paddings[3] + i*action_button_size.y),
												linked_action=action) for i, action in enumerate(self.actions)]
		
		self.action_points = 1
		self.current_action_index = None
		self.current_action_targets = None
	@property
	def current_animation(self):
		if self.current_action_index is None:
			return self.idle_animation
		else:
			return self.action_animations[self.current_action_index]
	@property
	def action_finished(self):
		if self.current_animation.finished:
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
	def start_action(self, action_index, targets):
		if self.alive:
			self.current_action_index = action_index
			self.current_action_targets = targets
	def start_random_action(self, allies, enemies):
		if self.alive:
			possible_actions_indices = [] # Actions which have their pre-reqs fulfilled
			# Check each of our actions, and add them to the list of possible random actions
			for i,action in enumerate(self.actions):
				if action.can_use(user_traits=self.cur_values):

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
					print('t')
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

			self.actions[self.current_action_index].execute(user_traits=self.cur_values,
													kwargs={	'source': self,
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
			x_pos = enemy_slot_positions[self.slot]

			y_offset = 0
			prev = Rect(Vec(0,0),Vec(0,0))
			for trait, max_value in self.max_values.items():
				cur_trait = self.cur_values[trait]
				preview_damage = 0
				if preview_action is not None:
					if trait == T.Vigor and preview_action.damages[T.Vigor] > 0:
						# Account for armor in preview damage
						armor = self.cur_values[T.Armor]
						preview_damage = max(1, preview_action.damages[trait] - armor)
					else:
						preview_damage = preview_action.damages[trait]

				# Draws trait bars
				draw_healthbar(	target, trait_colors[trait],
								Vec(x_pos, enemy_ui_paddings[1] + y_offset),
								cur_trait, max_value, preview_damage)

				y_offset += healthbar_height

			# Draws enemy sprite
			sprite_surface = wolf_enemy_surface
			if hover:
				self.current_animation.draw(target=target,
											pos=Vec(x_pos, enemy_ui_paddings[2]))
			else:
				self.current_animation.draw(target=target,
											pos=Vec(x_pos, enemy_ui_paddings[2]))

			# Draws action buttons
			for button in self.action_buttons:
				if button.linked_action == self.current_action:
					force_highlight = True
				else:
					force_highlight = False

				button.draw(target=target, mouse_pos=mouse_pos, force_highlight=force_highlight)

			# for i, action in enumerate(self.actions):
			# 	# TODO: Don't make a new action button every frame.
			# 	button = ActionButton(pos=Vec(x_pos, enemy_ui_paddings[3] + i*action_button_size.y), linked_action=action)
			# 	if i == self.current_action_index:
			# 		button.draw(target=screen, hover=True)
			# 	else:
			# 		button.draw(target=screen, hover=False)
	@property
	def alive(self):
		if self.cur_values[T.Vigor] > 0:
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

# class Friendly:
# 	def __init__(self, slot, traits, idle_animation, hover_idle_animation):
# 		self.max_values = copy(traits)
# 		self.cur_values = copy(self.max_values)
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
# 							traits=self.max_values,
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
# 			print("Tried to set friendly animation for non-existent action.")
# 			return

# 		self.action_animations[action_index] = animation
# 	@property
# 	def rect(self):
# 		rect = self.current_animation.rect
# 		rect.pos += get_sprite_slot_pos(slot=self.slot, team=self.team)
# 		return rect
# 	@property
# 	def alive(self):
# 		if self.cur_values[T.Vigor] > 0:
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
# 			for trait, max_value in self.max_values.items():
# 				cur_trait = self.cur_values[trait]
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
				armor = target.cur_values[T.Armor]
				if amount > 0:
					target.cur_values[trait] -= max(1, amount - armor)
				else:
					target.cur_values[trait] -= amount

				if amount > 0:
					game.start_animation(animation=vigor_damage_animation, pos=icon_pos)
				else:
					game.start_animation(animation=vigor_heal_animation, pos=icon_pos)						
			elif trait == T.Armor and amount != 0:
				target.cur_values[trait] -= amount
				if amount > 0:
					game.start_animation(animation=armor_damage_animation, pos=icon_pos)
				else:
					game.start_animation(animation=armor_heal_animation, pos=icon_pos)						
			elif trait == T.Focus and amount != 0:
				target.cur_values[trait] -= amount
				if amount > 0:
					game.start_animation(animation=focus_damage_animation, pos=icon_pos)
				else:
					game.start_animation(animation=focus_heal_animation, pos=icon_pos)
			if target.cur_values[trait] < 0:
				target.cur_values[trait] = 0
				

class TargetSet(Enum):
	All = 0
	Self = 1
	SingleAlly = 2
	OtherAlly = 3
	AllAllies = 4
	SingleEnemy = 5
	AllEnemies = 6

target_set_strings = {	TargetSet.All: "All",
						TargetSet.Self: "Self",
						TargetSet.SingleAlly: "Single Ally",
						TargetSet.OtherAlly: "Other Ally",
						TargetSet.SingleEnemy: "Single Enemy",
						TargetSet.AllEnemies: "All Enemies",
						TargetSet.AllAllies: "All Allies"}

class Action:
	def __init__(self, name, owner, target_set, required, damages, description=""):
		self.sub_actions = []
		self.name = name
		self.description = description
		self.owner = owner
		self.target_set = target_set
		self.required = required
		self.damages = damages
	def add_sub_action(self, sub_action):
		self.sub_actions.append(sub_action)
	def can_use(self, user_traits):
		valid_target = False

		if self.target_set == TargetSet.OtherAlly:
			for ally in game.state.get_allies(team=self.owner.team):
				if ally.alive == True and ally != self.owner:
					valid_target = True
		else:
			valid_target = True

		if valid_target == False:
			return False
		for trait, value in user_traits.items():
			if value < self.required[trait]:
				return False
		return True		
	def execute(self, user_traits, kwargs={}):
		if self.can_use(user_traits=user_traits) == True:
			for sub_action in self.sub_actions:
				sub_action(**kwargs)
			return True
		else:
			return False

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
				# if(self.linked_action.owner.cur_values[trait] < required):
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
				# if(self.linked_action.owner.cur_values[trait] < required):
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
	def draw(self, target, mouse_pos, force_highlight=False):
		if self.linked_action.can_use(user_traits=self.owner.cur_values) == False:
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

class BattleState:
	def __init__(self):
		self.turn = Turn(initial_active=True)
		# action_state represents what action the play is currently doing (after clicking a card, it might be "targeting")
		self.action_state = "Action Select"
		self.target_start_pos = Vec(0,0)
		#self.selected_action = None
		self.selected_action_button = None

		self.friendlies = []
		self.enemies = []

		# Set up warrior and put in slot 0
		warrior_schematic = UnitSchematic(	name="Warrior",
											traits={T.Vigor:50, T.Armor:10, T.Focus:5},
											idle_animation=FullAnimation(	sprites=[character_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,character_surface.height)]),
											hover_idle_animation=FullAnimation(	sprites=[character_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,character_highlighted_surface.height)])
							)

		rest_action = Action(	name="Rest",
								description="Restores 2 vigor to self.",				
								owner=None,
								target_set=TargetSet.Self,
								required={T.Vigor:0, T.Focus:0, T.Armor:0}, 
								damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
		rest_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': rest_action.damages}))

		# Strike
		med_strike_action = Action(	name="Medium Strike",
									description="Deals 5 vigor damage to target. Requires 2 vigor.",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:2, T.Focus:0, T.Armor:0},
									damages={T.Vigor:5, T.Focus:0, T.Armor:0})
		med_strike_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																						'targets': targets, 
																						'damages': med_strike_action.damages}))

		# Intimidate
		intimidate_action = Action(	name="Intimidate",
									description="Deals 5 focus damage to target. Requires 1 focus.",				
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:0, T.Focus:5, T.Armor:0})
		intimidate_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																						'targets': targets, 
																						'damages': intimidate_action.damages}))

		# Bash
		med_bash_action = Action(	name="Medium Bash",
									description="Deals 4 armor damage to target. Requires 1 focus.",				
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:0, T.Focus:0, T.Armor:4})
		med_bash_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																					'targets': targets, 
																					'damages': med_bash_action.damages}))

		warrior_schematic.add_action(rest_action)
		warrior_schematic.add_action(med_strike_action)
		warrior_schematic.add_action(intimidate_action)
		warrior_schematic.add_action(med_bash_action)

		rest_animation_length = 60
		rest_sprite_animation = FullAnimation(	#end_pos=Vec(0,30),
												#jerk=1.0,
												#tweens=[Tween(end_pos=Vec(0,30), jerk=1.0, duration=rest_animation_length)]
												duration=rest_animation_length,
												sprites=[character_highlighted_surface],
												sprite_lengths=[rest_animation_length],
												anchor_points=[Vec(0, character_highlighted_surface.height)])
		warrior_schematic.set_animation(	action_index=0,
											animation=rest_sprite_animation)

		med_strike_animation_length = 60
		med_strike_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
												#jerk=5.0,
												duration=med_strike_animation_length,
												sprites=[character_surface],
												sprite_lengths=[med_strike_animation_length],
												anchor_points=[Vec(0, character_surface.height)])
		warrior_schematic.set_animation(	action_index=1,
											animation=med_strike_sprite_animation)

		intimidate_animation_length = 60
		intimidate_sprite_animation = FullAnimation(#end_pos=Vec(-20,0),
													#jerk=0.7,
													duration=intimidate_animation_length,
													sprites=[character_surface],
													sprite_lengths=[intimidate_animation_length],
													anchor_points=[Vec(0, character_surface.height)])
		warrior_schematic.set_animation(	action_index=2,
											animation=intimidate_sprite_animation)

		bash_animation_length = 60
		bash_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
											#		jerk=0.5,												
													duration=bash_animation_length,
													sprites=[character_surface],
													sprite_lengths=[bash_animation_length],
													anchor_points=[Vec(0, character_surface.height)])
		warrior_schematic.set_animation(	action_index=3,
											animation=bash_sprite_animation)

		with open("warrior_test.dat", "w") as f:
			f.write(warrior_schematic.serialize())


		# self.friendlies.append(
		# self.friendlies.append(Friendly(slot=1,
		# 								traits={T.Vigor:35, T.Armor:5, T.Focus:8},
		# 								idle_animation=FullAnimation(	sprites=[character_surface],
		# 																sprite_lengths=[1],
		# 																anchor_points=[Vec(0,character_surface.height)]),
		# 								hover_idle_animation=FullAnimation(	sprites=[character_highlighted_surface],
		# 																	sprite_lengths=[1],
		# 																	anchor_points=[Vec(0,character_highlighted_surface.height)])
		# 								)		
		# 							)


		# Slot 0 friendly skills/animations
		# for friendly in [self.friendlies[0]]:
			# Res

		# Slot 1 Friendly skills/animations
		for friendly in [self.friendlies[1]]:
			# Rest
			rest_action = Action(	name="Rest",
									description="Restores 2 vigor to self.",				
									owner=None,
									target_set=TargetSet.Self,
									required={T.Vigor:0, T.Focus:0, T.Armor:0}, 
									damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
			rest_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																					'targets': targets, 
																					'damages': rest_action.damages}))

			# Strike
			light_strike_action = Action(	name="Light Strike",
									description="Deals 2 vigor damage to target. Requires 5 vigor.",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:5, T.Focus:0, T.Armor:0},
									damages={T.Vigor:2, T.Focus:0, T.Armor:0})
			light_strike_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																						'targets': targets, 
																						'damages': light_strike_action.damages}))

			# Intimidate
			intimidate_action = Action(	name="Intimidate",
										description="Deals 5 focus damage to target. Requires 1 focus.",				
										owner=None,
										target_set=TargetSet.SingleEnemy,
										required={T.Vigor:0, T.Focus:1, T.Armor:0},
										damages={T.Vigor:0, T.Focus:5, T.Armor:0})
			intimidate_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																							'targets': targets, 
																							'damages': intimidate_action.damages}))

			# Bash
			light_bash_action = Action(	name="Light Bash",
									description="Deals 2 armor damage to target. Requires 1 focus.",				
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:0, T.Focus:0, T.Armor:2})
			light_bash_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																					'targets': targets, 
																					'damages': light_bash_action.damages}))

			friendly.add_action(rest_action)
			friendly.add_action(light_strike_action)
			friendly.add_action(intimidate_action)
			friendly.add_action(light_bash_action)

			rest_animation_length = 60
			rest_sprite_animation = FullAnimation(	#end_pos=Vec(0,30),
													#jerk=1.0,
													#tweens=[Tween(end_pos=Vec(0,30), jerk=1.0, duration=rest_animation_length)]
													duration=rest_animation_length,
													sprites=[character_highlighted_surface],
													sprite_lengths=[rest_animation_length],
													anchor_points=[Vec(0, character_highlighted_surface.height)])
			friendly.set_animation(	action_index=0,
									animation=rest_sprite_animation)

			light_strike_animation_length = 60
			light_strike_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
													#jerk=5.0,
													duration=light_strike_animation_length,
													sprites=[character_surface],
													sprite_lengths=[light_strike_animation_length],
													anchor_points=[Vec(0, character_surface.height)])
			friendly.set_animation(	action_index=1,
									animation=light_strike_sprite_animation)

			intimidate_animation_length = 60
			intimidate_sprite_animation = FullAnimation(#end_pos=Vec(-20,0),
														#jerk=0.7,
														duration=intimidate_animation_length,
														sprites=[character_surface],
														sprite_lengths=[intimidate_animation_length],
														anchor_points=[Vec(0, character_surface.height)])
			friendly.set_animation(	action_index=2,
									animation=intimidate_sprite_animation)

			light_bash_animation_length = 60
			light_bash_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
												#		jerk=0.5,												
														duration=light_bash_animation_length,
														sprites=[character_surface],
														sprite_lengths=[light_bash_animation_length],
														anchor_points=[Vec(0, character_surface.height)])
			friendly.set_animation(	action_index=3,
									animation=light_bash_sprite_animation)		


		# START: Wolf schematic
		wolf_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:0, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[wolf_enemy_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,wolf_enemy_surface.height)]),
											hover_idle_animation=FullAnimation(	sprites=[wolf_enemy_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,wolf_enemy_highlighted_surface.height)])
											)
		# Bite
		bite_action = Action(	name="Bite",
								description="Deals 4 vigor damage to target. Requires 4 focus.",			
								owner=None,
								target_set=TargetSet.SingleEnemy,
								required={T.Vigor:0, T.Focus:4, T.Armor:0},
								damages={T.Vigor:4, T.Focus:0, T.Armor:0})
		bite_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': bite_action.damages}))

		# Howl
		howl_action = Action(	name="Howl",
								owner=None,
								target_set=TargetSet.AllAllies,
								required={T.Vigor:0, T.Focus:0, T.Armor:0},
								damages={T.Vigor:0, T.Focus:-1, T.Armor:0})
		howl_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': howl_action.damages}))

		wolf_schematic.add_action(bite_action)
		wolf_schematic.add_action(howl_action)

		bite_animation_length = 60
		bite_sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.2, duration=rest_animation_length)],
												duration=bite_animation_length,
												sprites=[wolf_enemy_surface],
												sprite_lengths=[bite_animation_length],
												anchor_points=[Vec(0, wolf_enemy_surface.height)])
		wolf_schematic.set_animation(	action_index=0,
										animation=bite_sprite_animation)

		howl_animation_length = 60
		howl_sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(20,0), jerk=0.5, duration=rest_animation_length)],
												duration=howl_animation_length,
												sprites=[wolf_enemy_howl_surface],
												sprite_lengths=[howl_animation_length],
												anchor_points=[Vec(0, wolf_enemy_howl_surface.height)])
		wolf_schematic.set_animation(	action_index=1,
										animation=howl_sprite_animation)
		# END: Wolf schematic

		# START: Human schematic
		human_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:10, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[human_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,human_surface.height)]),
											hover_idle_animation=FullAnimation(	sprites=[human_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,human_highlighted_surface.height)])
											)
		# Heal
		heal_action = Action(	name="Heal",
								owner=None,
								target_set=TargetSet.AllAllies,
								required={T.Vigor:0, T.Focus:2, T.Armor:0},
								damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
		heal_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': heal_action.damages}))

		# Armor
		armor_action = Action(	name="Rig Up",
								owner=None,
								target_set=TargetSet.OtherAlly,
								required={T.Vigor:0, T.Focus:0, T.Armor:1},
								damages={T.Vigor:0, T.Focus:0, T.Armor:-1})
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': targets, 
																				'damages': armor_action.damages}))
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': TargetSet.Self, 
																				'damages': {T.Vigor:0, T.Armor:1, T.Focus:0}}))

		# Attack
		attack_action = Action(	name="Attack",
								owner=None,
								target_set=TargetSet.SingleEnemy,
								required={T.Vigor:0, T.Focus:2, T.Armor:0},
								damages={T.Vigor:3, T.Focus:0, T.Armor:0})
		attack_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': targets, 
																				'damages': attack_action.damages}))		

		human_schematic.add_action(attack_action)
		human_schematic.add_action(heal_action)
		human_schematic.add_action(armor_action)

		# Heal Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(30,0), jerk=0.2, duration=animation_length)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=1,
										animation=sprite_animation)

		# Armor Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.1, duration=30),
													Tween(start_pos=Vec(-100,0), end_pos=Vec(0,0), jerk=0.4, duration=30)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=2,
										animation=sprite_animation)

		# Attack Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.2, duration=55),
													Tween(start_pos=Vec(-100,0), end_pos=Vec(0,0), jerk=1.0, duration=5)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=0,
										animation=sprite_animation)			
		# END: Human schematic

		self.enemies.append(Enemy(slot=0, schematic=wolf_schematic))
		self.enemies.append(Enemy(slot=1, schematic=wolf_schematic))
		self.enemies.append(Enemy(slot=2, schematic=human_schematic))
		self.enemies.append(Enemy(slot=3, schematic=human_schematic))		
	def update(self, mouse_pos):
		if self.turn.player_active:
			if game.input.pressed(key=pg.K_q):
				self.turn.end_turn(friendlies=self.friendlies, enemies=self.enemies)
			if game.input.pressed(button=0): # Left mouse pressed
				if self.action_state == "Action Select":
					for friendly in self.friendlies:
						if friendly.action_points > 0:
							for button in friendly.action_buttons:
								if button.check_hover(mouse_pos=mouse_pos) == True:
									self.action_state = "Target Select"
									self.selected_action_button = button

				elif self.action_state == "Target Select":
					for friendly in self.friendlies:
						if friendly.alive is False:
							continue
						if friendly_slot_intersect(pos=Vec(mouse_pos.x, mouse_pos.y), slot=friendly.slot):
							action = self.selected_action_button.linked_action
							owner = self.selected_action_button.linked_action.owner
							if action.target_set is TargetSet.All:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': self.friendlies+self.enemies})
								owner.action_points -= 1
							elif action.target_set is TargetSet.SingleAlly:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': [friendly]})
								owner.action_points -= 1
							elif action.target_set == TargetSet.Self and friendly == owner:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': [owner]})
								owner.action_points -= 1
							elif action.target_set is TargetSet.AllAllies:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': self.friendlies})
								owner.action_points -= 1
					for enemy in self.enemies:
						if enemy.alive is False:
							continue
						if enemy_slot_intersect(pos=Vec(mouse_pos.x, mouse_pos.y), slot=enemy.slot):
							action = self.selected_action_button.linked_action
							owner = self.selected_action_button.linked_action.owner
							if action.target_set is TargetSet.All:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': self.friendlies+self.enemies})
								owner.action_points -= 1								
							elif action.target_set is TargetSet.SingleEnemy:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': [enemy]})
								owner.action_points -= 1
							elif action.target_set is TargetSet.AllEnemies:
								action.execute(user_traits=owner.cur_values, kwargs={	'source': owner,
																						'targets': self.enemies})
								owner.action_points -= 1


							#self.turn.end_turn(friendlies=self.friendlies, enemies=self.enemies)

					self.action_state = "Action Select"

			if game.input.pressed(button=2): # Right mouse pressed
				if self.action_state == "Target Select":
					self.action_state = "Action Select"		

		self.turn.update(friendlies=self.friendlies, enemies=self.enemies)
		for enemy in self.enemies:
			enemy.update()

		previewed_target_set = []
		if self.action_state == "Target Select":
			action = self.selected_action_button.linked_action

			if action.target_set == TargetSet.All:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies+self.enemies # All
						break
				if previewed_target_set == []: # If we found something in friendlies, we don't need to check enemies
					for enemy in self.enemies:
						if enemy.alive == True and enemy_slot_intersect(pos=mouse_pos, slot=enemy.slot):
							previewed_target_set = self.friendlies+self.enemies # All
			elif action.target_set == TargetSet.AllEnemies:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=mouse_pos, slot=enemy.slot):
						previewed_target_set = self.enemies
						break
			elif action.target_set == TargetSet.AllAllies:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies
						break
			elif action.target_set == TargetSet.SingleEnemy:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=mouse_pos, slot=enemy.slot):
						previewed_target_set = [enemy]
						break
			elif action.target_set == TargetSet.SingleAlly:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=mouse_pos, slot=friendly.slot):
						previewed_target_set = [friendly]
						break
			elif action.target_set == TargetSet.Self:
				if action.owner.alive == True and friendly_slot_intersect(pos=mouse_pos, slot=action.owner.slot):
					previewed_target_set = [action.owner]

		# End turn if action points are at 0 for all allies
		if self.turn.player_active == True:
			if len([e for e in self.friendlies if e.action_points > 0]) == 0:
				self.turn.end_turn(friendlies=self.friendlies, enemies=self.enemies)			

		# Draw friendlies
		for friendly in self.friendlies:
			if friendly in previewed_target_set and self.action_state == "Target Select":
				friendly.draw(target=game.screen, mouse_pos=mouse_pos, preview_action=action)
				highlight_surface = Surface(Vec(200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				draw_surface(	target=game.screen,
								surface=highlight_surface,
								pos=Vec(friendly_slot_positions[friendly.slot], 0))
			else:
				back_surface = Surface(Vec(200,screen_height))
				back_surface.set_alpha(20)
				back_surface.fill(c.white)

				if self.turn.player_active == True:
					highlight_surface = Surface(Vec(200,screen_height))
					highlight_surface.set_alpha(30)
					if friendly.action_points == 0:
						highlight_surface.fill(c.red)
					else:
						highlight_surface.fill(c.green)

					draw_surface(	target=game.screen,
									surface=highlight_surface,
									pos=Vec(friendly_slot_positions[friendly.slot], 0))
				friendly.draw(target=game.screen, mouse_pos=mouse_pos)

		# Draw enemies
		for enemy in self.enemies:
			if enemy.alive == False:
				continue
			if enemy in previewed_target_set and self.action_state == "Target Select":
				enemy.draw(target=game.screen, mouse_pos=mouse_pos, preview_action=action)
				highlight_surface = Surface(Vec(200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				draw_surface(	target=game.screen,
								surface=highlight_surface,
								pos=Vec(enemy_slot_positions[enemy.slot], 0))
			else:
				enemy.draw(target=game.screen, mouse_pos=mouse_pos)

		if self.action_state == "Target Select":
			# Targeting line/arrow
			# width = abs(mouse_pos.x - self.selected_action_button.rect.center_right.x)
			# height = abs(mouse_pos.y - self.selected_action_button.rect.center_right.y)
			surface = Surface(size=Vec(screen_width, screen_height))
			surface.set_colorkey(c.pink)
			surface.fill(c.pink)
			draw_line(	target=surface,
						color=c.white,
						start=self.selected_action_button.rect.center_right,
						end=mouse_pos)

			game.queue_surface(surface=surface, depth=5, pos=Vec(0,0))				
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

class Game:
	def __init__(self):
		pg.init()
		self.screen = Surface.from_pgsurface(pg.display.set_mode((screen_width, screen_height)))

		self.state = BattleState()
		self.active_animations = []
		self.draw_queue = []
		self.game_clock = pg.time.Clock()
		self.input = InputState(	p_keys=None, keys=None,
									p_buttons=None, buttons=None,
									keypress_delay_interval=15, keypress_repeat_interval=3)

		# Activate debug mode if terminal line flag '-d' is given
		if len(sys.argv) >= 2 and sys.argv[1] == '-d':
			debug.debugger = debug.DebugUI(game=self, active=True)
	def draw(self):
		# Clear screen
		self.screen.fill(c.dkgrey)

		# Sort drawing queue by depth
		self.draw_queue.sort(key=lambda x: x[0], reverse=True)

		# Draw each surface in draw_queue at its position
		for e in self.draw_queue:
			surface = e[1]
			pos = e[2]
			draw_surface(	target=self.screen,
							surface=surface,
							pos=pos)

		# Draw each animation in active_animation at its position
		for data in self.active_animations:
			data['animation'].draw(target=self.screen, pos=data['pos'])

		# Draw FPS text in top left corner
		draw_text(	target=self.screen, color=c.green,
					pos=Vec(4,4), text="{:.2f}".format(self.game_clock.get_fps()),
					font=main_font_5, x_center=False, y_center=False)

		# Flip buffer to display
		pg.display.flip()
	def any_key_pressed(self, input_state):
		pass
	def update(self, df=1, mouse_pos=(0,0)): # TODO: mouse_pos, esp. with default arg, doesn't need to be here
		# Handle window events
		for event in pg.event.get():
			if event.type == pg.QUIT:
				sys.exit()
			elif event.type == pg.KEYDOWN:
				self.input.set_repeat_key(event.key)
			elif event.type == pg.KEYUP:
				self.input.unset_repeat_key(event.key)

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
		mouse_pos = Vec(mouse_x, mouse_y)

		# Update our active state
		self.state.update(mouse_pos=mouse_pos)

		# Draw all our queue'd up surfaces and animations
		self.draw()

		# Tick and frame limit to 60
		self.game_clock.tick(60)		
	def queue_surface(self, surface, depth, pos):
		self.draw_queue.append((depth, surface, pos))
	def start_animation(self, animation, pos, owner):
		self.active_animations.append({ 'animation': deepcopy(animation),
										'pos': pos,
										'owner': owner})

def main():
	global game
	game = Game()
	while True:
		game.update(df=1, mouse_pos=(0,0))
main()