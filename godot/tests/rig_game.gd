extends SceneTree
var el := 0.0
var sc
var shots := [5.6, 6.0, 6.4, 7.5]
var idx := 0
func _initialize():
	await process_frame
	var g = root.get_node("Game")
	g.chars = [0, 3]; g.stadium = 1; g.weather_now = "clear"
	sc = load("res://scenes/match.tscn").instantiate()
	root.add_child(sc)
func _process(d):
	el += d
	if sc and el > 5.4:
		var ev := InputEventKey.new(); ev.physical_keycode = KEY_D; ev.pressed = el < 7.0
		Input.parse_input_event(ev)
	if idx < shots.size() and el > shots[idx]:
		root.get_viewport().get_texture().get_image().save_png("/tmp/rig/game_%d.png" % idx); idx += 1
	if idx >= shots.size(): quit()
	return false
