extends SceneTree
var el := 0.0
var sc
var st := 0
func _initialize():
	sc = load("res://scenes/match.tscn").instantiate()
	root.add_child(sc)
func _process(d):
	el += d
	if el > 6.0 and st == 0:
		sc.world.time_left = 0.05; sc.world.score = [1, 1]; st = 1
	if st == 1 and sc.world.phase == "pen_aim" and sc.world.phase_t < 3.5:
		root.get_viewport().get_texture().get_image().save_png("/tmp/pen_aim.png"); st = 2
		print("aim ok turn ", sc.world.pen["turn"])
	if st == 2 and sc.world.phase == "pen_shot" and sc.world.phase_t < 0.8:
		root.get_viewport().get_texture().get_image().save_png("/tmp/pen_shot.png"); st = 3
		print("shot ", sc.world.pen["shot"])
	if el > 30: print("phase ", sc.world.phase); quit()
	if st == 3: quit()
	return false
