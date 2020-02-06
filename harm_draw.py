from enum import Enum
import pygame as pg
from harm_math import Vec, Rect

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



def draw_line(screen, color, start, end, width=1):
	pg.draw.line(screen, color, (start.x, start.y), (end.x, end.y), width)

def draw_rect(screen, color, pos, size, width=0):
	pg.draw.rect(screen, color, pg.Rect(int(pos.x), int(pos.y), int(size.x), int(size.y)), width)
	return Rect(pos, size)

def draw_text(screen, color, pos, text, font, x_center=True, y_center=True):
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