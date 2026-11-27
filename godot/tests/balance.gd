extends SceneTree
# 8 kahraman denge testi: herkes herkese karsi (iki tarafta da), bot-bot. Ayrica kafa-kiris guvenlik kontrolu.
func _init():
	var n := K.CHARACTERS.size()
	var wins := []
	var gf := []
	var ga := []
	var played := []
	for c in n:
		wins.append(0.0); gf.append(0); ga.append(0); played.append(0)
	var min_gap := 1e9
	var rounds := int(OS.get_environment("BAL_R")) if OS.get_environment("BAL_R") != "" else 2
	var t0 := Time.get_ticks_msec()
	var seed := 1
	for r in rounds:
		for a in n:
			for b in n:
				if a == b:
					continue
				seed += 1
				var w := SimWorld.new(a, b, 60.0, "clear", false, seed)
				var b0 := SimBot.new(0, 2)
				var b1 := SimBot.new(1, 2)
				var dt := 1.0 / 120.0
				var boosted := [false, false]   # ziplama gucuyle havalanan (kural disi) oyuncu
				var steps := 0
				while w.phase != "over" and steps < 120 * 150:
					var a0 := b0.think(w, dt)
					var a1 := b1.think(w, dt)
					w.apply_input(0, a0[0], a0[1], a0[2], a0[3], a0[4], null, b0.shoulder, false, dt)
					w.apply_input(1, a1[0], a1[1], a1[2], a1[3], a1[4], null, b1.shoulder, false, dt)
					w.step(dt)
					w.take_events()
					for p: SimPlayer in w.players:
						if p.jump_t > 0.0:
							boosted[p.idx] = true
						elif p.on_ground:
							boosted[p.idx] = false
						if not boosted[p.idx] and (p.y - p.h) - K.GOAL_TOP < min_gap:
							min_gap = (p.y - p.h) - K.GOAL_TOP
							if min_gap < 40.0:
								print("ihlal: char %d y %.1f vy %.1f h %.1f on_ground %s bike %.2f sh %.2f kick %.2f air %d other_y %.1f dx %.1f" % [p.char, p.y, p.vy, p.h, p.on_ground, p.bike_t, p.shoulder_t, p.kick_t, p.air_jumps, w.players[1 - p.idx].y, w.players[1 - p.idx].x - p.x])
					steps += 1
				var s: Array = w.score
				played[a] += 1; played[b] += 1
				gf[a] += s[0]; ga[a] += s[1]; gf[b] += s[1]; ga[b] += s[0]
				if s[0] > s[1]: wins[a] += 1.0
				elif s[1] > s[0]: wins[b] += 1.0
				else:
					wins[a] += 0.5; wins[b] += 0.5
	for c in n:
		print("%-8s  galibiyet %%%3d  attigi %.2f  yedigi %.2f" % [K.CHARACTERS[c]["name"], int(100.0 * wins[c] / played[c]), float(gf[c]) / played[c], float(ga[c]) / played[c]])
	print("en kucuk kafa-kiris boslugu: %.1f (top capi %.0f olmali en az)" % [min_gap, 2.0 * K.BALL_R])
	print("sure %d ms" % (Time.get_ticks_msec() - t0))
	quit()
