import os, sys
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (5,30)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import math
import random
from functools import partial
from enum import Enum
from copy import copy, deepcopy

import debug
from util import InputState
from harm_math import Vec, Rect
import constants as c

random.seed()

import pygame as pg
screen_width, screen_height = 1400,800

pg.font.init()
main_font_7 = pg.font.Font("font.ttf", 22)
main_font_5 = pg.font.Font("font.ttf", 18)
main_font_5_u = pg.font.Font("font.ttf", 18)
main_font_5_u.set_underline(True)
main_font_4 = pg.font.Font("font.ttf", 12)

slot_width = 200
enemy_slot_positions = [600,800,1000,1200]
friendly_slot_positions = [200,400,600]

# [top of screen => trait bars, top of screen => enemy sprite, top of screen => action icons]
enemy_ui_paddings = [100, 380, 380]
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
concentration_symbol_surface = pg.image.load("ConcentrationSymbol.png")
armor_symbol_surface = pg.image.load("ArmorSymbol.png")
vigor_symbol_surface = pg.image.load("VigorSymbol.png")

character_surface = pg.image.load("Character.png")
character_highlighted_surface = pg.image.load("CharacterHighlighted.png")

human_surface = pg.image.load("Human.png")
human_highlighted_surface = pg.image.load("Human.png")

wolf_enemy_surface = pg.image.load("WolfEnemy.png")
wolf_enemy_highlighted_surface = pg.image.load("WolfEnemyHighlighted.png")
wolf_enemy_howl_surface = pg.image.load("WolfEnemyHowl.png")

def darken_color(color, amount):
	return (int(color[0]*(1-amount)), int(color[1]*(1-amount)), int(color[2]*(1-amount)))



def draw_line(screen, color, start, end, width=1):
	pg.draw.line(screen, color, (start.x, start.y), (end.x, end.y), width)

def draw_rect(screen, color, pos, size, width=0):
	pg.draw.rect(screen, color, pg.Rect(int(pos.x), int(pos.y), int(size.x), int(size.y)), width)
	return Rect(pos, size)

def draw_text(screen, color, pos, text, font=main_font_5, x_center=True, y_center=True):
	text_surface = font.render(text, True, color)

	width, height = text_surface.get_size()
	if x_center is True:
		x = pos.x - width/2
	else:
		x = pos.x
	if y_center is True:
		y = pos.y - height/2
	else:
		y = pos.y
	
	screen.blit(text_surface, (x,y))
	size = Vec(text_surface.get_width(), text_surface.get_height())
	return Rect(pos, size)

class AlignX(Enum):
	Left = 0
	Center = 1
	Right = 2

class AlignY(Enum):
	Up = 0
	Center = 1
	Down = 2

def draw_surface(screen, pos, surface, x_align=AlignX.Left, y_align=AlignY.Up):
	aligned_pos = Vec(pos.x, pos.y)

	if x_align == AlignX.Center:
		aligned_pos.x -= surface.get_width()/2
	elif x_align == AlignX.Right:
		aligned_pos.x -= surface.get_width()

	if y_align == AlignY.Center:
		aligned_pos.y -= surface.get_height()/2
	if y_align == AlignY.Down:
		aligned_pos.y -= surface.get_height()

	screen.blit(surface, (aligned_pos.x, aligned_pos.y))

	# Return extent of drawn surface
	size = Vec(surface.get_width(), surface.get_height())
	return Rect(aligned_pos, size)


healthbar_width = 100
healthbar_height = 32
def draw_healthbar(screen, color, pos, value, max_value, preview_damage=0):
	bar_values_x_padding = 4

	prev = Rect(Vec(0,0), Vec(0,0))
	if color == c.red:
		prev = draw_surface(screen, pos, vigor_symbol_surface)
	elif color == c.ltblue:
		prev = draw_surface(screen, pos, concentration_symbol_surface)
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
	draw_text(	screen, amount_text_color, Vec(prev.right + bar_values_x_padding, prev.top + healthbar_height/2),
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

class Animation:
	def __init__(self, frame_duration):
		self.frame_duration = frame_duration
		self.current_frame = 0
	def update(self, frame_count=1):
		"""Advance animation frame.
		Return True if animation is finished, False otherwise"""
		self.current_frame += frame_count
		return self.finished
	def restart(self):
		self.current_frame = 0
	@property
	def finished(self):
		"""Returns True if the animation has finished (last frame reached), False otherwise"""
		if self.current_frame >= self.frame_duration:
			return True
		else:
			return False		

# class EmptyAnimation(Animation):
# 	def __init__(self):
# 		Animation.__init__(self=self, frame_duration=0)
# 	@property
# 	def finished(self):
# 		return True

class SpriteAnimation(Animation):
	"""Tracks animation, returning appropriate images (pygame surface) for the
	current animation frame"""
	def __init__(self, frame_duration, ):
		Animation.__init__(self=self, frame_duration=frame_duration)
		self._sprites = [] # All sprites used by the animation
		self._frames = [] # List of indexes to self._sprites for each frame in the animation.
	def add_section(self, sprite, frame_count, anchor_pos):
		"""Add a new sprite and number of frames to the end of the animation

		[sprite] surface that will be drawn during this section
		[frame_count] number of frames this surface will appear in the animation
		[anchor_pos] pos within the sprite that will be drawn at the draw position of the animation"""
		sprite_index = len(self._sprites)
		self._sprites.append(sprite)
		self._frames += [sprite_index]*frame_count
	@property
	def current_sprite(self):
		""" Returns sprite (surface) corresponding to current frame"""
		return self._sprites[self._frames[min(self.current_frame,len(self._sprites)-1)]]
	
	def __deepcopy__(self, memo):
		other = SpriteAnimation(frame_duration=self.frame_duration)

		other._sprites = self._sprites
		for i, sprite in enumerate(other._sprites):
			other._sprites[i] = sprite.copy()

		other._frames = self._frames

		return other

# class Tween(Animation):
# 	"""Tracks the positions frame-by-frame for a movement between two points.

# 	Weighted interpolation between [start_pos] and [end_pos] over [frame_duration] frames,
# 		with weighting [jerk]. [relative] tracks whether the positions should be
# 		interpreted as relative or absolute positions"""
# 	def __init__(self, frame_duration, start_pos, end_pos, jerk=1.0, relative_animation=False):
# 		Animation.__init__(self=self, frame_duration=frame_duration)
# 		self.start_pos = start_pos
# 		self.end_pos = end_pos
# 		self.jerk = jerk

# 		self.current_frame = 0

# 	@property
# 	def current_pos(self):
# 		"""Returns the pos for the current frame of the animation"""
# 		t = self.current_frame / self.frame_duration
# 		x = self.end_pos.x
# 		y = self.end_pos.y

# 		# Only use the complex expression if start and end are different in x or y respectively
# 		# (Stops jitters caused by rounding)	
# 		if(self.start_pos.x != self.end_pos.x):
# 			x = math.floor((1-pow(t,self.jerk))*self.start_pos.x + pow(t,self.jerk)*self.end_pos.x)
# 		if(self.start_pos.y != self.end_pos.y):
# 			y = math.floor((1-pow(t,self.jerk))*self.start_pos.y + pow(t,self.jerk)*self.end_pos.y)

# 		return Vec(x,y)

class Tween:
	def __init__(self, start_pos=Vec(0,0), end_pos=Vec(0,0), jerk=1.0, duration=1):
		self.start_pos=start_pos
		self.end_pos=end_pos
		self.jerk=jerk
		self.duration = duration
	def pos(self, t):
		x = self.end_pos.x
		y = self.end_pos.y

		if(self.start_pos.x != self.end_pos.x):
			x = math.floor((1-pow(t,self.jerk))*self.start_pos.x + pow(t,self.jerk)*self.end_pos.x)
		if(self.start_pos.y != self.end_pos.y):
			y = math.floor((1-pow(t,self.jerk))*self.start_pos.y + pow(t,self.jerk)*self.end_pos.y)

		return Vec(x,y)
	

class FullAnimation:
	"""Animation which contains both tween and per-frame sprites"""
	def __init__(	self,
					duration=1,
					sprites=[],
					sprite_lengths=[],
					tweens=[Tween()],
					anchor_points=[],
					loop=False):

		self.duration = duration
		self.cur_frame = 0
		self._sprites = [] # All sprites used in the animation
		self._frames = [] # Concurrent array with _sprites; which sprite to use on each frame
		self._tweens = deepcopy(tweens)
		self._tween_start_frames = [] # Concurrent to _tweens; the starting frame of each tween
		self._cur_tween_index = 0
		self.anchor_points = deepcopy(anchor_points) # Concurrent array with _sprites; corresponding anchor points
		self.loop = loop # TODO: Implement loop

		for sprite in sprites:
			self._sprites.append(sprite.copy())
		for i, sprite_length in enumerate(sprite_lengths):
			self._frames += [i]*sprite_length

		running_frame_count = 0
		for i, tween in enumerate(self._tweens):
			self._tween_start_frames.append(running_frame_count)
			running_frame_count += tween.duration 

	def update(self, frame_count=1):
		"""Advance animation frame.
		Return True if animation is finished, False otherwise"""
		self.cur_frame += frame_count

		if self._cur_tween_index != len(self._tweens)-1:
			# If the current tween isn't the last tween
			if self.cur_frame >= self._tween_start_frames[self._cur_tween_index+1]:
				# If the animation frame has reached the beginning of the next tween
				self._cur_tween_index += 1

		return self.finished
	def restart(self):
		self.cur_frame = 0
		self._cur_tween_index = 0
	@property
	def cur_tween(self):
		return self._tweens[self._cur_tween_index]
	@property
	def finished(self):
		"""Returns True if the animation has finished (last frame reached), False otherwise"""
		if self.cur_frame >= self.duration-1:
			return True
		else:
			return False

	def draw(self, screen, pos):
		cur_sprite_index = self._frames[self.cur_frame]
		print("{} / {}".format(self.cur_frame - self._tween_start_frames[self._cur_tween_index], self.cur_tween.duration))
		t = (self.cur_frame - self._tween_start_frames[self._cur_tween_index])/(self.cur_tween.duration) # should it be duration - 1?
		draw_surface(	screen=screen,
						pos=pos-
							self.anchor_points[cur_sprite_index]+
							self.cur_tween.pos(t=t),
						surface=self._sprites[cur_sprite_index])

	# @property
	# def current_extent(self):
	# 	"""Returns a Rect which represents the extent of the active sprite,
	# 	as drawn in the current position"""
	# 	return self._current_extent

	def __deepcopy__(self, memo):
		other = FullAnimation(	duration=self.duration,
								tweens=self._tweens,
								anchor_points=self.anchor_points,
								loop=self.loop)

		other._sprites = self._sprites
		for i, sprite in enumerate(other._sprites):
			other._sprites[i] = sprite.copy()

		other._frames = copy(self._frames)
		other._tween_start_frames = copy(self._tween_start_frames)

		return other		

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

		self.max_values = copy(schematic.max_values)
		self.cur_values = copy(schematic.cur_values)
		self.idle_animation = copy(schematic.idle_animation)
		self.hover_idle_animation = copy(schematic.hover_idle_animation)

		self.actions = copy(schematic.actions)
		self.action_animations = copy(schematic.action_animations) # Concurrent array to self.actions

		for action in self.actions:
			action.owner = self

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
			self.current_action_targets = None

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
	def update(self, frame_count=1):
		if self.current_action_index is not None:
			self.current_animation.update(frame_count)

			# Switch back to animation-less sprite once animation is finished
			if self.current_animation.finished is True:
				self.actions[self.current_action_index].execute(user_traits=self.cur_values,
																kwargs={	'source': self,
																			'targets':self.current_action_targets})
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
					if trait == T.Vigor:
						# Account for armor in preview damage
						armor = self.cur_values[T.Armor]
						preview_damage = max(1, preview_action.damages[trait] - armor)
					else:
						preview_damage = preview_action.damages[trait]

				# Draws trait bars
				draw_healthbar(	screen, trait_colors[trait],
								Vec(x_pos, enemy_ui_paddings[0] + y_offset),
								cur_trait, max_value, preview_damage)

				y_offset += healthbar_height

			# Draws enemy sprite
			sprite_surface = wolf_enemy_surface
			if hover:
				self.hover_idle_animation.draw( screen=screen,
												pos=Vec(x_pos, enemy_ui_paddings[1]))
			else:
				self.current_animation.draw(screen=screen,
											pos=Vec(x_pos, enemy_ui_paddings[1]))

			# Draws enemy sprite
			# draw_surface(	screen=screen,
			# 				pos=Vec(x_pos, enemy_ui_paddings[1])+self.current_animation.current_pos,
			# 				surface=self.current_animation.current_sprite,
			# 				y_align=AlignY.Down)

			for i, action in enumerate(self.actions):
				# TODO: Don't make a new action button every frame.
				button = ActionButton(pos=Vec(x_pos, enemy_ui_paddings[2] + i*action_button_size.y), linked_action=action)
				if i == self.current_action_index:
					button.draw(screen=screen, hover=True)
				else:
					button.draw(screen=screen, hover=False)
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


def deal_damage(source, targets, damages):
	if targets == TargetSet.Self:
		for trait, amount in damages.items():
			source.cur_values[trait] -= amount
			if source.cur_values[trait] < 0:
				source.cur_values[trait] = 0		
	else:
		for target in targets:
			for trait, amount in damages.items():
				if trait == T.Vigor:
					# Account for armor in any vigor damage.
					armor = target.cur_values[T.Armor]
					if amount > 0:
						target.cur_values[trait] -= max(1, amount - armor)
					else:
						target.cur_values[trait] -= amount

				else:
					target.cur_values[trait] -= amount

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
		prev = draw_text(screen, text_color, self.pos + padding, self.linked_action.name, x_center=False, font=main_font_5_u)

		# Target set text
		prev = draw_text(screen, text_color, prev.bottom_left, target_set_strings[self.linked_action.target_set], x_center=False, font=main_font_4)

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



		# self.action_buttons = []
		# self.action_buttons.append(ActionButton(Vec(0,100+action_button_size.y*0), rest_action))
		# self.action_buttons.append(ActionButton(Vec(0,100+action_button_size.y*1), strike_action))
		# self.action_buttons.append(ActionButton(Vec(0,100+action_button_size.y*2), intimidate_action))
		# self.action_buttons.append(ActionButton(Vec(0,100+action_button_size.y*3), bash_action))

		for friendly in self.friendlies:
			# Rest
			rest_action = Action(	name="Rest",
									owner=None,
									target_set=TargetSet.Self,
									required={T.Vigor:0, T.Focus:1, T.Armor:0}, 
									damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
			rest_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=rest_action.damages))

			# Strike
			strike_action = Action(	name="Strike",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:2, T.Focus:0, T.Armor:0})
			strike_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=strike_action.damages))

			# Intimidate
			intimidate_action = Action(	name="Intimidate",
										owner=None,
										target_set=TargetSet.SingleEnemy,
										required={T.Vigor:0, T.Focus:1, T.Armor:0},
										damages={T.Vigor:0, T.Focus:5, T.Armor:0})
			intimidate_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=intimidate_action.damages))

			# Bash
			bash_action = Action(	name="Bash",
									owner=None,
									target_set=TargetSet.SingleEnemy,
									required={T.Vigor:0, T.Focus:1, T.Armor:0},
									damages={T.Vigor:0, T.Focus:0, T.Armor:2})
			bash_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=bash_action.damages))		

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
		bite_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=bite_action.damages))

		# Howl
		howl_action = Action(	name="Howl",
								owner=None,
								target_set=TargetSet.AllAllies,
								required={T.Vigor:0, T.Focus:0, T.Armor:0},
								damages={T.Vigor:0, T.Focus:-1, T.Armor:0})
		howl_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=howl_action.damages))

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
		heal_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=heal_action.damages))

		# Armor
		armor_action = Action(	name="Armor",
								owner=None,
								target_set=TargetSet.SingleAllyNotSelf,
								required={T.Vigor:0, T.Focus:0, T.Armor:1},
								damages={T.Vigor:0, T.Focus:0, T.Armor:-1})
		armor_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=targets, damages=armor_action.damages))
		armor_action.add_sub_action(lambda source, targets: deal_damage(source=source, targets=TargetSet.Self, damages={T.Vigor:0, T.Focus:0, T.Armor:1}))

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
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.8, duration=animation_length)],
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
		pass

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

def main():
	game = Game()
	while True:
		game.update(df=1, mouse_pos=(0,0))
main()