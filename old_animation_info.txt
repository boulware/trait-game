# rest_animation_length = 60
		# rest_sprite_animation = FullAnimation(	#end_pos=Vec(0,30),
		# 										#jerk=1.0,
		# 										#tweens=[Tween(end_pos=Vec(0,30), jerk=1.0, duration=rest_animation_length)]
		# 										duration=rest_animation_length,
		# 										sprites=[character_highlighted_surface],
		# 										sprite_lengths=[rest_animation_length],
		# 										anchor_points=[Vec(0, character_highlighted_surface.height)])
		# warrior_schematic.set_animation(	action_index=0,
		# 									animation=rest_sprite_animation)

		# med_strike_animation_length = 60
		# med_strike_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
		# 										#jerk=5.0,
		# 										duration=med_strike_animation_length,
		# 										sprites=[character_surface],
		# 										sprite_lengths=[med_strike_animation_length],
		# 										anchor_points=[Vec(0, character_surface.height)])
		# warrior_schematic.set_animation(	action_index=1,
		# 									animation=med_strike_sprite_animation)

		# intimidate_animation_length = 60
		# intimidate_sprite_animation = FullAnimation(#end_pos=Vec(-20,0),
		# 											#jerk=0.7,
		# 											duration=intimidate_animation_length,
		# 											sprites=[character_surface],
		# 											sprite_lengths=[intimidate_animation_length],
		# 											anchor_points=[Vec(0, character_surface.height)])
		# warrior_schematic.set_animation(	action_index=2,
		# 									animation=intimidate_sprite_animation)

		# bash_animation_length = 60
		# bash_sprite_animation = FullAnimation(#end_pos=Vec(100,0),
		# 									#		jerk=0.5,												
		# 											duration=bash_animation_length,
		# 											sprites=[character_surface],
		# 											sprite_lengths=[bash_animation_length],
		# 											anchor_points=[Vec(0, character_surface.height)])
		# warrior_schematic.set_animation(	action_index=3,
		# 									animation=bash_sprite_animation)


		# with open("actions.dat", "w") as f:
		# 	for action in warrior_schematic.actions:
		# 		f.write(action.serialize())

		# with open("warrior_test.dat", "w") as f:
		# 	f.write(warrior_schematic.serialize())

		#Action.from_string(med_bash_action.serialize())

		# self.friendlies.append(
		# self.friendlies.append(Friendly(slot=1,
		# 								traits={T.Vigor:35, T.Armor:5, T.Focus:8},
		# 								idle_animation=FullAnimation(	sprites=[character_surface],
		# 																sprite_lengths=[1],
		# 																anchor_points=[Vec(0,character_surface.height)]),
		# 								hover_idle_animation=FullAnimation(	sprites=[character_highlighted_surface],
		# 																	sprite_lengths=[1],
		# 																	anchor_points=[Vec(0,character_highlighted_surface.height)])
		# 								)		
		# 							)


		# Slot 0 friendly skills/animations
		# for friendly in [self.friendlies[0]]:
			# Res

		# Slot 1 Friendly skills/animations	


		# START: Wolf schematic
		wolf_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:0, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[wolf_enemy_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,wolf_enemy_surface.height)]),
											hover_idle_animation=FullAnimation(	sprites=[wolf_enemy_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,wolf_enemy_highlighted_surface.height)])
											)
		# Bite
		bite_action = ActionSchematic(	name="Bite",
								description="Deals 4 vigor damage to target. Requires 4 focus.",			
								target_set=TargetSet.SingleEnemy,
								required={T.Vigor:0, T.Focus:4, T.Armor:0},
								damages={T.Vigor:4, T.Focus:0, T.Armor:0})
		bite_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': bite_action.damages}))

		# Howl
		howl_action = ActionSchematic(	name="Howl",
								target_set=TargetSet.AllAllies,
								required={T.Vigor:0, T.Focus:0, T.Armor:0},
								damages={T.Vigor:0, T.Focus:-1, T.Armor:0})
		howl_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': howl_action.damages}))

		wolf_schematic.add_action(bite_action)
		wolf_schematic.add_action(howl_action)

		bite_animation_length = 60
		bite_sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.2, duration=rest_animation_length)],
												duration=bite_animation_length,
												sprites=[wolf_enemy_surface],
												sprite_lengths=[bite_animation_length],
												anchor_points=[Vec(0, wolf_enemy_surface.height)])
		wolf_schematic.set_animation(	action_index=0,
										animation=bite_sprite_animation)

		howl_animation_length = 60
		howl_sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(20,0), jerk=0.5, duration=rest_animation_length)],
												duration=howl_animation_length,
												sprites=[wolf_enemy_howl_surface],
												sprite_lengths=[howl_animation_length],
												anchor_points=[Vec(0, wolf_enemy_howl_surface.height)])
		wolf_schematic.set_animation(	action_index=1,
										animation=howl_sprite_animation)
		# END: Wolf schematic

		# START: Human schematic
		human_schematic = EnemySchematic(	traits={T.Vigor:4, T.Armor:10, T.Focus:4}, 
											idle_animation=FullAnimation(	sprites=[human_surface],
																			sprite_lengths=[1],
																			anchor_points=[Vec(0,human_surface.height)]),
											hover_idle_animation=FullAnimation(	sprites=[human_highlighted_surface],
																				sprite_lengths=[1],
																				anchor_points=[Vec(0,human_highlighted_surface.height)])
											)
		# Heal
		heal_action = ActionSchematic(	name="Heal",
								target_set=TargetSet.AllAllies,
								required={T.Vigor:0, T.Focus:2, T.Armor:0},
								damages={T.Vigor:-2, T.Focus:0, T.Armor:0})
		heal_action.add_sub_action(lambda source, targets: deal_damage(kwargs={	'source': source,
																				'targets': targets, 
																				'damages': heal_action.damages}))

		# Armor
		armor_action = ActionSchematic(	name="Rig Up",
								target_set=TargetSet.OtherAlly,
								required={T.Vigor:0, T.Focus:0, T.Armor:1},
								damages={T.Vigor:0, T.Focus:0, T.Armor:-1})
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': targets, 
																				'damages': armor_action.damages}))
		armor_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': TargetSet.Self, 
																				'damages': {T.Vigor:0, T.Armor:1, T.Focus:0}}))

		# Attack
		attack_action = ActionSchematic(	name="Attack",
								owner=None,
								target_set=TargetSet.SingleEnemy,
								required={T.Vigor:0, T.Focus:2, T.Armor:0},
								damages={T.Vigor:3, T.Focus:0, T.Armor:0})
		attack_action.add_sub_action(lambda source, targets: deal_damage(kwargs={'source': source,
																				'targets': targets, 
																				'damages': attack_action.damages}))		

		human_schematic.add_action(attack_action)
		human_schematic.add_action(heal_action)
		human_schematic.add_action(armor_action)

		# Heal Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(30,0), jerk=0.2, duration=animation_length)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=1,
										animation=sprite_animation)

		# Armor Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.1, duration=30),
													Tween(start_pos=Vec(-100,0), end_pos=Vec(0,0), jerk=0.4, duration=30)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=2,
										animation=sprite_animation)

		# Attack Animation
		animation_length = 60
		sprite_animation = FullAnimation(	tweens=[Tween(end_pos=Vec(-100,0), jerk=0.2, duration=55),
													Tween(start_pos=Vec(-100,0), end_pos=Vec(0,0), jerk=1.0, duration=5)],
											duration=animation_length,
											sprites=[human_surface],
											sprite_lengths=[animation_length],
											anchor_points=[Vec(0, human_surface.height)])
		human_schematic.set_animation(	action_index=0,
										animation=sprite_animation)	