from enum import Enum
import pygame as pg
from harm_math import Vec, Rect
import constants as c
import util

# Wrapped pygame surface that implements __copy__ and __deepcopy__
class Surface:
	def __init__(self, size):
		self._pg_surface = pg.Surface(size.tuple)
	@classmethod
	def from_pgsurface(cls, pg_surface):
		new = Surface(size=Vec(0,0))
		new._pg_surface = pg_surface
		return new		
	@classmethod
	def from_file(cls, filename):
		file_surface = pg.image.load(filename)
		return cls.from_pgsurface(file_surface)
	def set_colorkey(self, color):
		self._pg_surface.set_colorkey(color)
	def fill(self, color):
		self._pg_surface.fill(color)
	def set_alpha(self, value):
		self._pg_surface.set_alpha(value)
	@property
	def width(self):
		return self._pg_surface.get_width()
	@property
	def height(self):
		return self._pg_surface.get_height()
	@property
	def size(self):
		return Vec(self.width, self.height)
	def __copy__(self):
		other = Surface(size=self.size)
		other._pg_surface = self._pg_surface.copy()
		return other
	def __deepcopy__(self, memo):
		other = Surface(size=self.size)
		other._pg_surface = self._pg_surface.copy()
		return other		

class AlignX(Enum):
	Left = 0
	Center = 1
	Right = 2

class AlignY(Enum):
	Up = 0
	Center = 1
	Down = 2

def darken_color(color, amount):
	return (int(color[0]*(1-amount)), int(color[1]*(1-amount)), int(color[2]*(1-amount)))



def draw_line(target, color, start, end, width=1):
	pg.draw.line(target._pg_surface, color, (start.x, start.y), (end.x, end.y), width)

def draw_rect(target, color, pos, size, width=0):
	pg.draw.rect(target._pg_surface, color, pg.Rect(int(pos.x), int(pos.y), int(size.x), int(size.y)), width)
	return Rect(pos, size)

def draw_text(target, color, pos, text, font, x_center=True, y_center=True):
	text_pg_surface = font.render(text, True, color)
	text_surface = Surface.from_pgsurface(text_pg_surface)

	width, height = text_surface.size
	if x_center is True:
		x = pos.x - width/2
	else:
		x = pos.x
	if y_center is True:
		y = pos.y - height/2
	else:
		y = pos.y
	
	draw_surface(target=target, surface=text_surface, pos=Vec(x,y))

	return Rect(Vec(x,y), text_surface.size)

def draw_text_wrapped(target, text, pos, font, color=c.white, word_wrap_width=None):
	if len(text) == 0:
		line_count = 0

	line_spacing = font.get_linesize()
	lines = util.split_text(text, font, word_wrap_width=word_wrap_width)
	line_count = len(lines)
	text_surface = Surface(Vec(word_wrap_width, line_spacing*line_count))
	text_surface.set_colorkey(c.black)
	text_surface.fill(c.black)

	for line_number, line in enumerate(lines):

		draw_surface(	target=text_surface, 
						surface=Surface.from_pgsurface(font.render(line, True, color)),
						pos=Vec(0,line_number*line_spacing))

	draw_surface(target=target, surface=text_surface, pos=pos)

	return line_count

def draw_x(target, color, rect, width=5):
	"""Draws an X along the diagonals of the given [rect]"""
	draw_line(target=target, color=color, start=rect.top_left, end=rect.bottom_right, width=width)
	draw_line(target=target, color=color, start=rect.top_right, end=rect.bottom_left, width=width)

def draw_surface(target, surface, pos, x_align=AlignX.Left, y_align=AlignY.Up):
	aligned_pos = Vec(pos.x, pos.y)

	if x_align == AlignX.Center:
		aligned_pos.x -= surface.width/2
	elif x_align == AlignX.Right:
		aligned_pos.x -= surface.width

	if y_align == AlignY.Center:
		aligned_pos.y -= surface.height/2
	if y_align == AlignY.Down:
		aligned_pos.y -= surface.height

	target._pg_surface.blit(surface._pg_surface,
							aligned_pos.tuple)

	# Return extent of drawn surface
	size = Vec(surface.width, surface.height)
	return Rect(aligned_pos, size)