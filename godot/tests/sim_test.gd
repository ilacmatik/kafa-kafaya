extends SceneTree
# Bot - bot maclari: 120 Hz ve 60 Hz'de skorlar ve fizik tutarliligi
func _init():
	var t0 := Time.get_ticks_msec()
	for hz in [120, 60]:
		var res := []
		var total := 0
		for m in 12:
			var w := SimWorld.new(m % 6, (m + 3) % 6, 60.0, "clear", false, 1000 + m)
			var b0 := SimBot.new(0, 1)
			var b1 := SimBot.new(1, 1)
			var dt: float = 1.0 / hz
			var steps := 0
			while w.phase != "over" and steps < hz * 200:
				var a0 := b0.think(w, dt)
				var a1 := b1.think(w, dt)
				w.apply_input(0, a0[0], a0[1], a0[2], a0[3], a0[4], null, b0.shoulder, false, dt)
				w.apply_input(1, a1[0], a1[1], a1[2], a1[3], a1[4], null, b1.shoulder, false, dt)
				w.step(dt)
				w.take_events()
				steps += 1
			res.append(str(w.score))
			total += w.score[0] + w.score[1]
		print("%d Hz: %s  toplam gol %d" % [hz, " ".join(res), total])
	print("sure %d ms" % (Time.get_ticks_msec() - t0))
	quit()
