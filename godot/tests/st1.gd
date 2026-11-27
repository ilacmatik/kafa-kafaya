extends SceneTree
var el := 0.0
var sc
func _initialize():
	await process_frame
	var g = root.get_node("Game")
	g.stadium = 1
	g.weather_now = "clear"
	sc = load("res://scenes/match.tscn").instantiate()
	root.add_child(sc)
func _process(d):
	el += d
	if el > 5.0:
		root.get_viewport().get_texture().get_image().save_png("/tmp/st1.png")
		quit()
	return false
