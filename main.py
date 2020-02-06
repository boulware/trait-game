import os, sys
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (100,30)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import math
import random
from functools import partial
from enum import Enum
from copy import copy, deepcopy

import debug
from util import InputState
from harm_math import Vec, Rect
from harm_animation import Tween, FullAnimation
from harm_draw import draw_surface, darken_color, draw_line, draw_rect, draw_text, AlignX, AlignY, draw_x
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

sword_surfaces = {	T.Vigor: pg.image.load("RedSword.png"),
					T.Armor: pg.image.load("YellowSword.png"),
					T.Focus: pg.image.load("BlueSword.png")}
# red_sword_surface = pg.image.load("RedSword.png")
# blue_sword_surface = pg.image.load("BlueSword.png")
# yellow_sword_surface = pg.image.load("YellowSword.png")
focus_symbol_surface = pg.image.load("ConcentrationSymbol.png")
armor_symbol_surface = pg.image.load("ArmorSymbol.png")
vigor_symbol_surface = pg.image.load("VigorSymbol.png")

require_surfaces = {T.Vigor: pg.image.load("RedRequire.png"),
					T.Armor: pg.image.load("YellowRequire.png"),
					T.Focus: pg.image.load("BlueRequire.png")}

character_surface = pg.image.load("Character.png")
character_highlighted_surface = pg.image.load("CharacterHighlighted.png")

human_surface = pg.image.load("Human.png")
human_highlighted_surface = pg.image.load("Human.png")

wolf_enemy_surface = pg.image.load("WolfEnemy.png")
wolf_enemy_highlighted_surface = pg.image.load("WolfEnemyHighlighted.png")
wolf_enemy_howl_surface = pg.image.load("WolfEnemyHowl.png")

vigor_damage_animation = FullAnimation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.get_width()/2, vigor_symbol_surface.get_height()/2)])
armor_damage_animation = FullAnimation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.get_width()/2, armor_symbol_surface.get_height()/2)])
focus_damage_animation = FullAnimation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,0),
														end_pos=Vec(0,50),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.get_width()/2, focus_symbol_surface.get_height()/2)])

vigor_heal_animation = FullAnimation(	duration=60,
										sprites=[vigor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(vigor_symbol_surface.get_width()/2, vigor_symbol_surface.get_height()/2)])
armor_heal_animation = FullAnimation(	duration=60,
										sprites=[armor_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(armor_symbol_surface.get_width()/2, armor_symbol_surface.get_height()/2)])
focus_heal_animation = FullAnimation(	duration=60,
										sprites=[focus_symbol_surface],
										sprite_lengths=[60],
										tweens=[Tween(	start_pos=Vec(0,50),
														end_pos=Vec(0,0),
														duration=60)],
										anchor_points=[Vec(focus_symbol_surface.get_width()/2, focus_symbol_surface.get_height()/2)])


healthbar_width = 100
healthbar_height = 32
def draw_healthbar(screen, color, pos, value, max_value, preview_damage=0):
	bar_values_x_padding = 4

	prev = Rect(Vec(0,0), Vec(0,0))
	if color == c.red:
		prev = draw_surface(screen, pos, vigor_symbol_surface)
	elif color == c.ltblue:
		prev = draw_surface(screen, pos, focus_symbol_surface)
	elif color == c.yellow:
		prev = draw_surface(screen, pos, armor_symbol_surface)

	if value > 0:
		# Draw colored part of bar, capped at size of healthbar (extra points won't draw it past the bar)
		max_value = max(1, max_value)
		colored_bar_width = min(healthbar_width, healthbar_width * (value/max_value))
		if preview_damage >= value:
			# Preview damage will cover the entire normal bar, so skip drawing it and just draw the preview bar
			draw_rect(screen, darken_color(color,0.5), prev.top_right, Vec(colored_bar_width, healthbar_height))
		else:
			draw_rect(screen, color, prev.top_right, Vec(colored_bar_width, healthbar_height))

			if preview_damage != 0 and value <= max_value: # TODO: This is glitchy when value > max_value, so we just don't draw anything for now
				# Draw darker colored previewed damage section of bar.
				preview_bar_start = prev.top_right + Vec(healthbar_width * ((value-preview_damage)/max_value), 0)
				preview_bar_size = Vec(healthbar_width * (preview_damage/max_value), healthbar_height)
				draw_rect(screen, darken_color(color, 0.5), preview_bar_start, preview_bar_size)

	# Draw white outline of bar
	prev = draw_rect(screen, c.white, prev.top_right, Vec(healthbar_width, healthbar_height), 1)

	amount_text_color = c.white
	if preview_damage != 0:
		# Draw the amount color darker if it will change due to damage preview
		amount_text_color = darken_color(c.white, 0.5)
	# Draw trait value text next to bar
	draw_text(	screen=screen,
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



class EnemySchematic:
	def __init__(self, traits, idle_animation, hover_idle_animation):
		self.max_values = copy(traits)
		self.cur_values = copy(self.max_values)
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

class Enemy:
	def __init__(self, slot, schematic):
		self.slot = slot
		self.team = 1

		self.max_values = copy(schematic.max_values)
		self.cur_values = copy(schematic.cur_values)
		self.idle_animation = deepcopy(schematic.idle_animation)
		self.hover_idle_animation = deepcopy(schematic.hover_idle_animation)

		self.actions = deepcopy(schematic.actions)
		self.action_animations = deepcopy(schematic.action_animations) # Concurrent array to self.actions

		for action in self.actions:
			action.owner = self

		self.action_buttons = [ActionButton(pos=Vec(x=enemy_slot_positions[self.slot],
														y=enemy_ui_paddings[3] + i*action_button_size.y),
												linked_action=action) for i, action in enumerate(self.actions)]

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
			elif action.target_set == TargetSet.SingleAllyNotSelf:
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

	def draw(self, screen, hover=False, preview_action=None):
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
				draw_healthbar(	screen, trait_colors[trait],
								Vec(x_pos, enemy_ui_paddings[1] + y_offset),
								cur_trait, max_value, preview_damage)

				y_offset += healthbar_height

			# Draws enemy sprite
			sprite_surface = wolf_enemy_surface
			if hover:
				self.hover_idle_animation.draw( screen=screen,
												pos=Vec(x_pos, enemy_ui_paddings[2]))
			else:
				self.current_animation.draw(screen=screen,
											pos=Vec(x_pos, enemy_ui_paddings[2]))

			# Draws action buttons
			for button in self.action_buttons: 
				button.draw(screen=screen, hover=False)

			# for i, action in enumerate(self.actions):
			# 	# TODO: Don't make a new action button every frame.
			# 	button = ActionButton(pos=Vec(x_pos, enemy_ui_paddings[3] + i*action_button_size.y), linked_action=action)
			# 	if i == self.current_action_index:
			# 		button.draw(screen=screen, hover=True)
			# 	else:
			# 		button.draw(screen=screen, hover=False)
	@property
	def alive(self):
		if self.cur_values[T.Vigor] > 0:
			return True
		else:
			return False
	
class Friendly:
	def __init__(self, slot, traits, idle_animation, hover_idle_animation):
		self.max_values = copy(traits)
		self.cur_values = copy(self.max_values)
		self.slot = slot
		self.team = 0
		self.actions = []
		self.action_points = 1

		self.idle_animation = copy(idle_animation)
		self.hover_idle_animation = copy(hover_idle_animation)

		self.action_animations = [] # Concurrent array to self.actions
		self.action_buttons = [] # Concurrent array to self.actions

		self.current_action_index = None
	def add_action(self, action):
		action.owner = self
		self.actions.append(deepcopy(action))
		self.action_animations.append(self.idle_animation)
		self.action_buttons.append(ActionButton(pos=Vec(x=friendly_slot_positions[self.slot],
														y=friendly_ui_paddings[3] + (len(self.actions)-1)*action_button_size.y),
												linked_action=action))
	def set_animation(self, action_index, animation):
		if action_index > len(self.action_animations)-1:
			print("Tried to set friendly animation for non-existent action.")
			return

		self.action_animations[action_index] = animation
	@property
	def rect(self):
		rect = self.current_animation.rect
		rect.pos += get_sprite_slot_pos(slot=self.slot, team=self.team)
		return rect
	@property
	def alive(self):
		if self.cur_values[T.Vigor] > 0:
			return True
		else:
			return False		
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
	
	def start_action(self, action_index):
		if self.alive:
			self.current_action_index = action_index
	def draw(self, screen, mouse_pos, preview_action=None):
		if self.alive:
			x_pos = friendly_slot_positions[self.slot]

			# Draws action point text
			if self.action_points == 0:
				text_color = c.grey
			else:
				text_color = c.white
			draw_text(	screen=screen,
						color=text_color,
						pos=Vec(x_pos, friendly_ui_paddings[0]),
						text=str(self.action_points),
						font=main_font_5,
						x_center=False)

			# Draw trait bars
			cur_y_offset = 0 # Tracks y offset for consecutive stacked trait bars
			for trait, max_value in self.max_values.items():
				cur_trait = self.cur_values[trait]
				preview_damage = 0
				if preview_action is not None:
					preview_damage = preview_action.damages[trait]

				draw_healthbar(	screen, trait_colors[trait],
								Vec(x_pos, friendly_ui_paddings[1] + cur_y_offset),
								cur_trait, max_value, preview_damage)

				cur_y_offset += healthbar_height

			# Draws sprite
			self.current_animation.draw(screen=screen,
										pos=Vec(x_pos, friendly_ui_paddings[2]))

			# Draws action buttons
			if self.action_points > 0:
				for button in self.action_buttons:
					button.draw(screen=screen, hover=button.check_hover(mouse_pos=mouse_pos))
			else:
				for button in self.action_buttons:
					button.draw(screen=screen, hover=False)

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
	SingleAllyNotSelf = 3
	AllAllies = 4
	SingleEnemy = 5
	AllEnemies = 6

target_set_strings = {	TargetSet.All: "All",
						TargetSet.Self: "Self",
						TargetSet.SingleAlly: "Single Ally",
						TargetSet.SingleAllyNotSelf: "Single Ally (Not Self)",
						TargetSet.SingleEnemy: "Single Enemy",
						TargetSet.AllEnemies: "All Enemies",
						TargetSet.AllAllies: "All Allies"}

class Action:
	def __init__(self, name, owner, target_set, required, damages):
		self.sub_actions = []
		self.name = name
		self.owner = owner
		self.target_set = target_set
		self.required = required
		self.damages = damages
	def add_sub_action(self, sub_action):
		self.sub_actions.append(sub_action)
	def can_use(self, user_traits):
		for trait, value in user_traits.items():
			if value < self.required[trait]:
				return False
		return True		
	def execute(self, user_traits, kwargs={}):
		if self.can_use(user_traits) == True:
			for sub_action in self.sub_actions:
				sub_action(**kwargs)
			return True
		else:
			return False
		

action_button_size =  Vec(175,100)
class ActionButton:
	def __init__(self, pos, linked_action):
		self.pos = pos
		self.size = action_button_size
		self.linked_action = linked_action
	def draw(self, screen, hover):
		if hover:
			border_color = c.red
			text_color = c.white
		else:
			border_color = c.grey
			text_color = c.grey

		padding = Vec(20,20) # Padding between upper left corner and text for action and target set text.

		# Button border
		draw_rect(screen, border_color, self.pos, self.size, 1)

		# Action name text
		prev_line = draw_text(	screen=screen, color=text_color, pos=self.pos + padding,
								text=self.linked_action.name, x_center=False, y_center=False, font=main_font_5_u)
		prev = prev_line
		for trait, required in self.linked_action.required.items():
			if required != 0:
				s = require_surfaces[trait]
				prev = draw_surface(screen=screen, pos=prev.center_right+Vec(s.get_width()/2 + 8, 0), surface=require_surfaces[trait],
									x_align=AlignX.Center, y_align=AlignY.Center)
				draw_text(	screen=screen, color=c.white, pos=prev.center,
							text=str(required), x_center=True, y_center=True, font=main_font_10)
				if(self.linked_action.owner.cur_values[trait] < required):
					draw_x(screen=screen, color=c.grey, rect=prev)

		# Target set text
		prev = draw_text(	screen=screen, color=text_color, pos=prev_line.bottom_left, text=target_set_strings[self.linked_action.target_set],
							x_center=False, y_center=False, font=main_font_4)

		# Trait sword icons and overlay'd damage text for the action
		for trait, damage in self.linked_action.damages.items():
			if damage != 0:
				prev = draw_surface(screen, prev.bottom_left, sword_surfaces[trait])
				draw_text(screen, c.white, prev.center, str(self.linked_action.damages[trait]), font=main_font_7)				

		# Return extent of drawn button
		return self.rect
	def check_hover(self, mouse_pos):
		if(
				mouse_pos.x > self.pos.x
			and mouse_pos.x < self.pos.x + self.size.x
			and mouse_pos.y > self.pos.y
			and mouse_pos.y < self.pos.y + self.size.y
		):
			return True
		else:
			return False

	@property
	def rect(self):
		return Rect(self.pos, self.size)
	

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

class Game:
	def __init__(self):
		pg.init()
		self.screen = pg.display.set_mode((screen_width, screen_height))

		self.turn = Turn(True)
		# action_state represents what action the play is currently doing (after clicking a card, it might be "targeting")
		self.action_state = "Action Select"
		self.target_start_pos = Vec(0,0)
		#self.selected_action = None
		self.selected_action_button = None

		self.active_timers = []
		self.active_animations = []

		self.friendlies = []
		self.friendlies.append(Friendly(slot=0,
										traits={T.Vigor:50, T.Armor:10, T.Focus:5},
										idle_animation=FullAnimation(	sprites=[character_surface],
																		sprite_lengths=[1],
																		anchor_points=[Vec(0,character_surface.get_height())]),
										hover_idle_animation=FullAnimation(	sprites=[character_highlighted_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,character_highlighted_surface.get_height())])
										)
									)
		self.friendlies.append(Friendly(slot=1,
										traits={T.Vigor:35, T.Armor:5, T.Focus:8},
										idle_animation=FullAnimation(	sprites=[character_surface],
																		sprite_lengths=[1],
																		anchor_points=[Vec(0,character_surface.get_height())]),
										hover_idle_animation=FullAnimation(	sprites=[character_highlighted_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,character_highlighted_surface.get_height())])
										)		
									)


		for friendly in self.friendlies:
			# Rest
			rest_action = Action(	name="Rest",
									owner=None,
									target_set=TargetSet.Self,
									required={T.Vigor:0, T.Focus:0, T.Armor:0}, 
									damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
			rest_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																					'targets': targets, 
																					'damages': rest_action.damages}))

			# Strike
			strike_action = Action(	name="Strike",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:5, T.Focus:0, T.Armor:0},
									damages={T.Vigor:2, T.Focus:0, T.Armor:0})
			strike_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																						'targets': targets, 
																						'damages': strike_action.damages}))

			# Intimidate
			intimidate_action = Action(	name="Intimidate",
										owner=None,
										target_set=TargetSet.SingleEnemy,
										required={T.Vigor:0, T.Focus:1, T.Armor:0},
										damages={T.Vigor:0, T.Focus:5, T.Armor:0})
			intimidate_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																							'targets': targets, 
																							'damages': intimidate_action.damages}))

			# Bash
			bash_action = Action(	name="Bash",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:0, T.Focus:0, T.Armor:2})
			bash_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																					'targets': targets, 
																					'damages': bash_action.damages}))

			friendly.add_action(rest_action)
			friendly.add_action(strike_action)
			friendly.add_action(intimidate_action)
			friendly.add_action(bash_action)

			rest_animation_length = 60
			rest_sprite_animation = FullAnimation(	#end_pos=Vec(0,30),
													#jerk=1.0,
													#tweens=[Tween(end_pos=Vec(0,30), jerk=1.0, duration=rest_animation_length)]
													duration=rest_animation_length,
													sprites=[character_highlighted_surface],
													sprite_lengths=[rest_animation_length],
													anchor_points=[Vec(0, character_highlighted_surface.get_height())])
			friendly.set_animation(	action_index=0,
									animation=rest_sprite_animation)

			strike_animation_length = 60
			strike_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
													#jerk=5.0,
													duration=strike_animation_length,
													sprites=[character_surface],
													sprite_lengths=[strike_animation_length],
													anchor_points=[Vec(0, character_surface.get_height())])
			friendly.set_animation(	action_index=1,
									animation=strike_sprite_animation)

			intimidate_animation_length = 60
			intimidate_sprite_animation = FullAnimation(#end_pos=Vec(-20,0),
														#jerk=0.7,
														duration=intimidate_animation_length,
														sprites=[character_surface],
														sprite_lengths=[intimidate_animation_length],
														anchor_points=[Vec(0, character_surface.get_height())])
			friendly.set_animation(	action_index=2,
									animation=intimidate_sprite_animation)

			bash_animation_length = 60
			bash_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
												#		jerk=0.5,												
														duration=bash_animation_length,
														sprites=[character_surface],
														sprite_lengths=[bash_animation_length],
														anchor_points=[Vec(0, character_surface.get_height())])
			friendly.set_animation(	action_index=3,
									animation=bash_sprite_animation)			


		# START: Wolf schematic
		wolf_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:0, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[wolf_enemy_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,wolf_enemy_surface.get_height())]),
											hover_idle_animation=FullAnimation(	sprites=[wolf_enemy_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,wolf_enemy_highlighted_surface.get_height())])
											)
		# Bite
		bite_action = Action(	name="Bite",
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
												anchor_points=[Vec(0, wolf_enemy_surface.get_height())])
		wolf_schematic.set_animation(	action_index=0,
										animation=bite_sprite_animation)

		howl_animation_length = 60
		howl_sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(20,0), jerk=0.5, duration=rest_animation_length)],
												duration=howl_animation_length,
												sprites=[wolf_enemy_howl_surface],
												sprite_lengths=[howl_animation_length],
												anchor_points=[Vec(0, wolf_enemy_howl_surface.get_height())])
		wolf_schematic.set_animation(	action_index=1,
										animation=howl_sprite_animation)
		# END: Wolf schematic

		# START: Human schematic
		human_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:10, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[human_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,human_surface.get_height())]),
											hover_idle_animation=FullAnimation(	sprites=[human_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,human_highlighted_surface.get_height())])
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
		armor_action = Action(	name="Armor",
								owner=None,
								target_set=TargetSet.SingleAllyNotSelf,
								required={T.Vigor:0, T.Focus:0, T.Armor:1},
								damages={T.Vigor:0, T.Focus:0, T.Armor:-1})
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': targets, 
																				'damages': armor_action.damages}))
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': TargetSet.Self, 
																				'damages': {T.Vigor:0, T.Armor:1, T.Focus:0}}))

		human_schematic.add_action(heal_action)
		human_schematic.add_action(armor_action)

		# Heal Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(30,0), jerk=0.2, duration=animation_length)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.get_height())])
		human_schematic.set_animation(	action_index=0,
										animation=sprite_animation)

		# Armor Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.1, duration=30),
													Tween(start_pos=Vec(-100,0), end_pos=Vec(0,0), jerk=0.4, duration=30)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.get_height())])
		human_schematic.set_animation(	action_index=1,
										animation=sprite_animation)	
		# END: Human schematic


		self.enemies = []
		self.enemies.append(Enemy(slot=0, schematic=wolf_schematic))
		self.enemies.append(Enemy(slot=1, schematic=wolf_schematic))
		self.enemies.append(Enemy(slot=2, schematic=human_schematic))


		self.left_mouse_clicked = False
		self.right_mouse_clicked = False
		self.game_clock = pg.time.Clock()
		self.input = InputState(	p_keys=None, keys=None,
									p_buttons=None, buttons=None,
									keypress_delay_interval=15, keypress_repeat_interval=3)

		if len(sys.argv) >= 2 and sys.argv[1] == '-d':
			debug.debugger = debug.DebugUI(game=self, active=True)

	def draw(self):
		for data in self.active_animations:
			data['animation'].draw(screen=self.screen, pos=data['pos'])

	def any_key_pressed(self, input_state):
		pass

	def update(self, df=1, mouse_pos=(0,0)):
		for event in pg.event.get():
			if event.type == pg.QUIT:
				sys.exit()
			elif event.type == pg.KEYDOWN:
				self.input.set_repeat_key(event.key)
			elif event.type == pg.KEYUP:
				self.input.unset_repeat_key(event.key)

		# Update
		for data in self.active_animations:
			data['animation'].update()

		# Remove finished animations from active_animations
		self.active_animations = [e for e in self.active_animations if e['animation'].finished == False]

		self.input.next_state(new_keys=pg.key.get_pressed(), new_buttons=pg.mouse.get_pressed())
		self.input.update(df=1)
		self.any_key_pressed(input_state=self.input)
		#mouse_buttons = pg.mouse.get_pressed()
		mouse_x, mouse_y = pg.mouse.get_pos()
		mouse_pos = Vec(mouse_x, mouse_y)

		if self.turn.player_active:
			if self.input.pressed(key=pg.K_q):
				self.turn.end_turn(friendlies=self.friendlies, enemies=self.enemies)
			if self.input.pressed(button=0): # Left mouse pressed
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

			if self.input.pressed(button=2): # Right mouse pressed
				if self.action_state == "Target Select":
					self.action_state = "Action Select"

		for i, timer in enumerate(self.active_timers):
			finished = timer.tick()
			if finished:
				del self.active_timers[i]

		# Update game objects
		self.turn.update(friendlies=self.friendlies, enemies=self.enemies)
		for enemy in self.enemies:
			enemy.update()

		# Calculate the hovered target set for slot highlighting
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
			all_action_points_exhausted = True
			for friendly in self.friendlies:
				if friendly.action_points > 0:
					all_action_points_exhausted = False
			if all_action_points_exhausted == True:
				self.turn.end_turn(friendlies=self.friendlies, enemies=self.enemies)


		self.screen.fill(c.dkgrey)

		# Draw friendlies
		for friendly in self.friendlies:
			if friendly in previewed_target_set and self.action_state == "Target Select":
				friendly.draw(screen=self.screen, mouse_pos=mouse_pos, preview_action=action)
				highlight_surface = pg.Surface((200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				self.screen.blit(highlight_surface, (friendly_slot_positions[friendly.slot], 0))
			else:
				back_surface = pg.Surface((200,screen_height))
				back_surface.set_alpha(20)
				back_surface.fill(c.white)

				#self.screen.blit(back_surface, (friendly_slot_positions[friendly.slot], 0))

				if self.turn.player_active == True:
					highlight_surface = pg.Surface((200,screen_height))
					highlight_surface.set_alpha(30)
					if friendly.action_points == 0:
						highlight_surface.fill(c.red)
					else:
						highlight_surface.fill(c.green)

					self.screen.blit(highlight_surface, (friendly_slot_positions[friendly.slot], 0))
				friendly.draw(screen=self.screen, mouse_pos=mouse_pos)




		# Draw enemies
		for enemy in self.enemies:
			if enemy.alive == False:
				continue
			if enemy in previewed_target_set and self.action_state == "Target Select":
				enemy.draw(screen=self.screen, hover=True, preview_action=action)
				highlight_surface = pg.Surface((200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				self.screen.blit(highlight_surface, (enemy_slot_positions[enemy.slot], 0))				
			else:
				enemy.draw(screen=self.screen, hover=False)

		if self.action_state == "Target Select":
			# targeting line/arrow
			draw_line(	screen=self.screen,
						color=c.white,
						start=self.selected_action_button.rect.center_right,
						end=mouse_pos)


		for timer in self.active_timers:
			draw_text(self.screen, c.white, Vec(10,10), "{:.1f} s".format(timer.time_remaining), x_center=False, y_center=False)

		self.draw()

		pg.display.flip()
		self.game_clock.tick(60)

	def start_animation(self, animation, pos):
		self.active_animations.append({'animation': deepcopy(animation), 'pos':pos})

def main():
	global game
	game = Game()
	while True:
		game.update(df=1, mouse_pos=(0,0))
main()