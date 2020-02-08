import re 

def parse_enemy_schematics(filename):
	in_enemy = False
	in_action = False

	cur_name = "[PLACEHOLDER NAME]"
	cur_vigor = 0
	cur_armor = 0
	cur_focus = 0

	with open(file=filename, mode='r') as file:
		for line in file:
			# Match enemy name
			match = re.search('^name is (.*)', line.rstrip())
			if match:
				cur_name = match.group(1)

			# Match enemy trait value
			match = re.search('has ([0-9]*) (.*)', line.rstrip())
			if match:
				trait = match.group(2)
				value = int(match.group(1))
				if trait == 'vigor': cur_vigor = int(value)
				if trait == 'armor': cur_armor = int(value)
				if trait == 'focus': cur_focus = int(value)


	print("{}: [Vigor={}, Armor={}, Focus={}]".format(cur_name, cur_vigor, cur_armor, cur_focus))




parse_enemy_schematics(filename="enemies.dat")