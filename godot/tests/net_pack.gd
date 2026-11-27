extends SceneTree
func _initialize():
	var w := SimWorld.new(0, 3, 90.0, "clear", true, 5)
	for i in 300:
		w.apply_input(0, false, true, i % 40 == 0, i % 30 == 0, false)
		w.apply_input(1, true, false, false, false, false)
		w.step(1.0 / 120.0)
	var b := preload("res://scripts/net/net.gd").pack_world(w, ["kick"])
	var w2 := SimWorld.new(1, 2, 60.0, "rain", true, 9)
	var ev = preload("res://scripts/net/net.gd").unpack_world(w2, b)
	print("bytes ", b.size(), " ev ", ev, " p0x ", w.players[0].x, "=", w2.players[0].x, " ball ", w.ball.x, "=", w2.ball.x, " char ", w2.players[1].char, " time ", w2.time_left, " wx ", w2.weather)
	quit()
