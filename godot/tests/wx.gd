extends SceneTree
var el := 0.0
var i := 0
var wxs := ["rain", "snow", "wind"]
var sc
func _initialize():
	_start()
func _start():
	var g = root.get_node("Game")
	g.weather_now = wxs[i]
	g.stadium = 0
	sc = load("res://scenes/match.tscn").instantiate()
	root.add_child(sc)
	el = 0.0
func _process(d):
	el += d
	if el > 5.0:
		root.get_viewport().get_texture().get_image().save_png("/tmp/wx_%s.png" % wxs[i])
		sc.queue_free()
		i += 1
		if i >= wxs.size():
			quit()
		else:
			_start()
	return false
