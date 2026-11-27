extends SceneTree
# --script tests/ui_shot.gd -- sahne.tscn cikis.png saniye [tiklama_x,y ...]
var el := 0.0
var args: PackedStringArray
var scene
var taps := []
func _initialize():
	args = OS.get_cmdline_user_args()
	scene = load(args[0]).instantiate()
	root.add_child(scene)
	for i in range(3, args.size()):
		taps.append(args[i])
func _process(d):
	el += d
	if el > float(args[2]):
		root.get_viewport().get_texture().get_image().save_png(args[1])
		quit()
	return false
