extends SceneTree
var scene
var el := 0.0
var step := 0
func _initialize():
	scene = load("res://scenes/match.tscn").instantiate()
	root.add_child(scene)
func _process(d):
	el += d
	if step == 0 and el > 6.0:
		root.get_viewport().get_texture().get_image().save_png("/tmp/ed_0.png")
		scene._toggle_pause()
		step = 1
	elif step == 1 and el > 6.5:
		root.get_viewport().get_texture().get_image().save_png("/tmp/ed_1.png")
		scene.touchc.start_edit()
		scene.touchc.sel = "k"
		step = 2
	elif step == 2 and el > 7.0:
		root.get_viewport().get_texture().get_image().save_png("/tmp/ed_2.png")
		quit()
	return false
