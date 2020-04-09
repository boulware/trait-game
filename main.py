import os, sys
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,30)
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
from constants import EditableType, editable_type_strings
import error

typeable_chars = 	  [chr(i) for i in range(ord('a'),ord('z')+1)] \
					+ [chr(i) for i in range(ord('A'),ord('Z')+1)] \
					+ [chr(i) for i in range(ord('0'),ord('9')+1)] \
					+ [' ', '.']

random.seed()

import pygame as pg
screen_width, screen_height = 1600,800
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
# 	def mouse_button_pressed(self, game, button, mouse_pos):
#  		pass
#  	def enter(self):
#  		pass
#  	def exit(self):
#  		pass

pg.font.init()
main_font_10 = pg.font.Font("font.ttf", 28)
main_font_10_u = pg.font.Font("font.ttf", 28)
main_font_10_u.set_underline(True)
main_font_7 = pg.font.Font("font.ttf", 22)
main_font_5 = pg.font.Font("font.ttf", 18)
main_font_5_u = pg.font.Font("font.ttf", 18)
main_font_5_u.set_underline(True)
main_font_4 = pg.font.Font("font.ttf", 12)
main_font_2 = pg.font.Font("font.ttf", 8)

slot_width = 200
friendly_slot_positions = [0+i*slot_width for i in range(4)]
enemy_slot_positions = [4*slot_width+i*slot_width for i in range(4)]
# [top of screen => trait bars, top of screen => enemy sprite, top of screen => skill icons]
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
trait_to_string = {T.Vigor: "vigor", T.Armor: "armor", T.Focus: "focus"}
string_to_trait = {value:key for key,value in trait_to_string.items()}

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
# skill - optional function to execute once the timer finishes
class Timer:
	"""Tracks ticks and when the timer has elapsed.
	(optional) Automatically executes function once timer elapses"""
	def __init__(self, duration, skill=None):
		self.duration = duration
		self.current_frame = 0
		self.skill = skill
	def tick(self):
		self.current_frame += 1
		if self.current_frame >= self.duration:
			if self.skill:
				self.skill()
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

target_set_to_string = {	TargetSet.All: "all",
							TargetSet.Self: "self",
							TargetSet.SingleAlly: "single ally",
							TargetSet.OtherAlly: "other ally",
							TargetSet.SingleEnemy: "single enemy",
							TargetSet.AllEnemies: "all enemies",
							TargetSet.AllAllies: "all allies"}

string_to_target_set = {value:key for key,value in target_set_to_string.items()}

class DamageEffect:
	def __repr__(self):
		return 'damage {}'.format([e for k,e in self.base_damage.items()])
	def __init__(self, base_damage):
		self.base_damage = base_damage
	def apply(self, target):
		# Calculate all damages before applying them to avoid order issues
		# (specifically the effect of armor on net_vigor_damage)
		net_vigor_damage = max(1, self.base_damage[T.Vigor] - target.armor)
		net_armor_damage = self.base_damage[T.Armor]
		net_focus_damage = self.base_damage[T.Focus]

		target.vigor -= net_vigor_damage
		target.armor -= net_armor_damage
		target.focus -= net_focus_damage

class HealEffect:
	def __repr__(self):
		return 'heal {}'.format([e for k,e in self.base_heal_amounts.items()])
	def __init__(self, base_heal_amounts):
		self.base_heal_amounts = base_heal_amounts
	def apply(self, target):
		target.vigor += self.base_heal_amounts[T.Vigor]
		target.armor += self.base_heal_amounts[T.Armor]
		target.focus += self.base_heal_amounts[T.Focus]

class SkillSchematic:
	def __init__(self, name, required, effect_groups):
		self.name = name
		self.required = required
		self.effect_groups = effect_groups # List of tuples: [(target_set, list of effects), ...]
	def __repr__(self):
		return 'name: {}, req: {}, effects_groups: {}'.format(self.name,self.required,self.effect_groups)
	def generate_skill(self, owner):
		return Skill(schematic=self, owner=owner)

class Skill:
	def __init__(self, schematic, owner):
		self.name = schematic.name
		self.required = copy(schematic.required)
		self.effect_groups = copy(schematic.effect_groups)
		self.owner = owner
	def apply_effects(self, target_groups):
		for i, _, effects in enumerate(self.effect_groups):
			for effect in effects:
				for target in target_groups[i]:
					effect.apply(target=target)

	# def execute(self, kwargs={}):
	# 	if self.usable is True:
	# 		for effect in self.effects:
	# 			effect(**kwargs)
	# 		return True
	# 	else:
	# 		return False
	@property
	def usable(self):
		valid_target = False

		# FIX
		# if self.target_set == TargetSet.OtherAlly:
		# 	for ally in game.active_state.get_allies(team=self.owner.team):
		# 		if ally.alive == True and ally != self.owner:
		# 			valid_target = True
		# else:
		# 	valid_target = True

		if valid_target == False:
			return False
		for trait, value in self.owner.cur_traits.items():
			if value < self.required[trait]:
				return False
		return True
class SkillSchematicDatabase:
	def __init__(self, skill_data_filepath):
		self.schematics = []

		class Token(Enum):
			Root = 0
			Skill = 1
			Target = 2

		def next_line(file):
			try:
				return next(file)
			except StopIteration:
				return None

		with open(skill_data_filepath) as f:
			name = '<NAME UNDECLARED>'
			required = {T.Vigor:0, T.Armor:0, T.Focus:0}
			effect_groups = []

			current_target_set = TargetSet.Nothing
			current_effects = []

			tokens = [Token.Root]
			line = next_line(f)
			while True:
				if line == None:
					# We're at end of file, so wrap up targets/skills and break.
					if tokens[-1] == Token.Target:
						effect_groups.append((current_target_set, current_effects))
						del tokens[-1] # pop Token.Target
						continue
					elif tokens[-1] == Token.Skill:
						self.schematics.append(SkillSchematic(name=name, required=copy(required), effect_groups=copy(effect_groups)))
						break
				if tokens[-1] == Token.Root:
					match = re.search('skill:(.*)', line.strip())
					if match:
						name = match[1].strip()
						required = {T.Vigor:0, T.Armor:0, T.Focus:0}
						effect_groups = []
						tokens.append(Token.Skill)
						line = next_line(f)
						continue
				elif tokens[-1] == Token.Skill:
					match = re.search('requires:(.*)', line.strip())
					if match:
						amount_strings = [e.strip() for e in match[1].split(',')]
						for i,s in enumerate(amount_strings):
							required[T(i)] = int(s)
						line = next_line(f)
						continue

					match = re.search('target:(.*)', line.strip())
					if match:
						current_target_set = string_to_target_set[match[1].strip()]
						current_effects = []
						tokens.append(Token.Target)
						line = next_line(f)
						continue

					match = re.search('skill:(.*)', line.strip())
					if match:
						# End of current skill.
						self.schematics.append(SkillSchematic(name=name, required=copy(required), effect_groups=copy(effect_groups)))
						del tokens[-1] # pop Token.Skill
						continue # Catches on Token.Root and start iterating new skill
				elif tokens[-1] == Token.Target:
					match = re.search('(?:target|skill):(.*)', line.strip())
					if match:
						# End of current target
						effect_groups.append((current_target_set, current_effects))
						del tokens[-1] # pop Token.Target
						continue # Catches on Token.Skill, and routes appropriately to either next target or skill
					match = re.search('(damage|heal|stun)\s*:\s*(.*)', line.strip())
					if match:
						trait_amounts = {T.Vigor:0, T.Armor:0, T.Focus:0}
						amount_strings = [e.strip() for e in match[2].split(',')]
						for i,s in enumerate(amount_strings):
							trait_amounts[T(i)] = int(s)

						if match[1].strip() == "damage":
							current_effects.append(DamageEffect(base_damage=trait_amounts))
						elif match[1].strip() == "heal":
							current_effects.append(HealEffect(base_heal_amounts=trait_amounts))
						elif match[1].strip() == "stun":
							pass

						line = next_line(f)
						continue

	def get_list_of_schematic_names(self):
		return [e.name for e in self.schematics]
	def get_schematic_by_name(self, name):
		return next(s for s in self.schematics if s.name == name)
	def generate_skill(self, name, owner):
		if name == '':
			return None
		schematic = next(s for s in self.schematics if s.name == name)
		return schematic.generate_skill(owner=owner)

class UnitSchematic:
	def __init__(self, name, description, traits, idle_animation, hover_idle_animation):
		self.name = name
		self.description = description
		self.traits = copy(traits)
		self.idle_animation = copy(idle_animation)
		self.hover_idle_animation = copy(hover_idle_animation)

		self.skill_schematics = [None] * c.skill_slots
		self.skill_animations = [None] * c.skill_slots # Concurrent array to self.skills
	@classmethod
	def from_string(cls, s):
		pass
		name = "<PLACEHOLDER NAME>"
		description = "<PLACEHOLDER DESCRIPTION>"
		traits = {T.Vigor: 0, T.Armor: 0, T.Focus: 0}
		idle_animation = None
		hover_idle_animation = None
		skill_schematics = []

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
				# or: "(has) skill Rest"
				match = re.search('([0-9]+) ([a-zA-Z]*)', line_match[1])
				if match:
					value = int(match[1])
					trait = string_to_trait[match[2]]
					traits[trait] = value
					continue
				match = re.search('skill (.*)', line_match[1])
				if match:
					skill_name = match[1]
					global game
					skill_schematics.append(game.skill_db.get_schematic_by_name(name=skill_name))
					continue

		# Generate unit schematic
		new = cls(	name=name,
					description=description,
					traits=traits,
					idle_animation=idle_animation,
					hover_idle_animation=hover_idle_animation)
		for i,s in enumerate(skill_schematics):
			new.skill_schematics[i] = s
		# Just fill the skill_animations list with our idle animations.
		# They'll be replaced later when the animations are read from
		# data files
		new.skill_animations = [idle_animation]*c.skill_slots

		return new
	def generate_unit(self, team, slot):
		return Unit(schematic=self, team=team, slot=slot)
	# def set_animation(self, skill_index, animation):
	# 	if skill_index > len(self.skill_animations)-1:
	# 		return

	# 	self.skill_animations[skill_index] = animation
	def serialize(self):
		s = ""
		s += "name is {}\n".format(self.name)
		for trait, value in self.max_traits.items():
			if value == 0: continue
			s += "\thas {} {}\n".format(value, trait_strings[trait])
		for skill in self.skills:
			s += "\thas skill {}\n".format(skill.name)

		return s
class Unit:
	def __init__(self, team, slot, schematic):
		self.name = schematic.name
		self.description = schematic.description
		self.team = team
		self.slot = slot
		self.max_traits = copy(schematic.traits)
		self.cur_traits = copy(schematic.traits)
		self.idle_animation = deepcopy(schematic.idle_animation)
		self.hover_idle_animation = deepcopy(schematic.hover_idle_animation)

		self.skills = [None]*c.skill_slots
		for i,s in enumerate(schematic.skill_schematics):
			if s == None:
				self.skills[i] = None
			else:
				self.skills[i] = s.generate_skill(owner=self)

		self.skill_animations = deepcopy(schematic.skill_animations)

		for skill in self.skills:
			if skill != None:
				skill.owner = self

		non_empty_skills = [e for e in self.skills if e != None] # We only want to generate buttons for non-empty skills
		self.skill_buttons = [SkillButton(pos=Vec(x=get_slot_x_pos(team=self.team, slot=self.slot),
													y=get_team_ui_padding(team=self.team, index=3) + i*skill_button_size.y),
												linked_skill=skill) for i, skill in enumerate(non_empty_skills)]

		self.skill_points = 1
		self.current_skill_index = None
		self.current_skill_targets = None
	@property
	def max_vigor(self):
		return self.max_traits[T.Vigor]
	@property
	def max_armor(self):
		return self.max_traits[T.Armor]
	@property
	def max_focus(self):
		return self.max_traits[T.Focus]

	@property
	def vigor(self):
		return self.cur_traits[T.Vigor]
	@property
	def armor(self):
		return self.cur_traits[T.Armor]
	@property
	def focus(self):
		return self.cur_traits[T.Focus]
	@vigor.setter
	def vigor(self, new_value):
		self.cur_traits[T.Vigor] = min(self.max_vigor, new_value)

		if self.vigor <= 0:
			# Vigor break (death)
			pass
	@armor.setter
	def armor(self, armor):
		self.cur_traits[T.Armor] = min(self.max_armor, new_value)

		if self.armor <= 0:
			# Armor break
			pass
	@focus.setter
	def focus(self, focus):
		self.cur_traits[T.Focus] = min(self.max_focus, new_value)

		if self.focus <= 0:
			# Focus break
			pass

	@property
	def current_animation(self):
		if self.current_skill_index is None:
			return self.idle_animation
		else:
			if len(self.skill_animations) != 0:
				return self.skill_animations[self.current_skill_index]
			else:
				return self.idle_animation
	@property
	def skill_finished(self):
		if self.current_skill_index == None or self.alive == False:
			return True
		else:
			return False
	@property
	def current_skill(self):
		if self.current_skill_index != None:
			return self.skills[self.current_skill_index]
		else:
			return None
	@property
	def rect(self):
		rect = self.current_animation.rect
		rect.pos += get_sprite_slot_pos(slot=self.slot, team=self.team)
		return rect
	def start_skill(self, skill, targeted, valid_targets):
		if self.alive:
			self.current_skill_index = next(i for i,a in enumerate(self.skills) if a==skill)
			targets = valid_targets
			if skill.target_set is TargetSet.SingleAlly:
				targets = [targeted]
			elif skill.target_set == TargetSet.Self and targeted == self:
				targets = [self]
			elif skill.target_set is TargetSet.SingleEnemy:
				targets = [targeted]

			self.current_skill_targets = targets
			self.current_skill.execute(kwargs={'source': self,
												'targets': targets})
			self.skill_points -= 1
	def start_random_skill(self, allies, enemies):
		if self.alive:
			possible_skills_indices = [i for i,a in enumerate(self.skills) if a != None and a.usable == True] # Skills which have their pre-reqs fulfilled
			# Check each of our skills, and add them to the list of possible random skills

			if len(possible_skills_indices) == 0:
				return

			self.current_skill_index = random.choice(possible_skills_indices)
			self.current_skill_targets = []

			skill = self.skills[self.current_skill_index]
			if skill.target_set == TargetSet.Self:
				self.current_skill_targets = [self]
			elif skill.target_set == TargetSet.SingleAlly:
				non_dead_allies = [e for e in allies if e.alive == True]
				if len(non_dead_allies) > 0:
					self.current_skill_targets = [random.choice(non_dead_allies)]
			elif skill.target_set == TargetSet.OtherAlly:
				non_self_non_dead_allies = [e for e in allies if e != self and e.alive == True]
				if len(non_self_non_dead_allies) > 0:
					self.current_skill_targets = [random.choice(non_self_non_dead_allies)]
			elif skill.target_set == TargetSet.AllAllies:
				non_dead_allies = [e for e in allies if e.alive == True]
				if len(non_dead_allies) > 0:
					self.current_skill_targets = non_dead_allies
			elif skill.target_set == TargetSet.SingleEnemy:
				if len(enemies) > 0:
					self.current_skill_targets = [random.choice(enemies)]
			elif skill.target_set == TargetSet.AllEnemies:
				if len(enemies) > 0:
					self.current_skill_targets = enemies

			if self.current_skill_index != None and self.current_skill_targets != None:
				self.current_animation.restart()

			self.skills[self.current_skill_index].execute(kwargs={'source': self,
																	'targets':self.current_skill_targets})

	def update(self, frame_count=1):
		if self.current_skill_index is not None:
			self.current_animation.update(frame_count)

			# Switch back to animation-less sprite once animation is finished
			if self.current_animation.finished is True:
				self.current_skill_index = None
				self.current_skill_targets = None
	def draw(self, target, mouse_pos, preview_skill=None):
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
				# if preview_skill is not None:
				# 	if trait == T.Vigor and preview_skill.damages[T.Vigor] > 0:
				# 		# Account for armor in preview damage
				# 		armor = self.cur_traits[T.Armor]
				# 		preview_damage = max(1, preview_skill.damages[trait] - armor)
				# 	else:
				# 		preview_damage = preview_skill.damages[trait]

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

			# Draws skill buttons
			for button in self.skill_buttons:
				#if button.linked_skill == self.current_skill:
				if button.linked_skill == preview_skill:
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
			skill_index = None
			string = ""
			while line:
				match = re.search('^([a-zA-Z]*)\'s (.*)', line.rstrip())
				if match:
					if unit_index == None:
						# This is the beginning of an animation
						print(self.schematics)
						unit_index, unit_schematic = next((i,s) for i,s in enumerate(self.schematics) if s.name == match[1])
						skill_index = next(i for i,s in enumerate(unit_schematic.skill_schematics) if s.name == match[2])
						string += line
					else:
						# This is the beginning of an animation, and
						# we've reached the end of the previous animation string
						anim = Animation.from_string(string)
						self.schematics[unit_index].skill_animations[skill_index] = anim
						unit_index, unit_schematic = next((i,s) for i,s in enumerate(self.schematics) if s.name == match[1])
						skill_index = next(i for i,s in enumerate(unit_schematic.skill_schematics) if s.name == match[2])
						string = line
				else:
					string += line

				line = f.readline()

			if string:
				# If there's still an animation, add it
				anim = Animation.from_string(string)
				self.schematics[unit_index].skill_animations[skill_index] = anim


	def get_list_of_schematic_names(self):
		return [s.name for s in self.schematics]
	def get_schematic_by_name(self, name):
		try:
			return next(s for s in self.schematics if s.name == name)
		except StopIteration:
			return None
	def generate_unit(self, name, team, slot):
		schematic = next(s for s in self.schematics if s.name == name)
		return schematic.generate_unit(team=team, slot=slot)

skill_button_size =  Vec(150,60)
skill_info_size = Vec(200,70)
class SkillButton:
	def __init__(self, pos, linked_skill):
		self.pos = pos
		self.size = skill_button_size
		self.linked_skill = linked_skill

		self.surface = None
		self.hover_surface = None
		self.unable_surface = None # Surface if skill requirements aren't mean
		self.info_box_surface = None
		self.refresh_surfaces()
	@property
	def owner(self):
		return self.linked_skill.owner
	def refresh_surfaces(self):
		# Non-hovered surface
		back_color = c.dkgrey
		border_color = c.grey
		text_color = c.grey

		self.surface = Surface(self.size)

		# Button background and border
		draw_rect(target=self.surface, color=back_color, pos=Vec(0,0), size=self.size, width=0)
		draw_rect(target=self.surface, color=border_color, pos=Vec(0,0), size=self.size, width=1)

		# Skill name text
		prev_line = draw_text(	target=self.surface, color=text_color, pos=Vec(skill_button_size.x/2, 0),
								text=self.linked_skill.name, x_center=True, y_center=False, font=main_font_5_u)
		prev = prev_line
		for trait, required in self.linked_skill.required.items():
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
				# if(self.linked_skill.owner.cur_traits[trait] < required):
				# 	draw_x(target=self.surface, color=c.grey, rect=prev)

		# Target set text
		# prev = draw_text(	target=self.surface, color=text_color, pos=prev_line.bottom_left, text=target_set_to_string[self.linked_skill.target_set],
		# 					x_center=False, y_center=False, font=main_font_4)

		# Trait sword icons and overlay'd damage text for the skill
		# for trait, damage in self.linked_skill.damages.items():
		# 	if damage != 0:
		# 		prev = draw_surface(target=self.surface, pos=prev.center_bottom, surface=sword_surfaces[trait], x_align=AlignX.Center)
		# 		draw_text(target=self.surface, color=c.white, pos=prev.center, text=str(self.linked_skill.damages[trait]), font=main_font_7)

		# Hovered surface
		hover_back_color = c.ltgrey
		hover_border_color = c.red
		hover_text_color = c.white

		self.hover_surface = Surface(self.size)

		# Button background and border
		draw_rect(target=self.hover_surface, color=hover_back_color, pos=Vec(0,0), size=self.size, width=0)
		draw_rect(target=self.hover_surface, color=hover_border_color, pos=Vec(0,0), size=self.size, width=1)

		# Skill name text
		prev_line = draw_text(	target=self.hover_surface, color=hover_text_color, pos=Vec(skill_button_size.x/2, 0),
								text=self.linked_skill.name, x_center=True, y_center=False, font=main_font_5_u)
		prev = prev_line
		for trait, required in self.linked_skill.required.items():
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
				# if(self.linked_skill.owner.cur_traits[trait] < required):
				# 	draw_x(target=self.hover_surface, color=hover_c.grey, rect=prev)

		# FIX
		# Target set text
		# prev = draw_text(	target=self.hover_surface, color=hover_text_color, pos=prev_line.bottom_left, text=target_set_to_string[self.linked_skill.target_set],
		# 					x_center=False, y_center=False, font=main_font_4)

		# FIX
		# Trait sword icons and overlay'd damage text for the skill
		# for trait, damage in self.linked_skill.damages.items():
		# 	if damage != 0:
		# 		prev = draw_surface(target=self.hover_surface, pos=prev.center_bottom, surface=sword_surfaces[trait], x_align=AlignX.Center)
		# 		draw_text(target=self.hover_surface, color=c.white, pos=prev.center, text=str(self.linked_skill.damages[trait]), font=main_font_7)

		# Info box surface
		self.info_box_surface = Surface(skill_info_size)

		# Background box and border
		draw_rect(target=self.info_box_surface, color=[50]*3, pos=Vec(0,0), size=skill_info_size, width=0)
		draw_rect(target=self.info_box_surface, color=c.white, pos=Vec(0,0), size=skill_info_size, width=1)
		prev=draw_text(	target=self.info_box_surface, color=c.white, pos=Vec(skill_info_size.x/2, 0),
						text=self.linked_skill.name, font=main_font_5_u, x_center=True, y_center=False)
		#target, text, pos, font, color=c.white, word_wrap_width=None):
		# prev=draw_text_wrapped(	target=self.info_box_surface, color=c.white, pos=Vec(skill_info_size.x*0.1, prev.bottom),
		# 						text=self.linked_skill.description, font=main_font_4, word_wrap_width=skill_info_size.x*0.9)

		# Unable Surface
		self.unable_surface = copy(self.surface)
		draw_x(target=self.unable_surface, color=c.red, rect=Rect(pos=Vec(0,0), size=skill_button_size))

	def draw_info_box(self, mouse_pos):
		game.queue_surface(surface=self.info_box_surface, depth=10, pos=mouse_pos)
	def draw(self, game, mouse_pos, force_highlight=False):
		if self.linked_skill.usable == False:
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
		# TODO: Should skill buttons ever really be copy'd or deepcopy'd? Almost everything
		# 		has to be changed anyway.
		# self.pos = pos
		# self.size = skill_button_size
		# self.linked_skill = linked_skill
		# self.surface = None
		# self.hover_surface = None
		# self.refresh_surfaces()
		other = SkillButton(	pos=self.pos,
								linked_skill=self.linked_skill)




class Turn:
	def __init__(self, initial_active=True):
		self.player_active = initial_active
		self.current_enemy = None
	def end_turn(self, friendlies, enemies):
		if self.player_active is True:
			# Switch from player's turn to enemy's turn
			self.player_active = False
			self.current_enemy = 0
			enemies[self.current_enemy].start_random_skill(allies=enemies, enemies=friendlies) # Opposite from perspective of enemies
		else:
			# Switch back from enemy's turn to player's turn
			for friendly in friendlies:
				friendly.skill_points = 1
			self.player_active = True
			self.current_enemy = None

	def update(self, friendlies, enemies):
		# If enemy is no longer animating, move on to the next enemy.
		# If last enemy is finished, turn goes back to player
		if self.current_enemy != None and self.player_active == False:
			if enemies[self.current_enemy].skill_finished:
				self.current_enemy += 1

				if(self.current_enemy >= len(enemies)):
					self.end_turn(friendlies=friendlies, enemies=enemies)
				else:
					enemies[self.current_enemy].start_random_skill(allies=enemies, enemies=friendlies)
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


def friendly_is_valid_target(skill, target):
	if skill.target_set == TargetSet.All:
		return True
	if skill.target_set == TargetSet.SingleAlly:
		return True
	if skill.target_set == TargetSet.AllAllies:
		return True
	if skill.target_set == TargetSet.Self and skill.owner == target:
		return True

	return False

def enemy_is_valid_target(skill, target):
	if skill.target_set == TargetSet.All:
		return True
	if skill.target_set == TargetSet.SingleEnemy:
		return True
	if skill.target_set == TargetSet.AllEnemies:
		return True

	return False



class MainMenuState:
	def __init__(self):
		self.buttons = []
		self.buttons.append(Button(	pos=Vec(100,100),
									size=Vec(150,70),
									text="Start Campaign",
									function=lambda: game.start_campaign()))
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
	def reset_focus_state(self):
		self.focused = False
		self.cursor_pos = 0
		self.highlight = [0,0]
	@property
	def pos(self):
		return self.rect.pos
	@property
	def size(self):
		return self.rect.size

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
				error.log("self.cursor_pos is not equal to either highlight[0] nor highlight[1]. Something went wrong.")
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
				error.log("self.cursor_pos is not equal to either highlight[0] nor highlight[1]. Something went wrong.")
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

		new_focus_state = None
		if game.input.pressed(button=0):
			if self.rect.intersect(point=game.mouse_pos):
				self.focus(mouse_pos=game.mouse_pos)
				new_focus_state = True
			else:
				if self.focused == True:
					self.unfocus()
					new_focus_state = False

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
			if game.input.down(button=0) and self.highlight_start != None:
				i = self.pos_to_char_index(pos=game.mouse_pos)
				self.cursor_pos = i
				if i >= self.highlight_start:
					self.highlight[0] = self.highlight_start
					self.highlight[1] = i
				else:
					self.highlight[0] = i
					self.highlight[1] = self.highlight_start
			if self.blink_visible:
				x_pos = self.char_rects[self.cursor_pos].left
				game.queue_drawline(start=Vec(self.rect.left+x_pos, self.rect.top),
									end=Vec(self.rect.left+x_pos, self.rect.bottom),
									color=c.red,
									width=1,
									depth=-50)

		return new_focus_state


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

			# if game.input.down(button=0) and self.highlight_start != None:
			# 	i = self.pos_to_char_index(pos=game.mouse_pos)
			# 	self.cursor_pos = i
			# 	if i >= self.highlight_start:
			# 		self.highlight[0] = self.highlight_start
			# 		self.highlight[1] = i
			# 	else:
			# 		self.highlight[0] = i
			# 		self.highlight[1] = self.highlight_start

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

class Dropdown:
	def __init__(self, pos, size, entries=[], default=None):
		self.rect = Rect(pos=pos, size=size)
		self.entries = entries
		self.selected_index = default
		self.open = False
	@property
	def pos(self):
		return self.rect.pos
	@property
	def size(self):
		return self.rect.size
	@property
	def selected_entry(self):
		if self.selected_index != None and len(self.entries) != 0:
			return self.entries[self.selected_index]
		else:
			return None

	def select_entry_by_name(self, name):
		self.selected_index = self.entries.index(name)
	def update(self, game):
		# Mostly drawing
		if self.selected_index != None and len(self.entries) != 0:
			game.queue_drawtext(pos=self.rect.center,
								text=self.entries[self.selected_index],
								font=main_font_7,
								color=c.white,
								depth=9)
		if self.open == False:
			color = c.white
		else:
			color = c.green
		game.queue_drawrect(pos=self.pos,
							size=self.size,
							color=color,
							width=1,
							depth=10)

		if self.open == True:
			list_start = self.rect.bottom_left
			for i, text in enumerate(self.entries):
				entry_start = list_start + Vec(0, i*self.size.y)

				if Rect(entry_start, self.size).intersect(point=game.mouse_pos):
					if game.input.pressed(button=0):
						self.selected_index = i
						self.open = False
					outline_color = c.green
					text_color = c.white
				else:
					outline_color = c.grey
					text_color = c.ltgrey

				game.queue_drawrect(pos=entry_start,
									size=self.size,
									color=c.dkgrey,
									width=0,
									depth=5)
				game.queue_drawrect(pos=entry_start,
									size=self.size,
									color=outline_color,
									width=1,
									depth=4)
				game.queue_drawtext(pos=entry_start+self.size/2,
									text=text,
									font=main_font_7,
									color=text_color,
									depth=3)

		if self.rect.intersect(game.mouse_pos) or self.open == True:
			game.queue_drawrect(pos=self.pos,
								size=self.size,
								color=c.grey,
								depth=11)

		# Mostly logic
		if game.input.pressed(button=0):
			if self.rect.intersect(point=game.mouse_pos):
				self.open = not self.open
			else:
				self.open = False
		if game.input.pressed(button=2):
			self.open = False


class ListView:
	def __init__(	self, pos, size, entry_height, font,
					entries=[], default=None):
		self.rect = Rect(pos=pos, size=size)
		self.entry_height = entry_height
		self.font = font
		self.entries = entries

		self.selected_index = default
	@property
	def selected_entry(self):
		if self.selected_index == None:
			return ''
		return self.entries[self.selected_index]
	@property
	def pos(self):
		return self.rect.pos
	@property
	def size(self):
		return self.rect.size

	def update(self, game):
		state_changed = False

		game.queue_drawrect(pos=self.pos,
							size=self.size,
							color=c.white,
							width=1,
							depth=0)

		# TODO: For performance, we should render and cache text surfaces
		for i, e in enumerate(self.entries):
			rect = Rect(pos=self.pos + Vec(0, i*self.entry_height+1),
						size=Vec(self.size.x, self.entry_height-1))
			if rect.intersect(game.mouse_pos):
				# If hovered, draw highlighted background
				game.queue_drawrect(pos=rect.pos,
									size=rect.size,
									color=c.grey,
									depth=10)

				if game.input.pressed(button=0):
					self.selected_index = i
					state_changed = True

			if self.selected_index == i:
				text_color = c.green
			else:
				text_color = c.white

			game.queue_drawtext(text=e,
								font=self.font,
								color=text_color,
								x_center=True,
								y_center=True,
								pos=self.pos + Vec(0, i*self.entry_height) + 0.5*Vec(self.size.x, self.entry_height),
								depth=2)
			game.queue_drawline(start=self.pos + Vec(0, (i+1)*self.entry_height),
								end=self.pos + Vec(self.size.x, (i+1)*self.entry_height),
								color=c.ltgrey,
								depth=1)

		return state_changed

	def draw(self, game):
		pass

class EditorState:
	def __init__(self):
		self.entry_list_start = Vec(0, 100)
		self.entry_height = 50
		self.left_pane_width = 400

		# UI elements that display and allow editing of object properties
		self.property_ui_elements = [None] * len(c.unit_ui_indices)

		self.focused_index = None # Index of UI element currently focused

		# Schematic that's currently available for editing in right pane
		self.loaded_schematic = None

		# ListView of editable types (e.g., Unit, Skill, Battle)
		self.editable_type_listview = ListView(	pos=Vec(20,0),
												size=Vec(100, 150),
												entry_height=50,
												font=main_font_7,
												entries=editable_type_strings,
												default=0)

		# ListView of editable objects of the selected editable type
		# e.g., Warrior, Wolf ... Rest, Intimidate
		self.entry_listview = ListView(	pos=Vec(0,200),
										size=Vec(200, 400),
										entry_height=50,
										font=main_font_5,
										entries=[])

		# Individual properties UI layout for each editable type
		self.property_ui_elements = {
			EditableType.Unit: [],
			EditableType.Skill: [],
			EditableType.Battle: []
		}
		property_ui_origin = Vec(500,50)
		property_textbox_width = 300
		for editable_type, ui_elements in self.property_ui_elements.items():
			for property_string, i in c.ui_indices[editable_type].items():
				ui_elements.append(TextBox(	rect=Rect(	pos=property_ui_origin+Vec(0, i*50),
														size=Vec(property_textbox_width, 50)),
											font=main_font_5,
											initial_text="<{}>".format(property_string)))


		# Set up surfaces for text labels of property UI elements
		self.property_label_text_surfaces = {
			EditableType.Unit: 	 [None] * len(c.unit_ui_indices),
			EditableType.Skill: [None] * len(c.skill_ui_indices),
			EditableType.Battle: [None] * len(c.battle_ui_indices)
		}
		for editable_type, text_surfaces in self.property_label_text_surfaces.items():
			for property_string, i in c.ui_indices[editable_type].items():
				print(property_string, i, editable_type)
				text_surfaces[i] = Surface.from_pgsurface(main_font_7.render(property_string, True, c.grey))

		self.save_button = Button(	pos=Vec(screen_width-120, screen_height-70),
									size=Vec(100,50),
									text="Save",
									function=self.save)

		self.test_battle_button = Button(	pos=Vec(screen_width/2, screen_height-140),
											size=Vec(200,100),
											text="Save & Test Battle",
											function=self.start_test_battle)

		self.dropdowns = {
			EditableType.Unit: 	 [None] * len(c.unit_ui_dropdowns),
			EditableType.Skill: [None] * len(c.skill_ui_dropdowns),
			EditableType.Battle: [None] * len(c.battle_ui_dropdowns)
		}

		global game
		for editable_type, dropdown_group in self.dropdowns.items():
			if editable_type == EditableType.Unit:
				for i, pos in enumerate(c.unit_ui_dropdowns):
					dropdown_group[i] = Dropdown(	pos=pos,
													size=Vec(200,40),
													entries=[''] + game.skill_db.get_list_of_schematic_names(),
													default=0)
			elif editable_type == EditableType.Skill:
				dropdown_group[0] = Dropdown(	pos=c.skill_ui_dropdowns[0],
												size=Vec(200,40),
												entries=[s for k,s in target_set_to_string.items()],
												default=0)
			elif editable_type == EditableType.Battle:
				for i, pos in enumerate(c.battle_ui_dropdowns):
					dropdown_group[i] = Dropdown(	pos=pos,
													size=Vec(200,40),
													entries=[''] + game.unit_db.get_list_of_schematic_names(),
													default=0)



		self._refresh_editable_listviews()

	def enter(self):
		pass
	def exit(self):
		pass
	def start_test_battle(self):
		self.save()
		global game
		friendlies = [None]*4
		enemies = [None]*4
		for i,s in enumerate(self.loaded_schematic.friendlies):
			if s != None:
				friendlies[i] = s.generate_unit(team=0, slot=i)
		for i,s in enumerate(self.loaded_schematic.enemies):
			if s != None:
				enemies[i] = s.generate_unit(team=1, slot=i)

		game.enter_state(BattleState(friendly_units=friendlies, enemy_units=enemies))

	def save(self):
		global game
		if self.active_editable_type == EditableType.Unit:
			# Save new text/number values into the loaded schematic
			schematic = self.loaded_schematic
			schematic.name = self.active_property_ui_group[c.unit_ui_indices['name']].text
			schematic.description = self.active_property_ui_group[c.unit_ui_indices['description']].text
			schematic.traits[T.Vigor] = int(self.active_property_ui_group[c.unit_ui_indices['vigor']].text)
			schematic.traits[T.Armor] = int(self.active_property_ui_group[c.unit_ui_indices['armor']].text)
			schematic.traits[T.Focus] = int(self.active_property_ui_group[c.unit_ui_indices['focus']].text)

			# Save new skills (dropdown menus) into the loaded unit schematic
			for i, dropdown in enumerate(self.dropdowns[EditableType.Unit]):
				if dropdown.selected_entry != '':
					schematic.skill_schematics[i] = game.skill_db.get_schematic_by_name(name=dropdown.selected_entry)
				else:
					schematic.skill_schematics[i] = None
		elif self.active_editable_type == EditableType.Skill:
			schematic = self.loaded_schematic

			# Save values from textboxes
			schematic.name = self.active_property_ui_group[c.skill_ui_indices['name']].text
			schematic.required[T.Vigor] = int(self.active_property_ui_group[c.skill_ui_indices['vigor requirement']].text)
			schematic.required[T.Armor] = int(self.active_property_ui_group[c.skill_ui_indices['armor requirement']].text)
			schematic.required[T.Focus] = int(self.active_property_ui_group[c.skill_ui_indices['focus requirement']].text)

			# Save values from dropdowns
			target_set_string = self.dropdowns[EditableType.Skill][0].selected_entry
		elif self.active_editable_type == EditableType.Battle:
			schematic = self.loaded_schematic

			# Save unit schematics from dropdowns
			for i,d in enumerate(self.dropdowns[EditableType.Battle][:4]):
				self.loaded_schematic.friendlies[i] = game.unit_db.get_schematic_by_name(d.selected_entry)
			for i,d in enumerate(self.dropdowns[EditableType.Battle][4:8]):
				self.loaded_schematic.enemies[i] = game.unit_db.get_schematic_by_name(d.selected_entry)

		self._refresh_editable_listviews()

	def _refresh_editable_listviews(self):
		selected_index = self.editable_type_listview.selected_index
		if selected_index == 0:
			# Unit
			self.entry_listview.entries = game.unit_db.get_list_of_schematic_names()
		if selected_index == 1:
			# Skill
			self.entry_listview.entries = game.skill_db.get_list_of_schematic_names()
		if selected_index == 2:
			# Battle
			self.entry_listview.entries = [str(i) for i,_ in enumerate(game.battle_db.battles)]
	def _refresh_property_ui_elements(self):
		pass
	@property
	def active_editable_type(self):
		return EditableType(self.editable_type_listview.selected_index)
	@property
	def active_property_ui_group(self):
		if self.editable_type_listview.selected_index != None:
			return self.property_ui_elements[self.active_editable_type]
		else:
			return []

	def update(self, game):
		if self.editable_type_listview.update(game=game):
			# Editable TYPE was chosen [e.g., unit/skill/battle]
			self.loaded_schematic = None
			self.entry_listview.selected_index = None
			self._refresh_editable_listviews()
			for e in self.active_property_ui_group:
				e.reset_focus_state()
				e.text = ''
		if self.entry_listview.update(game=game):
			# A new unit was chosen [e.g., Warrior/Rogue/Wolf]
			if self.active_editable_type == EditableType.Unit:
				self.loaded_schematic = game.unit_db.get_schematic_by_name(self.entry_listview.selected_entry)
				self.active_property_ui_group[c.unit_ui_indices['name']].text = self.loaded_schematic.name
				self.active_property_ui_group[c.unit_ui_indices['description']].text = self.loaded_schematic.description
				self.active_property_ui_group[c.unit_ui_indices['vigor']].text = str(self.loaded_schematic.traits[T.Vigor])
				self.active_property_ui_group[c.unit_ui_indices['armor']].text = str(self.loaded_schematic.traits[T.Armor])
				self.active_property_ui_group[c.unit_ui_indices['focus']].text = str(self.loaded_schematic.traits[T.Focus])

				for d in self.dropdowns[EditableType.Unit]:
					d.selected_index = None

				for i, schematic in enumerate(self.loaded_schematic.skill_schematics):
					dropdown = self.dropdowns[EditableType.Unit][i]
					dropdown.entries = [''] + game.skill_db.get_list_of_schematic_names()
					if schematic != None:
						dropdown.select_entry_by_name(name=schematic.name)
					else:
						dropdown.select_entry_by_name(name='')

			if self.active_editable_type == EditableType.Skill:
				self.loaded_schematic = game.skill_db.get_schematic_by_name(self.entry_listview.selected_entry)
				self.active_property_ui_group[c.skill_ui_indices['name']].text = self.loaded_schematic.name
				self.active_property_ui_group[c.skill_ui_indices['vigor requirement']].text = str(self.loaded_schematic.required[T.Vigor])
				self.active_property_ui_group[c.skill_ui_indices['armor requirement']].text = str(self.loaded_schematic.required[T.Armor])
				self.active_property_ui_group[c.skill_ui_indices['focus requirement']].text = str(self.loaded_schematic.required[T.Focus])
			if self.active_editable_type == EditableType.Battle:
				self.loaded_schematic = game.battle_db.battles[int(self.entry_listview.selected_entry)]

				# print(self.dropdowns[EditableType.Battle])
				# print(self.dropdowns[EditableType.Battle][:4])
				# print(self.dropdowns[EditableType.Battle][4:8])

				for i,d in enumerate(self.dropdowns[EditableType.Battle][:4]):
					d.entries = [''] + game.unit_db.get_list_of_schematic_names()
					schematic = self.loaded_schematic.friendlies[i]
					if schematic != None:
						d.select_entry_by_name(name=schematic.name)
				for i,d in enumerate(self.dropdowns[EditableType.Battle][4:8]):
					d.entries = [''] + game.unit_db.get_list_of_schematic_names()
					schematic = self.loaded_schematic.enemies[i]
					if schematic != None:
						d.select_entry_by_name(name=schematic.name)


			for e in self.active_property_ui_group:
				e.reset_focus_state()

			self.focused_index = None

		if self.loaded_schematic != None:
			for i, e in enumerate(self.active_property_ui_group):
				new_focus_state = e.update(game=game)
				if new_focus_state == True:
					if self.focused_index != None and self.focused_index != i:
						self.active_property_ui_group[self.focused_index].unfocus()

					self.focused_index = i
				elif new_focus_state == False:
					self.focused_index = None

			for e in self.dropdowns[self.active_editable_type]:
				if e != None:
					e.update(game=game)

			self.save_button.update(game=game)

			if self.active_editable_type == EditableType.Battle:
				self.test_battle_button.update(game=game)

			for i, s in enumerate(self.property_label_text_surfaces[self.active_editable_type]):
				game.queue_surface(	surface=s,
									pos=self.active_property_ui_group[i].rect.center_left - Vec(20,0),
									x_align=AlignX.Right,
									y_align=AlignY.Center,
									depth=10)

		game.queue_drawline(start=Vec(300,0),
							end=Vec(300,screen_height),
							color=c.dkgrey,
							width=1,
							depth=50)

		game.queue_surface(surface=pointer_cursor_surface, depth=-100, pos=game.mouse_pos)
	def draw(self, game):
		pass
	def mouse_button_pressed(self, game, button, mouse_pos):
		pass
	def key_pressed(self, game, key, mod, translated):
		if self.focused_index != None:
			self.active_property_ui_group[self.focused_index].key_pressed(game=game, key=key, mod=mod, translated=translated)
		if key == pg.K_TAB and len(self.active_property_ui_group) > 0:
			if (mod & pg.KMOD_SHIFT):
				# Shift-tab
				if self.focused_index == None:
					self.focused_index = last_index(self.active_property_ui_group)
				else:
					self.active_property_ui_group[self.focused_index].unfocus()

					self.focused_index -= 1
					if self.focused_index < 0:
						self.focused_index = last_index(self.active_property_ui_group)
			else:
				if self.focused_index == None:
					self.focused_index = 0
				else:
					self.active_property_ui_group[self.focused_index].unfocus()

					self.focused_index += 1
					if self.focused_index > last_index(self.active_property_ui_group):
						self.focused_index = 0

			self.active_property_ui_group[self.focused_index].focus()
			self.active_property_ui_group[self.focused_index].highlight_all()

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
	def mouse_button_pressed(self, game, button, mouse_pos):
		pass
	def enter(self):
		pass
	def exit(self):
		pass

class BattleState:
	def __init__(self, friendly_units, enemy_units):
		#self.turn = Turn(initial_active=True)
		self.is_player_turn = True
		self.active_subturn_slot = 0 # The slot which has the enemy currently doing its own subturn
		# skill_state represents what skill the play is currently doing (after clicking a card, it might be "targeting")
		self.skill_state = "Skill Select"
		self.target_start_pos = Vec(0,0)
		#self.selected_skill = None
		self.selected_skill_button = None

		# self.friendlies = []
		# self.enemies = []

		# Set up warrior and put in slot 0, usw.
		self.friendly_slots = friendly_units
		self.enemy_slots = enemy_units

		self.selected_targets = []

		# warrior_unit = game.unit_db.generate_unit(name="Warrior", team=0, slot=0)
		# rogue_unit = game.unit_db.generate_unit(name="Rogue", team=0, slot=1)
		# self.friendlies.append(warrior_unit)
		# self.friendlies.append(rogue_unit)

		# wolf_unit = game.unit_db.generate_unit(name="Wolf", team=1, slot=0)
		# wolf2_unit = game.unit_db.generate_unit(name="Wolf", team=1, slot=1)
		# human_unit = game.unit_db.generate_unit(name="Human", team=1, slot=2)
		# human2_unit = game.unit_db.generate_unit(name="Human", team=1, slot=3)
		# self.enemies.append(wolf_unit)
		# self.enemies.append(wolf2_unit)
		# self.enemies.append(human_unit)
		# self.enemies.append(human2_unit)
	@property
	def friendlies(self):
		'''Return a list of all friendly units (ignores empty slots)'''
		return [e for e in self.friendly_slots if e != None]
	@property
	def enemies(self):
		'''Return a list of all enemy units (ignores empty slots)'''
		return [e for e in self.enemy_slots if e != None]


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
			self.enemies[self.active_subturn_slot].start_random_skill(allies=self.enemies, enemies=self.friendlies)
		else:
			# Perform cleanup associated with ending ENEMY turn
			# and starting player turn
			self.is_player_turn = True
			for f in self.friendlies:
				f.skill_points = 1



	def update(self, game):
		if self.is_player_turn:
			# End turn if player presses Q
			if game.input.pressed(key=pg.K_q):
				self.end_turn()
			# End turn if skill points are at 0 for all allies
			if len([e for e in self.friendlies if e.skill_points > 0]) == 0:
				self.end_turn()
			# Handle left mouse button press
			# 	* Select the hovered skill if no skill is selected
			# 	* Select the hovered target if an skill has already been selected
			if game.input.pressed(button=0):
				if self.skill_state == "Skill Select":
					for friendly in self.friendlies:
						if friendly.skill_points > 0:
							for button in friendly.skill_buttons:
								if button.check_hover(mouse_pos=game.mouse_pos) == True:
									self.skill_state = "Target Select"
									self.selected_skill_button = button

				elif self.skill_state == "Target Select":
					skill = self.selected_skill_button.linked_skill
					owner = self.selected_skill_button.linked_skill.owner
					valid_targets = self.get_valid_targets(source_unit=owner, target_set=skill.target_set)

					for target in valid_targets:
						if target.alive is False:
							continue
						if slot_intersect(pos=game.mouse_pos, team=target.team, slot=target.slot):
							if skill.target_set in [TargetSet.Self, TargetSet.SingleAlly, TargetSet.OtherAlly, TargetSet.SingleEnemy]:
								targets = [targeted]
							else:
								targets = valid_targets

							self.selected_targets.append(targets)
							if len(self.selected_targets) == len(skill.effect_groups):
								# All targets have been chosen
								skill.apply_effects(target_groups = self.selected_targets)
							break

					self.skill_state = "Skill Select"

			# Handle right mouse button press
			#	* If an skill has been selected, deselect it so another one can be selected.
			if game.input.pressed(button=2):
				if self.skill_state == "Target Select":
					self.skill_state = "Skill Select"
		else: # (if it is NOT the player's turn)
			if self.enemies[self.active_subturn_slot].skill_finished == True:
				self.active_subturn_slot += 1
				if self.active_subturn_slot > last_index(self.enemies):
					# All enemies have done their subturns, so it is now the player's turn
					self.end_turn()
				else:
					self.enemies[self.active_subturn_slot].start_random_skill(allies=self.enemies, enemies=self.friendlies)


		for friendly in self.friendlies:
			friendly.update()
		for enemy in self.enemies:
			enemy.update()

		previewed_target_set = []
		if self.skill_state == "Target Select":
			skill = self.selected_skill_button.linked_skill

			# FIX:
			# OPTIMIZE: We only need to update the preview/hover when the mouse moves, or even further optimizing,
			#			it only needs to be updated when the mouse crosses a boundary between slots. Right now
			#			we're doing a ton of unnecessary stuff every frame.
			# NOTE: I may not want to optimize this too early, because the targeting system
			#		may change.

			# TODO: This could be unsafe. It assumes that when the last target is selected everything
			#		gets reset properly. If not, the index to skill.effects will be too large
			#		also: pretty sure skills with empty effects lists will throw exception here too
			next_target_set = skill.effect_groups[len(self.selected_targets)][0]
			if next_target_set == TargetSet.All:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies+self.enemies # All
						break
				if previewed_target_set == []: # If we found something in friendlies, we don't need to check enemies
					for enemy in self.enemies:
						if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
							previewed_target_set = self.friendlies+self.enemies # All
			elif next_target_set == TargetSet.AllEnemies:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
						previewed_target_set = self.enemies
						break
			elif next_target_set == TargetSet.AllAllies:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = self.friendlies
						break
			elif next_target_set == TargetSet.SingleEnemy:
				for enemy in self.enemies:
					if enemy.alive == True and enemy_slot_intersect(pos=game.mouse_pos, slot=enemy.slot):
						previewed_target_set = [enemy]
						break
			elif next_target_set == TargetSet.SingleAlly:
				for friendly in self.friendlies:
					if friendly.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=friendly.slot):
						previewed_target_set = [friendly]
						break
			elif next_target_set == TargetSet.Self:
				if skill.owner.alive == True and friendly_slot_intersect(pos=game.mouse_pos, slot=skill.owner.slot):
					previewed_target_set = [skill.owner]

		# Draw friendlies
		for friendly in self.friendlies:
			if friendly in previewed_target_set and self.skill_state == "Target Select":
				friendly.draw(target=game.screen, mouse_pos=game.mouse_pos, preview_skill=skill)
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
					if friendly.skill_points == 0:
						highlight_surface.fill(c.red)
					else:
						highlight_surface.fill(c.green)

					game.queue_surface(	surface=highlight_surface,
										pos=Vec(friendly_slot_positions[friendly.slot], 0),
										depth=100)

				# if self.skill_state == "Target Select":
				# 	preview_skill = self.selected_skill_button.linked_skill
				# else:
				# 	preview_skill = None

				friendly.draw(target=game.screen, mouse_pos=game.mouse_pos)

		# Draw enemies
		for enemy in self.enemies:
			if enemy.alive == False:
				continue
			if enemy in previewed_target_set and self.skill_state == "Target Select":
				enemy.draw(target=game.screen, mouse_pos=game.mouse_pos, preview_skill=skill)
				highlight_surface = Surface(Vec(200,screen_height))
				highlight_surface.set_alpha(30)
				highlight_surface.fill(c.white)
				game.queue_surface(	surface=highlight_surface,
									pos=Vec(enemy_slot_positions[enemy.slot], 0),
									depth=-1)
			else:
				enemy.draw(target=game.screen, mouse_pos=game.mouse_pos)

		if self.skill_state == "Target Select":
			# Targeting line/arrow
			# width = abs(game.mouse_pos.x - self.selected_skill_button.rect.center_right.x)
			# height = abs(game.mouse_pos.y - self.selected_skill_button.rect.center_right.y)
			game.queue_drawline(start=self.selected_skill_button.rect.center_right,
								end=game.mouse_pos,
								color=c.white,
								depth=-10)
			# surface = Surface(size=Vec(screen_width, screen_height))
			# surface.set_colorkey(c.pink)
			# surface.fill(c.pink)
			# draw_line(	target=surface,
			# 			color=c.white,
			# 			start=self.selected_skill_button.rect.center_right,
			# 			end=game.mouse_pos)

			# game.queue_surface(surface=surface, depth=-10, pos=Vec(0,0))
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
	def enter(self, friendly_units, enemy_units):
		if self.room_type == RoomType.Battle:

			return BattleState(	friendly_units=friendly_units,
								enemy_units=enemy_units)
		elif self.room_type == RoomType.Shop:
			return ShopState()

class CampaignState:
	def __init__(self, game):
		self.game = game

		self.rooms = [Room(room_type=RoomType.Battle) for i in range(4)]
		self.rooms.append(Room(room_type=RoomType.Shop))

		# The units currently in the player's party
		# 4 slots
		self.player_units = [None]*4

		for i, schematic in enumerate(game.starting_party):
			self.add_unit_to_party(schematic=schematic, slot=i)
	def add_unit_to_party(self, schematic, slot):
		if slot >= 0 and slot < 4:
			# If the slot given is a valid slot number
			self.player_units[slot] = schematic.generate_unit(team=0, slot=slot)

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

		self.game.queue_drawtext(	text="Party",
									font=main_font_10_u,
									color=c.ltgrey,
									pos=Vec(900, 150),
									depth=0)

		for i, unit in enumerate(self.player_units):
			if unit == None:
				continue
			self.game.queue_drawtext(	text=unit.name,
										font=main_font_7,
										color=c.white,
										pos=Vec(900, 200+i*50),
										depth=0)

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
					enemy_units = game.battle_db.get_random_battle_units()
					game.enter_state(room.enter(friendly_units=self.player_units,
												enemy_units=enemy_units))


	def key_pressed(self, game, key, mod, translated):
		pass

class BattleSchematic:
	def __init__(self, friendlies=[None]*4, enemies=[None]*4):
		self.friendlies = friendlies
		self.enemies = enemies
		assert(len(self.friendlies) == 4)
		assert(len(self.enemies) == 4)

class BattleSchematicDatabase:
	def __init__(self, battle_data, unit_db):
		self.battles = []

		with open(battle_data) as f:
			for line in f:
				match = re.search('^\[(.*)\,(.*)\,(.*)\,(.*)\,(.*)\,(.*)\,(.*)\,(.*)\]', line.rstrip())
				if match:
					b = BattleSchematic(friendlies=[unit_db.get_schematic_by_name(match.group(i)) for i in range(1,5)],
										enemies=[unit_db.get_schematic_by_name(match.group(i)) for i in range(5,9)])

					self.battles.append(b)
				else:
					error.log("Invalid line found while loading battles from {}".format(battle_data))

	def get_random_battle_units(self):
		battle = random.choice(self.battles)
		return [unit_schematic.generate_unit(team=1, slot=i) for i,unit_schematic in enumerate(battle.enemies) if unit_schematic != None]

class Game:
	def __init__(self):
		global game
		game = self

		pg.init()
		self.screen = Surface.from_pgsurface(pg.display.set_mode((screen_width, screen_height)))
		pg.mouse.set_visible(False)
		#pg.key.set_repeat(250, 32)


		self.skill_db = SkillSchematicDatabase(skill_data_filepath="skills.dat")
		self.unit_db = UnitSchematicDatabase(unit_data="units.dat", animation_data="animations.dat")
		self.battle_db = BattleSchematicDatabase(battle_data="battles.dat", unit_db=self.unit_db)

		self.starting_party = [
			self.unit_db.get_schematic_by_name(name="Warrior"),
			self.unit_db.get_schematic_by_name(name="Rogue")
		]

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
				self.input.set_repeat_key(event.key)
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
	def queue_surface(self, surface, depth, pos, x_align=AlignX.Left, y_align=AlignY.Up):
		self.draw_queue.append(	(depth,
								 lambda: draw_surface(	target=self.screen,
														surface=surface,
														pos=pos,
														x_align=x_align,
														y_align=y_align)))
		#self.draw_queue.append((depth, surface, pos))
	def start_animation(self, animation, pos, owner):
		self.active_animations.append({ 'animation': deepcopy(animation),
										'pos': pos,
										'owner': owner})
	def start_campaign(self):
		self.enter_state(CampaignState(game=self))
	def start_editor(self):
		self.enter_state(EditorState())

def main():
	game = Game()
	while True:
		game.update(df=1, mouse_pos=(0,0))
main()