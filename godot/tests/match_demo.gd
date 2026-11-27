extends SceneTree
# Mac videosu: KAFA_DEMO=1 ile iki bot oynar. -- c0 c1 sure
var el := 0.0
var dur := 20.0
func _initialize():
	var a := OS.get_cmdline_user_args()
	await process_frame
	var g = root.get_node("Game")
	g.chars = [int(a[0]), int(a[1])]
	dur = float(a[2])
	g.mode = "bot"
	root.add_child(load("res://scenes/match.tscn").instantiate())
func _process(d):
	el += d
	if el > dur:
		quit()
	return false
