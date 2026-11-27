extends SceneTree
var el := 0.0
var sc
func _initialize():
	sc = load("res://scenes/match.tscn").instantiate()
	root.add_child(sc)
func _process(d):
	el += d
	if el > 4.0:
		sc.world.players[0].kick_t = 0.11
		sc.world.players[1].kick_t = 0.05
	if el > 4.3:
		root.get_viewport().get_texture().get_image().save_png("/tmp/kick.png")
		quit()
	return false
