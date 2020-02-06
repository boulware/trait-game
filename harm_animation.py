from copy import copy, deepcopy
import math

from harm_draw import draw_surface
from harm_math import Vec, Rect

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
	@property
	def cur_sprite_index(self):
		return self._frames[self.cur_frame]
	

	@property
	def cur_pos(self):
		t = (self.cur_frame - self._tween_start_frames[self._cur_tween_index])/(self.cur_tween.duration) # should it be duration - 1?
		return self.anchor_points[self.cur_sprite_index]-self.cur_tween.pos(t=t)
	

	def draw(self, screen, pos):
		draw_surface(	screen=screen,
						pos=pos-self.cur_pos,
						surface=self._sprites[self.cur_sprite_index])

	@property
	def rect(self):
		sprite = self._sprites[self.cur_sprite_index]
		size = Vec(sprite.get_width(), sprite.get_height())
		return Rect(pos=self.cur_pos, size=size)

	

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