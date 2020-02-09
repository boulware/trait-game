import inspect
import colorama
from colorama import Fore, Back, Style
import traceback
import functools
import copy
import pygame as pg
import constants as c
import time
import UI
import draw
import numpy as np
import json
from util import InputState

from harm_draw import draw_surface
from harm_math import Vec

colorama.init(autoreset=True)

print_callstack = traceback.print_stack
active = False
active_print = True
debugger = None

def info(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		if active_print is True:
			stack = inspect.stack()
			args_repr = [repr(a) for a in args]
			kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
			signature = ", ".join(args_repr + kwargs_repr)

			frame = inspect.stack()[1]
			module = inspect.getmodule(frame[0])
			filename = module.__file__
			print(f"{filename}:{stack[1].lineno}->" + Fore.RED + f"{func.__name__}" + Fore.YELLOW + f"({signature})")
		return func(*args, **kwargs)

	return wrapper

def time_me(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		start_time = time.clock()
		return_value = func(*args, **kwargs)
		end_time = time.clock()
		dt = end_time - start_time
		print(f"{func.__name__}: {dt*pow(10,3):.3f} ms")
		return return_value

	return wrapper

class DebugUI:
	def __init__(self, game, active=False):
		self.game = game
		self.active = active
		self.font = pg.font.Font('font.ttf', 14)
		self.bg_alpha = 100
		self.displayed_strings = []

		self.test_treeview = TreeView(pos=(0,0), font_size=14, parent_node_object=self)
		self.test_treeview.root.load_children() # Required for the treeview itself to show up in the debug list from the beginning

		self._hook_all()

	def __getstate__(self):
		state = self.__dict__.copy()
		state['font'] = "boo"

		return state

	@property
	def active(self):
		return self._active

	@active.setter
	def active(self, value):
		self._active = value
		global active
		active = value

	def _hook_all(self):
		"""Hook into self.game and decorate its methods to enable debugging"""
		self.game.draw = self._draw_hook(hooked_func=self.game.draw)
		self.game.any_key_pressed = self._any_key_pressed_hook(hooked_func=self.game.any_key_pressed)
		self.game.update = self._update_hook(hooked_func=self.game.update)

	def _draw_hook(self, hooked_func):
		@functools.wraps(hooked_func)
		def wrapper(*args, **kwargs):
			hooked_func()
			self.draw()
			pg.display.flip()
		return wrapper

	def _any_key_pressed_hook(self, hooked_func):
		@functools.wraps(hooked_func)
		def wrapper(*args, **kwargs):
			self.any_key_pressed(*args, **kwargs)
			hooked_func(*args, **kwargs)
		return wrapper

	def _update_hook(self, hooked_func):
		@functools.wraps(hooked_func)
		def wrapper(*args, **kwargs):
			hooked_func(*args, **kwargs)
			self.update(*args, **kwargs)
		return wrapper

	def print(self, values):
		for name, value in values.items():
			print(Fore.RED + f"{name}" + Fore.WHITE + f"=" + Fore.YELLOW + f"{repr(value)}")
			try:
				for key,e in vars(value).items():
					print('\t' + Fore.CYAN + f"{key}" + Fore.WHITE + ' = ' + Fore.GREEN + f"{repr(e)}")
			except TypeError:
				pass

		print(Fore.BLUE + "***********")

	def write(self, string):
		self.displayed_strings.append(string)

	def update(self, df, mouse_pos):
		self.displayed_strings = []

	def draw(self):
		if self.active == False: return
		screen = self.game.screen._pg_surface

		if self.bg_alpha > 0:
			bg = pg.Surface(screen.get_size())
			bg.set_alpha(self.bg_alpha)
			pg.draw.rect(bg, c.black, ((0,0),(screen.get_size())))
			screen.blit(bg, (0,0))

		current_y = 0
		for string in self.displayed_strings:
			string_surface = self.font.render(string, True, self.text_color)
			screen.blit(string_surface, (0, current_y))
			current_y += self.font.get_linesize()

		self.test_treeview.parent_node = self.game
		self.test_treeview.draw(target=screen)

		pg.display.flip()
	def any_key_pressed(self, input_state):
		key = input_state # Alias for shorter expressions
		if key.pressed(pg.K_d, pg.K_LCTRL):
			self.active = not self.active

		# Only allow the ctrl+d to enable or disable the debug interface if it's "deactivated"
		if self.active is True:
			self.test_treeview.any_key_pressed(input_state=input_state)
			if key.pressed(pg.K_PLUS, pg.K_LCTRL):
				global active_print
				active_print = not active_print
			elif key.pressed(pg.K_t, pg.K_LCTRL):
				if self.bg_alpha != 255:
					self.bg_alpha = 255
				else:
					self.bg_alpha = 0

class Node:
	def __init__(self, name, value, parent=None, expanded=False):
		self.name = name
		self.value = value
		self.parent = parent
		self.expanded = expanded

		self.children = []

		if parent is not None:
			parent.add_child(self)

	def set_value(self, value):
		self.value = value

		try:
			if isinstance(self.parent.value, (list,dict,np.ndarray)):
				self.parent.value[self.name] = value
			else:
				setattr(self.parent.value, self.name, value)
		except AttributeError as error:
			# Attribute has no setter, so do nothing
			pass
		except TypeError as error:
			# try:
				#print(f'lvl 2 (name={self.parent.name}): {e}')
				# The parent type doesn't support __setitem__ (as indexing), so we assume it's a tuple?
				# I think I'll ducktype all my classes for __getitem__ and __setitem__ to call getattr()/setattr()

				# If the parent is a tuple, we have to go one level above to search for a mutable type (list, dict, obj):
				# Then after we look one level up, if it's still not mutable, we go up a level again, u.s.w

				node = self
				parent = self.parent
				temp_list = list(parent.value)
				temp_list[node.name] = value

				mutable_found = False
				while mutable_found is False:
					node = parent
					parent = node.parent
					try:
						if isinstance(parent.value, (list,dict,np.ndarray,tuple)):
							parent.value[node.name] = tuple(temp_list)
						else:
							setattr(parent.value, node.name, tuple(temp_list))

						mutable_found = True
					except TypeError as error:
						new_temp_list = list(parent.value)
						if isinstance(parent.value, (list,dict,np.ndarray,tuple)):
							new_temp_list[parent.name] = tuple(temp_list)
						else:
							setattr(parent.value, parent.name, tuple(temp_list))
						temp_list = new_temp_list
			# except (TypeError, AttributeError) as error:
			# 	d.print_callstack()
			# 	print(Fore.YELLOW + f"Unable to set attribute \'{node.name}\' on {parent.value}")
			# 	print(Fore.RED + f"{type(parent.value).__name__} may not be ducktyped for __getattr__() or __setattr__()")
			# 	print(Fore.MAGENTA + f"error: {error}")

	def add_child(self, child):
		self.children.append(child)

	def get_indexable_attributes(self):
		# Returns list of attributes accessible by [] ('__getitem__')

		attribute_names = []

		if isinstance(self.value, (tuple,list)):
			for index, _ in enumerate(self.value):
				attribute_names.append(index)
		elif isinstance(self.value, np.ndarray):
			for index, _ in np.ndenumerate(self.value):
				attribute_names.append(index)
		elif isinstance(self.value, dict):
			for key, value in self.value.items():
				attribute_names.append(key)
		else:
			try:
				members = inspect.getmembers(self.value, lambda a:not(inspect.isroutine(a)))
				for member_name, _ in [a for a in members if not(a[0].startswith('__') and a[0].endswith('__'))]:
					attribute_names.append(member_name)
			except TypeError as e:
				attribute_names = []

		return attribute_names

	def load_children(self):
		self.children = []

		attribute_names = self.get_indexable_attributes()

		if len(attribute_names) == 0:
			self.expanded = False

		if isinstance(self.value, (list,dict,np.ndarray,tuple)):
			for name in attribute_names:
				Node(name=name, value=self.value[name], parent=self)
		else:
			for name in attribute_names:
				Node(name=name, value=getattr(self.value, name), parent=self)

	def refresh_children(self):
		if len(self.get_indexable_attributes()) != len(self.children):
			self.load_children()

		if isinstance(self.value, (list,dict,np.ndarray,tuple)):
			for child in self.children:
				child.value = self.value[child.name]
				if child.expanded is True:
					child.refresh_children()
		else:
			for child in self.children:
				child.value = getattr(self.value, child.name)
				if child.expanded is True:
					child.refresh_children()

def generate_node_tree_to_depth(root_node, max_depth, current_depth=0, ID_list=None, root=True):
	if current_depth >= max_depth:
		return []

	if ID_list is None:
		ID_list = [] # Tracks objects that have already been added.

	node_list = [(root_node.name, repr(root_node.value), current_depth, id(root_node.value))]

	if isinstance(root_node.value, (bool,int,float,str)):
		# Only expand this child if it's not one of these default types. Their repr() usually has enough info.
		return node_list

	ID_exists = False
	for ID in ID_list:
		if ID == id(root_node.value):
			ID_exists = True

	if ID_exists is True:
		# If this object's already been expanded, just show it's repr(), but don't expand it again
		return node_list
	else:
		ID_list.append(id(root_node.value))

	root_node.load_children()
	for child in root_node.children:
		#node_list.append((child.name, child.value, current_depth))
		node_list += generate_node_tree_to_depth(root_node=child, max_depth=max_depth, current_depth=current_depth+1, ID_list=ID_list, root=False)

	return node_list



class TreeView(UI.Element):
	def __init__(	self,
					pos, font_size=14,
					parent_node_object=dict(),
					parent_container=None):
		UI.Element.__init__(self=self, parent_container=parent_container)
		self.pos = pos
		self.font = None
		self.font_size = font_size

		self.text_color = c.white
		self.no_setter_text_color = c.grey
		self.active_node_color = (150,50,50)
		self.max_string_length = 80

		self.parent_node_object = parent_node_object # Parent object, from which all branches stem
		self.root = Node(name=type(parent_node_object).__name__, value=parent_node_object, expanded=True)
		self.default_root = self.root
		#self.root.load_children()
		self.selected_node = self.root
		self.pinned_nodes = [] # Nodes to be pinned at the top of the tree view, so you can view/modify them easily

		# Represents the current depth to which each branch (and sub-branch, sub-sub-...) is exploded
		# This may need to keep named references, because the order of properties on an object might change over time? Not sure.
		# Is a simple string list of each displayed item with its corresponding integer depth
		# (contains no actual object references)
		self.current_list = []

	@property
	def font_size(self):
		return self._font_size

	@font_size.setter
	def font_size(self, value):
		self._font_size = value
		self.font = pg.font.Font('font.ttf', value)

	def _recursed_generate_current_list(self, current_node=None, depth=0):
		if current_node is None:
			current_node = self.root
		if depth == 0:
			self.current_list = []
			for node in self.pinned_nodes:
				self.current_list.append((node, -1))
		if current_node not in self.pinned_nodes:
			self.current_list.append((current_node, depth))
			if current_node.expanded is True:
				current_node.refresh_children()
				for child_node in current_node.children:
					self._recursed_generate_current_list(current_node=child_node, depth=depth+1)

	def _generate_current_list(self, current_node=None, depth=0):
		self._recursed_generate_current_list(current_node=current_node, depth=depth)

		selected_in_current_list = False
		# for depth_pair in self.current_list:
		# 	print(depth_pair[0].name)
		# print('***')

		for depth_node in self.current_list:
			node = depth_node[0]
			# print(node.name, self.selected_node.name)
			# print(node, self.selected_node)
			if node == self.selected_node:
				selected_in_current_list = True
				break

		if selected_in_current_list is False:
			if len(self.current_list) > 0:
				self.selected_node = self.current_list[0][0]


	def any_key_pressed(self, input_state):
		key = input_state # Alias for shorter expressions
		multiplier = 1
		if key.down(pg.K_LSHIFT) or key.down(pg.K_RSHIFT):
			multiplier = 10

		# if str(unicode_key).isalnum() or str(unicode_key) == '_':
		# 	if mod == pg.KMOD_LSHIFT or mod == pg.KMOD_RSHIFT:
		# 		search_list = self.current_list[::-1] # Search list backwards (i.e., seek a node upwards from selected node)
		# 	else:
		# 		search_list = self.current_list

		# 	searching = False
		# 	for node, _ in search_list:
		# 		if searching is True:
		# 			if str(node.name)[0].lower() == str(unicode_key).lower():
		# 				self.selected_node = node
		# 				break
		# 		if node == self.selected_node:
		# 			searching = True

		if key.pressed(pg.K_DOWN):
			# Move 1 item down in the list
			for i, depth_pair in enumerate(self.current_list):
				node = depth_pair[0]
				depth = depth_pair[1]
				if node == self.selected_node and i < len(self.current_list)-1:
					self.selected_node = self.current_list[i+1][0]
					break
		elif key.pressed(pg.K_UP):
			# Move 1 item up in the list
			for i, depth_pair in enumerate(self.current_list):
				node = depth_pair[0]
				depth = depth_pair[1]
				if node == self.selected_node and i > 0:
					self.selected_node = self.current_list[i-1][0]
					break
		elif key.pressed(pg.K_RETURN):
			# Expand or unexpand currently selected node
			if self.selected_node is not None:
				self.selected_node.expanded = not self.selected_node.expanded
				self.selected_node.load_children()
		elif key.pressed(pg.K_f, pg.K_LCTRL) or key.pressed(pg.K_f, pg.K_RCTRL):
			# Re-center root of the tree on the currently selected node, only showing it and its children
			self.root = self.selected_node
		elif key.pressed(pg.K_r, pg.K_LCTRL) or key.pressed(pg.K_r, pg.K_RCTRL):
			# Reset root to the default root.
			self.root = self.default_root
			self.root.expanded = False
			self.selected_node = self.root
		elif key.pressed(pg.K_RIGHT):
			# Increase currently selected value, if valid operation
			value = self.selected_node.value
			if type(value) is bool:
				self.selected_node.set_value(True)
			elif type(value) is int:
				# Increase integers by 1 (10 when boosted with SHIFT)
				self.selected_node.set_value(value + (1*multiplier))
			elif type(value) is float:
				# Increase by 1%; 10% when boosted (SHIFT);
				# If it's 0.0, set it to 1.0
				if value == 0.0:
					self.selected_node.set_value(1.0)
				else:
					self.selected_node.set_value(value + value*(0.01*multiplier))
			else:
				print("Tried to increment debug value which is not implemented.")
		elif key.pressed(pg.K_LEFT):
			# Decrease currently selected value, if valid operation
			value = self.selected_node.value
			if type(value) is bool:
				self.selected_node.set_value(False)
			elif type(value) is int:
				# Decrease integers by 1 (10 when boosted with SHIFT)
				self.selected_node.set_value(value - (1*multiplier))
			elif type(value) is float:
				# Decrease by 1%; 10% when boosted (SHIFT)
				# If it's 0.0, set it to -1.0
				if value == 0.0:
					self.selected_node.set_value(-1.0)
				else:
					self.selected_node.set_value(value - value*(0.01*multiplier))
			else:
				print("Tried to increment debug value which is not implemented.")
		elif key.pressed(pg.K_DELETE):
			# Set currently selected node to None (be careful!)
			self.selected_node.set_value(None)
		elif key.pressed(pg.K_0):
			# Set currently selected node to 0
			value = self.selected_node.value
			if type(value) is int:
				self.selected_node.set_value(0)
			if type(value) is float:
				self.selected_node.set_value(0.0)
		elif key.pressed(pg.K_BACKSPACE):
			# Jump selection to parent of currently selected node
			if self.selected_node.parent is not None:
				if self.root == self.selected_node:
					self.root = self.selected_node.parent
				self.selected_node = self.selected_node.parent
				self.selected_node.expanded = True
		elif key.pressed(pg.K_p, pg.K_LCTRL) or key.pressed(pg.K_p, pg.K_RCTRL):
			# Pin currently selected node to the top of the tree (it will be highlighted blue)
			# It will always be visible as long as the tree is visible, until unpinned (same hotkey)
			if self.selected_node not in self.pinned_nodes:
				# Node isn't pinned, so pin it
				current_list_selected_index = None
				for i, depth_pair in enumerate(self.current_list):
					node = depth_pair[0]
					if node == self.selected_node:
						current_list_selected_index = i


				if current_list_selected_index is None:
					print("selected_node isn't in selected_list. something is probably wrong.")
					return

				self.pinned_nodes.append(self.selected_node)
				if len(self.current_list) <= 1:
					# Our newly pinned node is the only node in the tree, so it will stay selected
					pass
				elif current_list_selected_index == len(self.current_list)-1:
					# Our newly pinned node was the LAST node in current_list, so move the selected node to the now last node
					self.selected_node = self.current_list[current_list_selected_index-1][0]
				else:
					self.selected_node = self.current_list[current_list_selected_index-1][0]

			else:
				# Node is already pinned, so remove the pin
				current_list_selected_index = None
				for i, depth_pair in enumerate(self.current_list):
					if depth_pair[0] == self.selected_node:
						current_list_selected_index = i

				if current_list_selected_index is None:
					print("selected_node isn't in selected_list. something is probably wrong.")
					return

				self.pinned_nodes.remove(self.selected_node)

				if current_list_selected_index == len(self.current_list)-1:
					self.selected_node = self.current_list[current_list_selected_index-1][0]
				elif len(self.current_list) > 1:
					self.selected_node = self.current_list[current_list_selected_index+1][0]
				else:
					self.selected_node = None

	def draw(self, target):
		self.current_list = []
		self._generate_current_list()

		for node in self.pinned_nodes:
			if node.parent is not None:
				node.parent.refresh_children()

		for i, depth_pair in enumerate(self.current_list):
			node = depth_pair[0]
			depth = depth_pair[1]

			if depth == -1: # pinned node:
				string = str(node.name) + ' = ' + str(node.value)
			else:
				string = '>>'*depth + str(node.name) + ' = ' + str(node.value)

			max_string_length = self.max_string_length
			if len(string) > max_string_length:
				string = string[:max_string_length] + ' [...] ' + string[-10:]

			string_surface = self.font.render(string, True, self.text_color)

			if node.parent is not None and self.selected_node is not node:
				try:
					attr = getattr(type(node.parent.value), node.name)
					if isinstance(attr, property):
						if attr.fset == None:
							string_surface = self.font.render(string, True, self.no_setter_text_color)
				except (AttributeError, TypeError):
					pass

			if depth == -1:
				pg.draw.rect(target, c.blue, ((self.pos[0], self.pos[1]+self.font.get_linesize()*i),string_surface.get_size()))
				if node == self.selected_node:
					pg.draw.rect(target, self.active_node_color, ((self.pos[0], self.pos[1]+self.font.get_linesize()*i),string_surface.get_size()), 2)
			elif node == self.selected_node:
				pg.draw.rect(target, self.active_node_color, ((self.pos[0], self.pos[1]+self.font.get_linesize()*i),string_surface.get_size()))
			target.blit(string_surface, (self.pos[0], self.pos[1]+self.font.get_linesize()*i))