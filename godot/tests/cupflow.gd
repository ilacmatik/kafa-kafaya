extends SceneTree
var el := 0.0
var st := 0
var G
func _initialize():
	await process_frame
	G = root.get_node("Game")
	G.new_cup(1)
	G.cup_result = true
	change_scene_to_file("res://scenes/cup.tscn")
func _process(d):
	el += d
	if el > 1.2 and st == 0:
		root.get_viewport().get_texture().get_image().save_png("/tmp/ui_cup.png"); st = 1
		G.cup["stage"] = 4; G.cup_result = true
		change_scene_to_file("res://scenes/cup.tscn")
	if el > 5.0 and st == 1:
		print("scene ", current_scene.name, " cups ", G.profile["cups"])
		root.get_viewport().get_texture().get_image().save_png("/tmp/ui_trophy.png"); quit()
	return false
