extends SceneTree
var role := "host"
var el := 0.0
var st := 0
var G
var N
func _initialize():
	role = OS.get_cmdline_user_args()[0]
	await process_frame
	G = root.get_node("Game")
	N = root.get_node("Net")
	if role == "host": N.host()
	N.joined.connect(func(): G.mode = role; change_scene_to_file("res://scenes/select.tscn"))
func _process(d):
	el += d
	if role == "client" and st == 0 and el > 2.0:
		N.join("127.0.0.1"); st = 1
	var c = current_scene
	if c and c.name == "Select" and st < 2 and el > 6.0:
		st = 2
		c.on_tap("hero%d" % (2 if role == "host" else 5))
		c._next()
		print(role, " ready sent")
	if c and c.name == "Select" and el > 8.5 and st == 2:
		st = 3
		root.get_viewport().get_texture().get_image().save_png("/tmp/sel_%s.png" % role)
	if c and c.name == "Match" and st < 4:
		st = 4
		print(role, " MATCH chars ", G.chars, " me=", c.me)
	if el > 12.0: quit()
	return false
