class Vec:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def __add__(self, other):
		return Vec(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		return Vec(self.x - other.x, self.y - other.y)

	def __truediv__(self, divisor):
		return Vec(self.x / divisor, self.y / divisor)

	def __repr__(self):
		return "<{}, {}>".format(self.x, self.y)

class Rect:
	def __init__(self, pos, size):
		self.pos = pos
		self.size = size
	@property
	def top_left(self):
		return self.pos
	@property
	def top_right(self):
		return self.pos + Vec(self.size.x, 0)
	@property
	def bottom_left(self):
		return self.pos + Vec(0, self.size.y)
	@property
	def bottom_right(self):
		return self.pos + self.size
	@property
	def center(self):
		return self.pos + self.size/2
	@property
	def center_left(self):
		return self.pos + Vec(0, self.size.y/2)
	@property
	def center_right(self):
		return self.pos + Vec(self.size.x, self.size.y/2)
	@property
	def center_top(self):
		return self.pos + Vec(self.size.x/2, 0)
	@property
	def center_bottom(self):
		return self.pos + Vec(self.size.x/2, self.size.y)
	@property
	def left(self):
		return self.pos.x
	@property
	def right(self):
		return self.pos.x + self.size.x
	@property
	def top(self):
		return self.pos.y
	@property
	def bottom(self):
		return self.pos.y + self.size.y

	def intersect(self, point):
		if point.x >= self.left and point.x <= self.right:
			if point.y >= self.top and point.y <= self.bottom:
				return True

		return False