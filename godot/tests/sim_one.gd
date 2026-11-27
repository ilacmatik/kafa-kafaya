extends SceneTree
func _init():
	var t0 := Time.get_ticks_msec()
	var w := SimWorld.new(0, 3, 10.0, "clear", false, 7)
	var b0 := SimBot.new(0, 1)
	var b1 := SimBot.new(1, 1)
	var dt: float = 1.0 / 120.0
	var steps := 0
	while steps < 600:
		var a0: Array = b0.think(w, dt)
		var a1: Array = b1.think(w, dt)
		w.apply_input(0, a0[0], a0[1], a0[2], a0[3], a0[4], null, b0.shoulder, false, dt)
		w.apply_input(1, a1[0], a1[1], a1[2], a1[3], a1[4], null, b1.shoulder, false, dt)
		w.step(dt)
		w.take_events()
		steps += 1
		if steps % 100 == 0:
			print(steps, " ", w.phase, " ", Time.get_ticks_msec() - t0, "ms ball ", Vector2(w.ball.x, w.ball.y))
	quit()
