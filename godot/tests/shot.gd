extends SceneTree
# Kullanim: --script tests/shot.gd -- cikis_oneki saniye1,saniye2,...
var times := []
var prefix := "/tmp/shot"
var scene
var elapsed := 0.0
var idx := 0

func _initialize():
	var args := OS.get_cmdline_user_args()
	if args.size() > 0: prefix = args[0]
	if args.size() > 1:
		for s in args[1].split(","): times.append(float(s))
	else:
		times = [1.0, 4.0]
	scene = load("res://scenes/match.tscn").instantiate()
	root.add_child(scene)

func _process(delta):
	elapsed += delta
	if idx < times.size() and elapsed >= times[idx]:
		var img := root.get_viewport().get_texture().get_image()
		img.save_png("%s_%d.png" % [prefix, idx])
		print("SHOT %d t=%.2f size=%s phase=%s score=%s" % [idx, elapsed, img.get_size(), scene.world.phase, scene.world.score])
		idx += 1
	if idx >= times.size():
		quit()
	return false
