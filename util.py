class Vec2f:
	def __init__(self, x=None, y=None, tuple=None, vec2f=None):
		if x is not None and y is not None:
			self.components = (float(x), float(y))
		elif tuple is not None:
			self.components = (float(tuple[0]), float(tuple[1]))
		elif vec2f is not None:
			self.components = (vec2f.x, vec2f.y)
		else:
			self.components = (0.0, 0.0)

	@property
	def x(self):
		return self.components[0]

	@x.setter
	def x(self, value):
		self.components = tuple(float(value), self.y)

	@property
	def y(self):
		return self.components[1]

	@y.setter
	def y(self, value):
		self.components = tuple(self.x, float(value))

	@property
	def length(self):
		return (self.x**2 + self.y**2)**0.5

	@property
	def dir(self):
		"""Returns a normalized Vec2f pointing in the same direction as this vector"""
		return (1.0/self.length) * self

	def __add__(self, other):
		assert isinstance(other, Vec2f) is True, f"Tried to add an invalid object (type={type(other)}) to Vec2f."
		return Vec2f(x=self.x+other.x, y=self.y+other.y)

	def __sub__(self, other):
		assert isinstance(other, Vec2f) is True, f"Tried to add an invalid object (type={type(other)}) to Vec2f."
		return Vec2f(x=self.x-other.x, y=self.y-other.y)

	def __rmul__(self, scalar):
		return Vec2f(x=float(scalar*self.x), y=float(scalar*self.y))

	def __mul__(self, scalar):
		return Vec2f(x=float(scalar*self.x), y=float(scalar*self.y))

	def __neg__(self):
		return Vec2f(x=-self.x, y=-self.y)

	def __str__(self):
		return f"Vec2i({self.x}, {self.y})"

	def as_tuple(self):
		return self.components

	def rounded(self):
		"""Returns a Vec2i which has components equal to this vector's components, but rounded to the nearest integer"""
		return Vec2i(self.x, self.y)

class Vec2i:
	def __init__(self, x=None, y=None, tuple=None, Vec2i=None):
		if x is not None and y is not None:
			self.components = (round(x), round(y))
		elif tuple is not None:
			self.components = (round(tuple[0]), round(tuple[1]))
		elif vec2f is not None:
			self.components = (vec2i.x, vec2i.y)
		else:
			self.components = (0,0)

	@property
	def x(self):
		return self.components[0]

	@x.setter
	def x(self, value):
		self.components = tuple(round(value), self.y)

	@property
	def y(self):
		return self.components[1]

	@property
	def length(self):
		return (self.x**2 + self.y**2)**0.5

	@property
	def dir(self):
		"""Returns a normalized Vec2f pointing in the same direction as this vector"""
		f_self = Vec2f(self.x, self.y)
		return (1.0/self.length)*f_self

	@y.setter
	def y(self, value):
		self.components = tuple(self.x, round(value))

	def __add__(self, other):
		assert isinstance(other, Vec2i) is True, f"Tried to add an invalid object (type={type(other)}) to Vec2i."
		return Vec2i(x=self.x+other.x, y=self.y+other.y)

	def __sub__(self, other):
		assert isinstance(other, Vec2i) is True, f"Tried to add an invalid object (type={type(other)}) to Vec2i."
		return Vec2i(x=self.x-other.x, y=self.y-other.y)

	def __rmul__(self, scalar):
		return Vec2i(x=round(scalar*self.x), y=round(scalar*self.y))

	def __mul__(self, scalar):
		return Vec2i(x=round(scalar*self.x), y=round(scalar*self.y))

	def __neg__(self):
		return Vec2i(x=-self.x, y=-self.y)

	def __str__(self):
		return f"Vec2i({self.x}, {self.y})"

	def as_tuple(self):
		return self.components

	def float(self):
		return Vec2f(self.x, self.y)

def in_range(number, low, high):
	if number >= low and number < high:
		return True
	else:
		return False

def last_index(container):
	"""For lists and tuples, return the last valid index"""
	if isinstance(container, (list,tuple)):
		return len(container)-1
	else:
		print('Tried to get last_index of invalid container type.')
		raise TypeError()

def is_positive_index(container, index):
	if isinstance(container, (list,tuple)):
		if in_range(index, 0, len(container)):
			return True
		else:
			return False
	else:
		print('Tried is_positive_index for invalid container type.')
		raise TypeError()

def key_pressed(key, p_keys, keys):
	if p_keys[key] == False and keys[key] == True:
		return True
	else:
		return False

def key_down(key, keys):
	return keys[key]

class InputState:
	def __init__(self, p_keys, keys, p_buttons, buttons, keypress_delay_interval=30, keypress_repeat_interval=10):
		self.p_keys = p_keys
		self.keys = keys
		self.p_buttons = p_buttons
		self.buttons = buttons

		self.repeat_key = None
		self.delay_tick = -1 # positive if in delay mode, -1 otherwise
		self.repeat_tick = -1 # positive if in repeat mode, -1 otherwise
		self.keypress_delay_interval = keypress_delay_interval
		self.keypress_repeat_interval = keypress_repeat_interval
	def next_state(self, new_keys, new_buttons):
		self.p_keys = self.keys
		self.p_buttons = self.buttons

		self.keys = new_keys
		self.buttons = new_buttons
	def set_repeat_key(self, key):
		self.repeat_key = key
		self.delay_tick = 0
		self.repeat_tick = -1
	def unset_repeat_key(self, key):
		""" If the given key is the repeat_key, unset it"""
		if self.repeat_key == key:
			self.repeat_key = None
			self.repeat_tick = -1
	def update(self, df=1):
		if self.delay_tick >= 0:
			# We're in delay mode
			self.delay_tick += 1
			if self.delay_tick >= self.keypress_delay_interval:
				# If delay period has elapsed, switch into repeat mode
				self.delay_tick = -1
				self.repeat_tick = self.keypress_repeat_interval # First press should happen at end of delay interval, not delay+repeat interval.

		if self.repeat_tick >= 0:
			# We're in repeat mode
			self.repeat_tick += df
	def down(self, key=None, button=None):
		if key != None:
			return self.keys[key]
		elif button != None:
			return self.buttons[button]
		else:
			return False
	def pressed(self, key=None, button=None, mod=None):
		if key != None:
			if self.p_keys == None:
				# First frame is indeterminate because there's no data from previous frame,
				# so just assume no keys have been pressed.
				return False

			if self.repeat_key == key and self.repeat_tick >= self.keypress_repeat_interval:
				if mod is None:
					self.repeat_tick = 0
					return True
				else:
					if self.keys[mod] == True:
						self.repeat_tick = 0
						return True
			if self.p_keys[key] == False and self.keys[key] == True:
				if mod is None:
					return True
				else:
					if self.keys[mod] == True:
						return True
			else:
				return False
		elif button != None:
			if self.p_buttons == None:
				# First frame is indeterminate because there's no data from previous frame,
				# so just assume no buttons have been pressed.
				return False
			if self.p_buttons[button] == False and self.buttons[button] == True:
				if mod is None:
					return True
				else:
					if self.keys[mod] == True:
						return True

	def released(self, key=None, button=None):
		if key != None:
			if self.p_keys == None:
				# First frame is indeterminate because there's no data from previous frame,
				# so just assume no keys have been released.
				return False

			if self.p_keys[key] == True and self.keys[key] == False:
				return True
			else:
				return False
		elif button != None:
			if self.p_buttons == None:
				# First frame is indeterminate because there's no data from previous frame,
				# so just assume no buttons have been pressed.
				return False
			if self.p_buttons[button] == True and self.buttons[button] == False:
				return True					


def split_text(text, font, word_wrap_width):
		lines = []

		split_text = text.split(' ')
		current_line = ''
		for i, word in enumerate(split_text):
			if i == 0:
				line_width = font.size(word)[0]
			else:
				line_width = font.size(current_line + ' ' + word)[0]
			if line_width >= word_wrap_width:
				lines.append(current_line)
				current_line = word
			else:
				if i == 0:
					current_line += word
				else:
					current_line += ' ' + word

		if len(current_line) > 0:
			lines.append(current_line)

		return lines

def clamp(value, min_value, max_value):
	clamped_value = value
	if value < min_value:
		clamped_value = min_value
	elif value > max_value:
		clamped_value = max_value

	return clamped_value

# Scales color towards (0,0,0), where amount is between 0 and 1 (1 taking it all the way to c.black)
def darken_color(color, amount):
	try:
		new_color = list(color)
		for i, channel in enumerate(new_color):
			new_color[i] = clamp(channel*(1-amount), 0, 255)
		return new_color
	except IndexError:
		print("Failed to darken color.")
		return color

# Scales color towards (0,0,0), where amount is between 0 and 1 (1 takes it all the way to c.white)
def lighten_color(color, amount):
	try:
		new_color = list(color)
		for i, channel in enumerate(new_color):
			new_color[i] = clamp(channel + amount*(255-channel), 0, 255)
		return new_color
	except:
		print("Failed to darken color.")
		return color