from copy import copy, deepcopy
import math
import re

from util import last_index
from harm_draw import draw_surface, Surface
from harm_math import Vec, Rect

class Tween:
	def __init__(self, start_pos=Vec(0,0), end_pos=Vec(0,0), jerk=1.0, duration=1):
		self.start_pos=start_pos
		self.end_pos=end_pos
		self.jerk=jerk
		self.duration = duration
	def pos(self, t):
		x = (1-pow(t,self.jerk))*self.start_pos.x+(pow(t,self.jerk))*self.end_pos.x
		y = (1-pow(t,self.jerk))*self.start_pos.y+(pow(t,self.jerk))*self.end_pos.y
		#if t > 0:
			# if(self.start_pos.x != self.end_pos.x):
			# 	x = math.floor((1-pow(t,self.jerk))*self.start_pos.x + pow(t,self.jerk)*self.end_pos.x)
			# if(self.start_pos.y != self.end_pos.y):
			# 	y = math.floor((1-pow(t,self.jerk))*self.start_pos.y + pow(t,self.jerk)*self.end_pos.y)

		return Vec(x,y)

class Animation:
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
		self._sprites = sprites # All sprites used in the animation
		self._frames = [] # Concurrent array with _sprites; which sprite to use on each frame
		self._tweens = tweens
		self._tween_start_frames = [] # Concurrent to _tweens; the starting frame of each tween
		self._cur_tween_index = 0
		self.anchor_points = anchor_points # Concurrent array with _sprites; corresponding anchor points
		self.loop = loop # TODO: Implement loop

		# for sprite in sprites:
		# 	self._sprites.append(sprite.copy())
		for i, sprite_length in enumerate(sprite_lengths):
			self._frames += [i]*sprite_length

		running_frame_count = 0
		for i, tween in enumerate(self._tweens):
			self._tween_start_frames.append(running_frame_count)
			running_frame_count += tween.duration
	@classmethod			
	def from_string(cls, s):
		name_of_owner = "<NO OWNER NAME>"
		name_of_action = "<NO ACTION NAME>"
		duration = 1
		_sprites = []
		sprite_lengths = []
		_tweens = []
		anchor_points = []
		loop = False

		#Warrior's Rest
		# 	duration is 60
		# 	has tween
		# 		duration is 60
		# 		starts at (0,0)
		# 		ends at (0,0)
		# 		jerk is 1.0
		# 	has sub-animation
		# 		duration is 60
		# 		sprite is "WarriorIdle.png"
		# 		anchor is bottom left

		cur_tween = None
		in_sub_animation = False
		cur_sub_index = 0

		for line in s.splitlines():

			# Match possessive unit name with action name
			# ex: Warrior's Strike
			match = re.search('^([a-zA-Z]*)\'s (.*)', line.rstrip())
			if match:
				name_of_owner = match.group(1)
				name_of_action = match.group(2)
				continue

			# Match duration of animation
			line_match = re.search('^\tduration is (-*[0-9]+)', line.rstrip())
			if line_match:
				duration = int(line_match.group(1))
				continue
			# Match beginning of tween data
			line_match = re.search('^\thas tween', line.rstrip())
			if line_match:
				cur_tween = Tween()
				if in_sub_animation == True:
					cur_sub_index += 1
					in_sub_animation = False
				continue
			# Match beginning of sub-animation data
			line_match = re.search('^\thas sub-animation', line.rstrip())
			if line_match:
				in_sub_animation = True
				if cur_tween != None:
					_tweens.append(cur_tween)
					cur_tween = None
				continue
			if cur_tween != None:
				# Match duration length of current tween
				line_match = re.search('^\t\tduration is (-*[0-9]+)', line.rstrip())
				if line_match:
					cur_tween.duration = int(line_match[1])
					continue
				# Match start_pos of current tween
				line_match = re.search('^\t\tstarts? (?:at )?\((-*[0-9]+),(-*[0-9]+)\)', line.rstrip())
				if line_match:
					cur_tween.start_pos = Vec(int(line_match[1]), int(line_match[2]))
					continue
				# Match end_pos of current tween
				line_match = re.search('^\t\tends? (?:at )?\((-*[0-9]+),(-*[0-9]+)\)', line.rstrip())
				if line_match:
					cur_tween.end_pos = Vec(int(line_match[1]), int(line_match[2]))
					continue
				# Match jerk of current tween
				line_match = re.search('^\t\tjerk is (-*[0-9]+\.[0-9]+)', line.rstrip())
				if line_match:
					cur_tween.jerk = float(line_match[1])
					continue
			elif in_sub_animation == True:
				# TODO: This is vulnerable to incorrectly formatted animation files,
				# 		because it doesn't check that each sub-animation only has 1
				#		duration, sprite path, anchor
				
				# Match duration of current sub-animation
				line_match = re.search('^\t\tduration is ([0-9]+)', line.rstrip())
				if line_match:
					sprite_lengths.append(int(line_match[1]))
					continue
				# Match sprite (filepath) of current sub-animation
				line_match = re.search('^\t\tsprite is \"(.*)\"', line.rstrip())
				if line_match:
					_sprites.append(Surface.from_file(filepath=line_match[1]))
					continue
				# Match sprite (filepath) of current sub-animation					
				line_match = re.search('^\t\tanchor is (.*)', line.rstrip())
				if line_match:
					if line_match[1] == "bottom left":
						anchor_points.append(Vec(0, _sprites[cur_sub_index].height))
						continue

		new = Animation(	duration=duration,
							sprites=_sprites,
							sprite_lengths=sprite_lengths,
							tweens=_tweens,
							anchor_points=anchor_points,
							loop=loop)

		return new
	def update(self, frame_count=1):
		"""Advance animation frame.
		Return True if animation is finished, False otherwise"""
		self.cur_frame += frame_count

		if self._cur_tween_index != last_index(self._tweens):
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
	@property
	def cur_sprite_index(self):
		return self._frames[min(self.duration-1, self.cur_frame)]
	@property
	def cur_pos(self):
		t = (self.cur_frame - self._tween_start_frames[self._cur_tween_index])/(self.cur_tween.duration) # should it be duration - 1?
		return self.anchor_points[self.cur_sprite_index]-self.cur_tween.pos(t=t)
	def draw(self, game, pos):
		game.queue_surface(	surface=self._sprites[self.cur_sprite_index],
							pos=pos-self.cur_pos,
							depth=100)

		# draw_surface(	target=target,
		# 				pos=pos-self.cur_pos,
		# 				surface=self._sprites[self.cur_sprite_index])
	@property
	def rect(self):
		sprite = self._sprites[self.cur_sprite_index]
		size = Vec(sprite.get_width(), sprite.get_height())
		return Rect(pos=self.cur_pos, size=size)
	# def __deepcopy__(self, memo):
	# 	other = Animation(	duration=self.duration,
	# 						tweens=self._tweens,
	# 						anchor_points=self.anchor_points,
	# 						loop=self.loop)

	# 	other._sprites = deepcopy(self._sprites)
	# 	other._frames = copy(self._frames)
	# 	other._tween_start_frames = copy(self._tween_start_frames)

	# 	return othe