extends SceneTree
# --script tests/net_e2e.gd -- host|client
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
	if role == "host":
		print("host err ", N.host())
	else:
		N.start_scan()
	N.joined.connect(func(): print(role, " JOINED ", Time.get_unix_time_from_system()); _go())
	N.multiplayer.peer_disconnected.connect(func(id): print(role, " PEER DISC ", id, " ", Time.get_unix_time_from_system()))
	N.message.connect(func(d): print(role, " MSG ", d))
	N.left.connect(func(r): print(role, " LEFT ", r, " ", Time.get_unix_time_from_system()))
func _go():
	G.mode = role
	if role == "host":
		await create_timer(0.5).timeout
		N.send({"t": "start", "c0": 0, "c1": 4, "dur": 60.0, "stad": 1, "wx": "rain"})
		G.chars = [0, 4]; G.stadium = 1; G.weather_now = "rain"; G.duration = 60.0
		change_scene_to_file("res://scenes/match.tscn")
	else:
		N.message.connect(func(d):
			if d.get("t") == "start":
				G.chars = [d["c0"], d["c1"]]; G.stadium = d["stad"]; G.weather_now = d["wx"]; G.duration = d["dur"]
				change_scene_to_file("res://scenes/match.tscn"))
func _process(d):
	el += d
	if int(el * 2) != int((el - d) * 2) and role == "client": print("c scene ", current_scene.name if current_scene else "-")
	if role == "client" and st == 0 and el > 3.0:
		print("found ", N.found)
		var ip = "127.0.0.1"
		if N.found.size() > 0: ip = N.found.keys()[0]
		print("join ", ip, " ", N.join(ip)); st = 1
	if role == "client" and st == 1 and el > 10.0:
		var ev := InputEventKey.new(); ev.physical_keycode = KEY_A; ev.pressed = true
		Input.parse_input_event(ev); st = 1.5
	var m = current_scene
	if m and m.name == "Match" and el > 16.0 and st < 2:
		st = 2
		if role == "client":
			m.press["k"] = true
		print(role, " online=", m.online, " phase=", m.world.phase, " p0=", snapped(m.world.players[0].x, 0.1), " p1=", snapped(m.world.players[1].x, 0.1), " ball=", snapped(m.world.ball.x, 0.1), ",", snapped(m.world.ball.y,0.1), " t=", snapped(m.world.time_left, 0.01))
		root.get_viewport().get_texture().get_image().save_png("/tmp/net_%s.png" % role)
	if el > 24.0:
		quit()
	return false
