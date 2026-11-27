## Kafa Kafaya - mac simulasyonu (sim.py World'un birebir GDScript karsiligi).
## Host (ya da tek cihaz) bunu calistirir; istemci snapshot() ciktisini cizer.
## Kare hizindan bagimsizdir: 60 Hz'e gore ayarlanmis kare-basi katsayilar K.f60/K.p60 ile cevrilir.
class_name SimWorld
extends RefCounted

var rng := RandomNumberGenerator.new()
var players: Array = []
var ball := SimBall.new()
var score := [0, 0]
var duration := 90.0
var time_left := 90.0
var phase := "ready"
var phase_t := 2.6
var golden := false
var winner := -1
var last_touch := -1
var events: Array = []
var pu = null                  # [tur, x, y, omur] ya da null
var pu_timer := 9.0
var shield := [0.0, 0.0]
var glove := [0.0, 0.0]
var scorer := -1
var clock := 0.0
var last_kind := "shot"
var shake := 0.0
var weather := "clear"
var wind := 0.0
var wind_t := 12.0
var pens_on := true
var net_cd := 0.0
var pen = null
var goal_info := ""
var stats := {"shots": [0, 0], "heads": [0, 0], "saves": [0, 0], "fast": [0, 0], "poss": [0.0, 0.0]}


func _init(char0: int, char1: int, dur: float = 90.0, wx: String = "clear", pens: bool = true, seed_v: int = -1) -> void:
	if seed_v >= 0:
		rng.seed = seed_v
	else:
		rng.randomize()
	players = [SimPlayer.new(0, char0), SimPlayer.new(1, char1)]
	ball.reset(rng)
	duration = dur
	time_left = dur
	pu_timer = rng.randf_range(7.0, 11.0)
	weather = wx
	wind = ((1.0 if rng.randf() < 0.5 else -1.0) * rng.randf_range(150.0, 230.0)) if wx == "wind" else 0.0
	wind_t = rng.randf_range(10.0, 16.0)
	pens_on = pens
	events.append("whistle")


func _choice(arr: Array):
	return arr[rng.randi_range(0, arr.size() - 1)]


# ------------------------------------------------------------ girdiler
func apply_input(i: int, left: bool, right: bool, jump: bool, kick_pressed: bool, super_pressed: bool,
		kick_held = null, shoulder: bool = false, lob: bool = false, dt: float = 1.0 / 60.0) -> void:
	var p: SimPlayer = players[i]
	var jump_edge := jump and not p.jump_prev
	p.jump_prev = jump
	if phase == "pen_aim":
		if kick_pressed and pen["c"][i] == null:
			var col := (1 if right else 0) - (1 if left else 0)
			pen["c"][i] = [col, 1 if jump else 0]
			events.append("pen_lock:%d" % i)
		p.vx = 0.0
		return
	if phase in ["ready", "over", "pen_ready", "pen_res", "pen_shot"]:
		p.vx = 0.0
		p.charging = false
		return
	if p.disabled():
		p.vx *= K.p60(0.85, dt)
		return
	if phase == "pen" and pen["turn"] != i and last_touch < 0:
		p.vx = 0.0
		return
	var spd: float = p.stats["speed"] * (1.45 if p.speed_t > 0.0 else 1.0)
	if weather == "snow":
		spd *= 0.88
	var move := (1 if right else 0) - (1 if left else 0)
	var back := move != 0 and move != p.dir
	if back:
		spd *= K.BACK_SPEED
	var target := move * spd
	var acc := ((0.45 if back else 0.35) if p.on_ground else (0.26 if back else 0.18))
	if weather == "rain" and p.on_ground:
		acc *= 0.5
	p.vx += (target - p.vx) * K.f60(acc, dt)
	if shoulder and p.shoulder_cd <= 0.0 and p.on_ground and p.slide_t <= 0.0:
		var o: SimPlayer = players[1 - i]
		if move != 0 and absf(p.vx) > 150.0:
			p.sl_dir = move
			p.slide_t = 0.5
			p.shoulder_cd = 1.6
			p.sl_hit = false
			events.append("slide:%d" % i)
		else:
			p.sh_dir = move if move != 0 else (1 if o.x > p.x else -1)
			p.shoulder_t = 0.28
			p.shoulder_cd = 1.8
			p.sh_hit = false
			events.append("shoulder:%d" % i)
	if p.slide_t > 0.0:
		var k := p.slide_t / 0.5
		p.vx = p.sl_dir * (120.0 + 560.0 * k)
		p.move = 0
		p.jump_prev = jump
		return
	if p.shoulder_t > 0.0:
		p.vx = p.sh_dir * 640.0
	p.move = move
	p.face = p.dir
	var jmul := 1.28 if p.jump_t > 0.0 else 1.0
	p.lob = lob
	if jump and p.on_ground:
		p.vy = -minf(p.stats["jump"] * K.JUMP_K * jmul, p.jump_cap() if jmul <= 1.0 else 1e9)
		p.on_ground = false
		p.air_jumps = 1
		p.jump_cut = false
		events.append("jump")
	elif not jump and not p.on_ground and p.vy < -180.0 and not p.jump_cut:
		p.vy *= 0.55
		p.jump_cut = true
	elif jump_edge and not p.on_ground and p.air_jumps > 0:
		p.air_jumps = 0
		p.vy = -minf(p.stats["jump"] * K.JUMP_K * 0.82 * jmul, p.jump_cap() if jmul <= 1.0 else 1e9)
		events.append("jump2:%d" % i)
	if kick_held == null:
		if kick_pressed and p.kick_t <= 0.0:
			_swing(p, 0.0)
	else:
		if kick_pressed and not p.charging and p.kick_t <= 0.0:
			p.charging = true
			p.charge = 0.0
		if p.charging and not kick_held:
			p.charging = false
			_swing(p, p.charge)
	if super_pressed and p.meter >= 100.0 and p.armed <= 0.0 and p.magnet_t <= 0.0 and phase == "play":
		_use_power(p)


# ------------------------------------------------------------ yardimcilar
func _use_power(p: SimPlayer) -> void:
	var pw: String = p.stats["power"]
	var b := ball
	var o: SimPlayer = players[1 - p.idx]
	p.meter = 0.0
	if pw == "fire" or pw == "ice":
		p.armed = 5.0
		events.append("armed")
		if Vector2(b.x - p.x, b.y - (p.y - p.h * 0.5)).length() < 150.0:
			_super_shot(p)
	elif pw == "magnet":
		p.magnet_t = 3.0
		b.mode = 0
		last_touch = p.idx
		events.append("magnet:%d" % p.idx)
	elif pw == "glove":
		shield[p.idx] = 4.5
		glove[p.idx] = 4.5
		events.append("glove:%d" % p.idx)
	elif pw == "bolt":
		var fx := p.x
		p.x = clampf(b.x - p.dir * 48.0, 40.0, K.W - 40.0)
		if b.y > K.GROUND - 160.0:
			p.y = K.GROUND
			p.vy = 0.0
			p.on_ground = true
		p.speed_t = maxf(p.speed_t, 3.0)
		events.append("bolt:%d:%d" % [p.idx, int(fx)])
	elif pw == "quake":
		events.append("quake:%d" % p.idx)
		shake = 0.6
		if o.y >= K.GROUND - 30.0 and o.frozen <= 0.0:
			o.stun = 1.3
			o.vy = -260.0
			o.on_ground = false
			o.vx = 320.0 * (1.0 if o.x > p.x else -1.0)
		if b.y > K.GROUND - 220.0 and b.mode == 0:
			b.vy = -760.0
			b.vx *= 0.4
			b.spin = 0.0


func _swing(p: SimPlayer, charge: float) -> void:
	p.kick_t = 0.24
	p.kick_hit = false
	p.lob_shot = false
	p.kick_power = 1.0 + 0.45 * maxf(0.0, (charge - 0.15) / 0.85)
	events.append("swing")


func _super_shot(p: SimPlayer) -> void:
	var b := ball
	p.armed = 0.0
	var kind := 1 if p.stats["power"] == "fire" else 2
	var gx := K.W - K.GOAL_D * 0.5 if p.idx == 0 else K.GOAL_D * 0.5
	var gy := K.GROUND - rng.randf_range(40.0, K.GOAL_H - 50.0)
	var d := Vector2(gx - b.x, gy - b.y)
	var l := d.length()
	if l == 0.0:
		l = 1.0
	b.vx = d.x / l * K.SUPER_SPEED
	b.vy = d.y / l * K.SUPER_SPEED
	b.mode = kind
	b.mode_t = K.SUPER_TIME
	b.owner = p.idx
	last_touch = p.idx
	last_kind = "super"
	events.append("super_fire" if kind == 1 else "super_ice")
	shake = 0.25


func _touch(p: SimPlayer) -> bool:
	var b := ball
	var own_x := 0.0 if p.idx == 0 else K.W
	var toward := (b.vx < -350.0) if p.idx == 0 else (b.vx > 350.0)
	if p.touch_cd <= 0.0 and toward and absf(b.x - own_x) < 300.0 and last_touch != p.idx:
		stats["saves"][p.idx] += 1
	p.contact = clock
	if p.touch_cd <= 0.0:
		p.meter = minf(100.0, p.meter + K.METER_PER_TOUCH)
		p.touch_cd = 0.35
	last_touch = p.idx
	if p.armed > 0.0:
		_super_shot(p)
		return true
	return false


func _circle_vs_ball(cx: float, cy: float, r: float, pvx: float, pvy: float, e: float = 0.55) -> bool:
	var b := ball
	var dx := b.x - cx
	var dy := b.y - cy
	var d := sqrt(dx * dx + dy * dy)
	var rr := r + K.BALL_R
	if d >= rr or d == 0.0:
		return false
	var nx := dx / d
	var ny := dy / d
	b.x += nx * (rr - d)
	b.y += ny * (rr - d)
	var rvx := b.vx - pvx
	var rvy := b.vy - pvy
	var vn := rvx * nx + rvy * ny
	if vn < 0.0:
		b.vx -= (1.0 + e) * vn * nx
		b.vy -= (1.0 + e) * vn * ny
	var vn2 := (b.vx - pvx) * nx + (b.vy - pvy) * ny
	if vn2 < 140.0:
		b.vx += nx * (140.0 - vn2)
		b.vy += ny * (140.0 - vn2)
	return true


func _rect_vs_ball(x0: float, y0: float, x1: float, y1: float, e: float = 0.6) -> bool:
	var b := ball
	var cx := clampf(b.x, x0, x1)
	var cy := clampf(b.y, y0, y1)
	var dx := b.x - cx
	var dy := b.y - cy
	var d := sqrt(dx * dx + dy * dy)
	if d >= K.BALL_R:
		return false
	if d == 0.0:
		b.y = y0 - K.BALL_R
		b.vy = -absf(b.vy) * e
		return true
	var nx := dx / d
	var ny := dy / d
	b.x += nx * (K.BALL_R - d)
	b.y += ny * (K.BALL_R - d)
	var vn := b.vx * nx + b.vy * ny
	if vn < 0.0:
		b.vx -= (1.0 + e) * vn * nx
		b.vy -= (1.0 + e) * vn * ny
		if absf(vn) > 200.0:
			events.append("post")
	return true


func _kick(p: SimPlayer, rel: float) -> void:
	var b := ball
	var pw: float = p.stats["kick"]
	var q := 1.0 - 0.4 * clampf(rel, 0.0, 1.0)
	var h := p.y - b.y
	var off := clampf(32.0 * K.SIZE - h + K.BALL_R * 0.4, -55.0, 40.0)
	var ang := clampf(30.0 + off * 0.62, -6.0, 56.0)
	var kind := "volley" if h >= 85.0 else "shot"
	q *= 1.0 - 0.12 * clampf(absf(off) / 40.0, 0.0, 1.0)
	var spin := 0.1
	var mv := p.move * p.dir
	if p.lob and h < 90.0:
		ang = 64.0
		spin = -0.8
		kind = "lob"
	elif mv < 0:
		ang = 66.0
		q *= 0.9
		spin = -0.9
		kind = "lob"
	if not p.on_ground:
		ang -= 4.0
	if phase == "pen" and pen["turn"] == p.idx:
		var gx := K.W - K.GOAL_D + 10.0 if p.dir == 1 else K.GOAL_D - 10.0
		var hy := rng.randf_range(128.0, 150.0) if p.lob else rng.randf_range(26.0, 46.0)
		var vx := 820.0 * pw * p.kick_power
		var T := absf(gx - b.x) / vx
		var ty := K.GROUND - hy
		b.vx = p.dir * vx
		b.vy = (ty - b.y - 0.5 * K.BALL_G * T * T) / T
		b.spin = 0.0
		b.mode = 0
		b.ignore_t = 0.12
		b.ignore_p = p.idx
		last_kind = "lob" if p.lob else "drive"
		stats["shots"][p.idx] += 1
		events.append("kick")
		_touch(p)
		return
	b.curve = 0.0
	if mv > 0 and absf(p.vx) > 150.0 and kind != "lob":
		ang += 8.0
		q *= 0.96
		b.curve = 1.0
		if kind == "shot":
			kind = "curve"
	var speed := 900.0 * pw * q * p.kick_power
	if p.kick_power > 1.3:
		kind = "power"
		events.append("kick_hard")
	var r := deg_to_rad(ang)
	b.vx = p.dir * speed * cos(r) + p.vx * 0.25
	b.vy = -speed * sin(r) + (p.vy * 0.2 if p.vy < 0.0 else 0.0)
	b.spin = spin
	b.cdir = p.dir
	b.mode = 0
	b.ignore_t = 0.12
	b.ignore_p = p.idx
	last_kind = kind
	stats["shots"][p.idx] += 1
	stats["fast"][p.idx] = maxi(stats["fast"][p.idx], int(speed))
	events.append("kick")
	_touch(p)


func _bicycle(p: SimPlayer) -> void:
	var b := ball
	var pw: float = p.stats["kick"] * p.kick_power
	b.vx = p.dir * 1020.0 * pw
	b.vy = 160.0 if b.y < K.GROUND - 280.0 else -40.0
	b.spin = 0.3
	b.mode = 0
	b.ignore_t = 0.2
	b.ignore_p = p.idx
	p.bike_t = 0.5
	p.vy = minf(p.vy, -120.0)
	last_kind = "bicycle"
	stats["shots"][p.idx] += 1
	stats["fast"][p.idx] = maxi(stats["fast"][p.idx], int(Vector2(b.vx, b.vy).length()))
	events.append("bicycle:%d" % p.idx)
	_touch(p)


func _smash(p: SimPlayer) -> void:
	var b := ball
	var pw: float = p.stats["kick"] * p.kick_power
	b.vx = p.dir * 880.0 * pw
	b.vy = 260.0 if b.y < K.GROUND - 200.0 else -120.0
	b.spin = 0.4
	b.mode = 0
	b.ignore_t = 0.15
	b.ignore_p = p.idx
	last_kind = "smash"
	events.append("smash")
	_touch(p)


func _flick(p: SimPlayer) -> void:
	var b := ball
	b.x = p.x - p.dir * 6.0
	b.y = minf(b.y, p.y - 45.0)
	b.vx = p.dir * (340.0 + absf(p.vx) * 0.3)
	b.vy = -990.0
	b.spin = -0.3
	b.mode = 0
	b.ignore_t = 0.45
	b.ignore_p = p.idx
	last_kind = "flick"
	events.append("kick")
	_touch(p)


func goal_rects() -> Array:
	var r := K.ROOF_T / 2.0
	return [
		[0.0, K.GOAL_TOP - K.ROOF_T, K.GOAL_D + 20.0 - r, K.GOAL_TOP],
		[K.W - K.GOAL_D - 20.0 + r, K.GOAL_TOP - K.ROOF_T, K.W, K.GOAL_TOP],
	]


func post_tips() -> Array:
	var r := K.ROOF_T / 2.0 + 1.0
	var y := K.GOAL_TOP - K.ROOF_T / 2.0
	return [Vector3(K.GOAL_D + 20.0 - r, y, r), Vector3(K.W - K.GOAL_D - 20.0 + r, y, r)]


# ------------------------------------------------------------ adim
func step(dt: float) -> void:
	clock += dt
	if phase == "pen_ready":
		phase_t -= dt
		if phase_t <= 0.0:
			phase = "pen_aim"
			phase_t = K.PEN_AIM_T
			events.append("whistle")
		return
	if phase == "pen_aim":
		phase_t -= dt
		var c: Array = pen["c"]
		if (c[0] != null and c[1] != null) or phase_t <= 0.0:
			_pen_shoot()
		return
	if phase == "pen_shot":
		phase_t -= dt
		if phase_t <= 0.0:
			_pen_result(pen["shot"][4])
		return
	if phase == "pen_res":
		phase_t -= dt
		if phase_t <= 0.0:
			_pen_next()
		return
	if phase == "play":
		if last_touch >= 0:
			stats["poss"][last_touch] += dt
		if wind != 0.0:
			wind_t -= dt
			if wind_t <= 0.0:
				wind = -wind * rng.randf_range(0.8, 1.2)
				wind_t = rng.randf_range(10.0, 16.0)
				events.append("wind")
	if phase == "over":
		_step_players(dt)
		return
	if phase == "ready":
		phase_t -= dt
		if phase_t <= 0.0:
			phase = "play"
			events.append("whistle")
		return
	if phase == "play":
		time_left -= dt
		if time_left <= 0.0 and not golden:
			time_left = 0.0
			if score[0] != score[1]:
				_end()
				return
			if pens_on:
				_start_pens()
				return
			golden = true
			events.append("golden")
	if phase == "goal":
		phase_t -= dt
		if phase_t > 2.4 - 0.7:
			dt *= 0.3
		if phase_t <= 0.0:
			if golden or (time_left <= 0.0 and score[0] != score[1]):
				_end()
				return
			_kickoff()
			return

	for p: SimPlayer in players:
		if phase == "play":
			p.meter = minf(100.0, p.meter + K.METER_PER_SEC * dt)
		if p.charging:
			p.charge = minf(1.0, p.charge + dt / 0.4)
		p.kick_t = maxf(0.0, p.kick_t - dt)
		p.frozen = maxf(0.0, p.frozen - dt)
		p.stun = maxf(0.0, p.stun - dt)
		p.speed_t = maxf(0.0, p.speed_t - dt)
		p.jump_t = maxf(0.0, p.jump_t - dt)
		p.armed = maxf(0.0, p.armed - dt)
		p.touch_cd = maxf(0.0, p.touch_cd - dt)
		p.magnet_t = maxf(0.0, p.magnet_t - dt)
		p.shoulder_t = maxf(0.0, p.shoulder_t - dt)
		p.shoulder_cd = maxf(0.0, p.shoulder_cd - dt)
		p.bike_t = maxf(0.0, p.bike_t - dt)
		p.slide_t = maxf(0.0, p.slide_t - dt)
	for i in 2:
		shield[i] = maxf(0.0, shield[i] - dt)
		glove[i] = maxf(0.0, glove[i] - dt)

	_step_players(dt)
	# topu ~180 Hz'de alt adimla (hizli toplar duvardan gecmesin)
	var sub := maxi(1, ceili(dt * 180.0 - 0.001))
	for _k in sub:
		_step_ball(dt / sub)
	_step_powerup(dt)


func _step_players(dt: float) -> void:
	var a: SimPlayer = players[0]
	var b: SimPlayer = players[1]
	for p: SimPlayer in players:
		var prev_y: float = p.y
		var prev_top: float = p.y - p.h
		p.vy += K.PLAYER_G * dt
		p.x += p.vx * dt
		p.y += p.vy * dt
		if absf(p.vx) > 30.0 and p.on_ground:
			p.run_t += dt
		p.on_ground = false
		if p.y >= K.GROUND:
			p.air_jumps = 0
			if p.vy > 300.0:
				events.append("land")
			p.y = K.GROUND
			p.vy = 0.0
			p.on_ground = true
		p.x = clampf(p.x, 28.0, K.W - 28.0)
		for r in goal_rects():
			var gx0: float = r[0]
			var gy0: float = r[1]
			var gx1: float = r[2]
			var gy1: float = r[3]
			if gx0 - 18.0 < p.x and p.x < gx1 + 18.0:
				if prev_y <= gy0 + 1.0 and p.y >= gy0 and p.vy >= 0.0:
					p.y = gy0
					p.vy = 0.0
					p.on_ground = true
				elif prev_top >= gy1 - 1.0 and p.y - p.h < gy1 and p.vy < 0.0:
					p.y = gy1 + p.h
					p.vy = 0.0
	var dx := b.x - a.x
	if absf(dx) < 72.0 and (a.y - a.h < b.y and b.y - b.h < a.y):
		var over := 72.0 - absf(dx)
		var s := 1 if dx >= 0.0 else -1
		var ma: float = a.stats["mass"]
		var mb: float = b.stats["mass"]
		a.x -= s * over * mb / (ma + mb)
		b.x += s * over * ma / (ma + mb)
		a.x = clampf(a.x, 28.0, K.W - 28.0)
		b.x = clampf(b.x, 28.0, K.W - 28.0)
		if (a.vx - b.vx) * s > 180.0 and a.shoulder_t <= 0.0 and b.shoulder_t <= 0.0:
			var e := 0.5
			var va := (ma * a.vx + mb * b.vx + mb * e * (b.vx - a.vx)) / (ma + mb)
			var vb := (ma * a.vx + mb * b.vx + ma * e * (a.vx - b.vx)) / (ma + mb)
			a.vx = va
			b.vx = vb
		for pair in [[a, b, s], [b, a, -s]]:
			var p: SimPlayer = pair[0]
			var o: SimPlayer = pair[1]
			var d: int = pair[2]
			if p.shoulder_t > 0.0 and not p.sh_hit and p.sh_dir == d:
				p.sh_hit = true
				var r: float = p.stats["mass"] / o.stats["mass"]
				o.vx = d * minf(760.0, 430.0 * r)
				if o.frozen <= 0.0:
					o.vy = -minf(380.0, 200.0 * r)
					o.on_ground = false
					o.stun = maxf(o.stun, minf(0.7, 0.32 * r))
				o.charging = false
				p.vx *= 0.25
				p.shoulder_t = 0.0
				events.append("bump:%d" % o.idx)
		for pair in [[a, b, s], [b, a, -s]]:
			var p: SimPlayer = pair[0]
			var o: SimPlayer = pair[1]
			var d: int = pair[2]
			if p.slide_t > 0.0 and not p.sl_hit and p.sl_dir == d and o.on_ground:
				p.sl_hit = true
				o.stun = maxf(o.stun, 0.8)
				o.vy = -260.0
				o.on_ground = false
				o.vx = d * 180.0
				o.charging = false
				events.append("trip:%d" % o.idx)


func _step_ball(dt: float) -> void:
	var b := ball
	for i in 2:
		if b.hit_cd[i] > 0.0:
			b.hit_cd[i] -= dt
	if b.ignore_t > 0.0:
		b.ignore_t -= dt
	if net_cd > 0.0:
		net_cd -= dt
	if b.squeeze_cd > 0.0:
		b.squeeze_cd -= dt
	var bdt := dt * K.BALL_TS
	var mag: SimPlayer = null
	for q: SimPlayer in players:
		if q.magnet_t > 0.0 and not q.disabled():
			mag = q
	if mag != null and b.mode == 0:
		var tx := mag.x + mag.dir * 34.0
		var ty := mag.y - 26.0 if mag.on_ground else mag.y - mag.h * 0.35
		var kk := minf(1.0, dt * 14.0)
		b.vx += ((tx - b.x) * 60.0 - b.vx) * kk
		b.vy += ((ty - b.y) * 60.0 - b.vy) * kk
		b.spin = 0.0
	elif b.mode != 0:
		b.mode_t -= dt
		if b.mode_t <= 0.0:
			b.mode = 0
	else:
		b.vy += K.BALL_G * bdt + b.spin * 430.0 * bdt
		b.vx *= (1.0 - 0.12 * bdt)
		if wind != 0.0 and b.y < K.GROUND - K.BALL_R - 4.0:
			b.vx += wind * bdt
		if b.curve > 0.0:
			if b.y < K.GROUND - K.BALL_R - 4.0:
				b.vx += b.cdir * 520.0 * b.curve * bdt
				b.vy += 300.0 * b.curve * bdt
			b.curve = maxf(0.0, b.curve - dt * 1.3)
		b.spin *= (1.0 - 0.6 * bdt)
	b.px = b.x
	b.x += b.vx * bdt
	b.y += b.vy * bdt
	b.ang += (b.vx / K.BALL_R + b.spin * 12.0 * (1.0 if b.vx >= 0.0 else -1.0)) * bdt

	# zemin
	if b.y + K.BALL_R > K.GROUND:
		b.y = K.GROUND - K.BALL_R
		if b.vy > 0.0:
			if b.vy > 160.0:
				events.append("bounce")
				if b.spin != 0.0:
					b.vx += (1.0 if b.vx >= 0.0 else -1.0) * b.spin * 160.0
					b.spin *= 0.4
			var rest := 0.68
			if weather == "rain":
				rest = 0.55
			elif weather == "snow":
				rest = 0.42
			b.vy = -b.vy * rest
			if absf(b.vy) < 60.0:
				b.vy = 0.0
		var fr := 1.1
		if weather == "rain":
			fr = 0.45
		elif weather == "snow":
			fr = 2.6
		b.vx *= (1.0 - fr * dt)
		if absf(b.vy) < 40.0 and b.spin != 0.0:
			b.vx += (1.0 if b.vx >= 0.0 else -1.0) * b.spin * 140.0 * dt
			b.spin *= (1.0 - 2.2 * dt)
		if absf(b.vx) < 6.0 and absf(b.vy) < 1.0:
			b.vx = 0.0
		if b.mode != 0:
			b.mode = 0
	# tavan
	if b.y - K.BALL_R < 0.0:
		b.y = K.BALL_R
		b.vy = absf(b.vy) * 0.7
	# yan duvarlar
	for side in 2:
		var wall := K.BALL_R if side == 0 else K.W - K.BALL_R
		var hit := (b.x < wall) if side == 0 else (b.x > wall)
		if hit:
			var inside_goal := b.y > K.GOAL_TOP
			var e := 0.25 if inside_goal else 0.75
			b.x = wall
			b.vx = (absf(b.vx) if side == 0 else -absf(b.vx)) * e
			if b.mode != 0:
				b.mode = 0
			if not inside_goal:
				events.append("bounce")
	# kale catisi / ust direk
	for r in goal_rects():
		if _rect_vs_ball(r[0], r[1], r[2], r[3]):
			if b.mode != 0:
				b.mode = 0
	for t in post_tips():
		var spd := Vector2(b.vx, b.vy).length()
		if _circle_vs_ball(t.x, t.y, t.z, 0.0, 0.0, 0.72):
			b.spin = -b.spin * 0.5
			if b.mode != 0:
				b.mode = 0
			if spd > 250.0:
				events.append("post")
	# file
	for side in 2:
		var inside := (b.x < K.GOAL_D - 4.0) if side == 0 else (b.x > K.W - K.GOAL_D + 4.0)
		if inside and b.y > K.GOAL_TOP:
			var damp := 1.0 - minf(0.9, 5.5 * dt)
			b.vx *= damp
			b.spin *= damp
			if b.y - K.BALL_R < K.GOAL_TOP + 2.0 and b.vy < 0.0:
				b.y = K.GOAL_TOP + K.BALL_R + 2.0
				b.vy = absf(b.vy) * 0.2
			var back := K.BALL_R + 4.0 if side == 0 else K.W - K.BALL_R - 4.0
			if (side == 0 and b.x < back) or (side == 1 and b.x > back):
				if absf(b.vx) > 120.0 and net_cd <= 0.0:
					events.append("net:%d:%d" % [side, int(b.y)])
					net_cd = 0.4
	# buz kalkani
	for i in 2:
		if shield[i] > 0.0 and phase == "play":
			if i == 0 and b.x - K.BALL_R < K.GOAL_D + 8.0 and b.y > K.GOAL_TOP and b.vx < 0.0:
				b.x = K.GOAL_D + 8.0 + K.BALL_R
				b.vx = absf(b.vx) * 0.8
				b.mode = 0
				events.append("shield")
			if i == 1 and b.x + K.BALL_R > K.W - K.GOAL_D - 8.0 and b.y > K.GOAL_TOP and b.vx > 0.0:
				b.x = K.W - K.GOAL_D - 8.0 - K.BALL_R
				b.vx = -absf(b.vx) * 0.8
				b.mode = 0
				events.append("shield")

	# oyuncular
	for p: SimPlayer in players:
		var opp_super := b.mode != 0 and b.owner != p.idx
		if opp_super and b.hit_cd[p.idx] <= 0.0:
			var hh: Vector3 = p.head()
			var bb: Vector3 = p.body()
			var ll: Vector3 = p.legs()
			if (Vector2(b.x - hh.x, b.y - hh.y).length() < hh.z + K.BALL_R or
					Vector2(b.x - bb.x, b.y - bb.y).length() < bb.z + K.BALL_R or
					Vector2(b.x - ll.x, b.y - ll.y).length() < ll.z + K.BALL_R):
				b.hit_cd[p.idx] = 0.5
				if p.kick_t > 0.05 and not p.disabled():
					b.mode = 0
					b.vx = -b.vx * 0.6
					b.vy = -400.0
					events.append("block")
					stats["saves"][p.idx] += 1
					_touch(p)
				elif b.mode == 1:
					p.stun = 0.9
					p.vx = 520.0 * (1.0 if b.vx > 0.0 else -1.0)
					p.vy = -380.0
					p.on_ground = false
					events.append("fire_hit")
				else:
					p.frozen = 2.2
					events.append("freeze")
				continue
		if b.mode != 0 and b.owner != p.idx:
			continue
		if mag != null and mag != p:
			continue
		if mag == p and not (p.kick_t > 0.0 and not p.kick_hit):
			continue
		if b.ignore_t > 0.0 and (b.ignore_p == p.idx or b.ignore_p == -2):
			continue
		var touched := false
		# kayarak mudahale
		if p.slide_t > 0.0 and not p.sl_hit and b.y > K.GROUND - 70.0:
			var fx_ := p.x + p.sl_dir * 40.0
			if absf(b.x - fx_) < 46.0:
				p.sl_hit = true
				b.vx = p.sl_dir * 560.0
				b.vy = -200.0
				b.spin = 0.2
				b.ignore_t = 0.25
				b.ignore_p = p.idx
				last_kind = "body"
				events.append("kick")
				_touch(p)
				continue
		# top surme
		if (p.on_ground and p.move != 0 and absf(p.vx) > 120.0 and p.kick_t <= 0.0 and not p.disabled()
				and b.y > K.GROUND - K.BALL_R - 8.0 and absf(b.vy) < 120.0 and b.mode == 0
				and 8.0 < (b.x - p.x) * p.move and (b.x - p.x) * p.move < 74.0 and absf(b.vx - p.vx) < 320.0):
			var tx := p.x + p.move * 50.0
			b.vx += ((tx - b.x) * 7.0 + p.vx - b.vx) * minf(1.0, dt * 10.0)
			b.spin = 0.0
			if last_touch != p.idx:
				_touch(p)
			last_touch = p.idx
			continue
		if p.kick_t > 0.0 and not p.kick_hit and not p.disabled() and not p.on_ground:
			var hh: Vector3 = p.head()
			var back := (b.x - p.x) * p.dir
			if (b.y < p.y - p.h * 0.62 and -85.0 < back and back < 14.0
					and Vector2(b.x - hh.x, b.y - hh.y).length() < hh.z + K.BALL_R + 44.0):
				p.kick_hit = true
				_bicycle(p)
				continue
			if b.y < p.y - p.h * 0.55 and Vector2(b.x - hh.x, b.y - hh.y).length() < hh.z + K.BALL_R + 14.0:
				p.kick_hit = true
				_smash(p)
				continue
		if p.kick_t > 0.0 and not p.kick_hit and not p.disabled():
			var ff: Vector3 = p.foot()
			var dist := Vector2(b.x - ff.x, b.y - ff.y).length()
			if dist < ff.z + K.BALL_R or mag == p:
				p.kick_hit = true
				if mag == p:
					p.magnet_t = 0.0
					p.kick_power = maxf(p.kick_power, 1.4)
					dist = 0.0
				_kick(p, dist / (ff.z + K.BALL_R))
				continue
			var back2 := (b.x - p.x) * p.dir
			if -78.0 < back2 and back2 < 6.0 and p.y - b.y < 95.0 and absf(b.y - (p.y - 30.0)) < 75.0:
				p.kick_hit = true
				_flick(p)
				continue
		var hd: Vector3 = p.head()
		if _circle_vs_ball(hd.x, hd.y, hd.z, p.vx, p.vy, 0.75):
			touched = true
			last_kind = "head"
			b.spin *= 0.3
			if p.vy < -50.0:
				b.vy += p.vy * 0.35
			if p.move != 0:
				b.vx += p.move * 260.0
				b.vx = clampf(b.vx, -1100.0, 1100.0)
			if absf(b.vx) + absf(b.vy) > 450.0:
				events.append("head")
				if p.touch_cd <= 0.0:
					stats["heads"][p.idx] += 1
		var bd: Vector3 = p.body()
		if _circle_vs_ball(bd.x, bd.y, bd.z, p.vx, p.vy, 0.45):
			touched = true
		if p.on_ground or p.y > b.y + 4.0:
			var lg: Vector3 = p.legs()
			if _circle_vs_ball(lg.x, lg.y, lg.z, p.vx, p.vy, 0.4):
				touched = true
		if touched:
			if last_touch != p.idx:
				last_kind = "body"
			_touch(p)
	# iki oyuncu arasinda sikisan top yukari firlar
	var pa: SimPlayer = players[0]
	var pc: SimPlayer = players[1]
	if (b.mode == 0 and b.squeeze_cd <= 0.0 and (b.x - pa.x) * (b.x - pc.x) < 0.0
			and absf(pa.x - pc.x) < 150.0 and b.y > K.GROUND - 125.0
			and clock - pa.contact < 0.25 and clock - pc.contact < 0.25):
		b.y = minf(b.y, K.GROUND - K.BALL_R - 4.0)
		b.vy = -780.0
		b.vx = rng.randf_range(-90.0, 90.0)
		b.spin = 0.0
		b.ignore_t = 0.3
		b.ignore_p = -2
		b.squeeze_cd = 0.6
		last_touch = -1
		events.append("pop")
	# son sinir kontrolu
	if b.y + K.BALL_R > K.GROUND:
		b.y = K.GROUND - K.BALL_R
		if b.vy > 0.0:
			b.vy = -b.vy * 0.5
	if b.x < K.BALL_R:
		b.x = K.BALL_R
		b.vx = absf(b.vx) * 0.5
	elif b.x > K.W - K.BALL_R:
		b.x = K.W - K.BALL_R
		b.vx = -absf(b.vx) * 0.5
	var sp := Vector2(b.vx, b.vy).length()
	var lim := K.SUPER_SPEED * 1.05 if b.mode != 0 else K.BALL_MAX
	if sp > lim:
		b.vx *= lim / sp
		b.vy *= lim / sp
	# doksan
	if phase == "play" and b.mode == 0 and b.post_cd <= 0.0:
		for side in 2:
			var lx := K.GOAL_D if side == 0 else K.W - K.GOAL_D
			var crossed := (b.px >= lx and lx > b.x) if side == 0 else (b.px <= lx and lx < b.x)
			if crossed and K.GOAL_TOP < b.y and b.y < K.GOAL_TOP + K.BALL_R + 24.0:
				var toward := -1.0 if side == 0 else 1.0
				var spv := b.spin * (1.0 if b.vx * toward > 0.0 else -1.0)
				var out_p := clampf(0.5 - 0.3 * spv, 0.15, 0.85)
				b.post_cd = 0.4
				events.append("post")
				if rng.randf() < out_p:
					b.x = lx - toward * (K.BALL_R + 2.0)
					b.vx = -b.vx * 0.5
					b.vy = absf(b.vy) * 0.3 + 160.0
					b.spin = -b.spin * 0.5
					events.append("doksan_out")
				else:
					b.vy = absf(b.vy) * 0.5 + 220.0
					b.vx *= 0.7
	if b.post_cd > 0.0:
		b.post_cd -= dt
	# gol
	if phase == "play":
		if b.x < K.GOAL_D - K.BALL_R * 0.6 and b.y > K.GOAL_TOP + 2.0:
			_goal(1)
		elif b.x > K.W - K.GOAL_D + K.BALL_R * 0.6 and b.y > K.GOAL_TOP + 2.0:
			_goal(0)


func _step_powerup(dt: float) -> void:
	if phase != "play":
		return
	var b := ball
	if pu == null:
		pu_timer -= dt
		if pu_timer <= 0.0:
			pu = [_choice(K.PU_KINDS), rng.randf_range(330.0, K.W - 330.0), rng.randf_range(260.0, 420.0), 9.0]
			events.append("pu_spawn")
	else:
		pu[3] -= dt
		if pu[3] <= 0.0:
			pu = null
			pu_timer = rng.randf_range(6.0, 10.0)
			return
		if Vector2(b.x - pu[1], b.y - pu[2]).length() < K.BALL_R + 32.0:
			_collect(pu[0])
			pu = null
			pu_timer = rng.randf_range(7.0, 12.0)


func _collect(kind: String) -> void:
	var i := last_touch
	if i < 0:
		i = 0 if ball.vx > 0.0 else 1
	var p: SimPlayer = players[i]
	var o: SimPlayer = players[1 - i]
	match kind:
		"speed":
			p.speed_t = 7.0
		"jump":
			p.jump_t = 7.0
		"shield":
			shield[i] = 6.0
		"freeze":
			o.frozen = 2.5
			events.append("freeze")
		"gold":
			p.meter = 100.0
	events.append("pu:%s:%d" % [kind, i])


func _goal(who: int) -> void:
	var b := ball
	var sp := int(Vector2(b.vx, b.vy).length())
	var kind := "super" if b.mode != 0 else last_kind
	var own := 1 if (last_touch >= 0 and last_touch != who) else 0
	goal_info = "%d:%s:%d:%d" % [who, kind, sp, own]
	score[who] += 1
	scorer = who
	phase = "goal"
	phase_t = 2.4
	events.append("goal:" + goal_info)
	ball.mode = 0
	shake = 0.5


# ------------------------------------------------------------ penaltilar
func _start_pens() -> void:
	pen = {"turn": 0, "res": [[], []], "t": 0.0, "c": [null, null], "shot": null}
	pu = null
	events.append("pens")
	_pen_setup()


func _pen_setup() -> void:
	var sh: int = pen["turn"]
	for p: SimPlayer in players:
		p.reset()
		p.armed = 0.0
		p.magnet_t = 0.0
		p.h = p.h0
	shield = [0.0, 0.0]
	glove = [0.0, 0.0]
	var shooter: SimPlayer = players[sh]
	var keeper: SimPlayer = players[1 - sh]
	var bx := K.W - 500.0 if sh == 0 else 500.0
	ball.reset(rng, bx, K.GROUND - K.BALL_R)
	ball.vx = 0.0
	shooter.x = bx - shooter.dir * 90.0
	keeper.x = K.W - K.GOAL_D - 40.0 if sh == 0 else K.GOAL_D + 40.0
	keeper.h = keeper.h0 * 0.7
	last_touch = -1
	pen["c"] = [null, null]
	pen["shot"] = null
	phase = "pen_ready"
	phase_t = 1.5


func _pen_shoot() -> void:
	var sh: int = pen["turn"]
	var kp := 1 - sh
	var c: Array = pen["c"]
	if c[sh] == null:
		c[sh] = [_choice([-1, 0, 1]), _choice([0, 1])]
	if c[kp] == null:
		c[kp] = [0, 0]
	var scol: int = c[sh][0]
	var srow: int = c[sh][1]
	var kcol: int = c[kp][0]
	var krow: int = c[kp][1]
	var out := 0
	if srow == 1 and scol != 0 and rng.randf() < 0.12:
		out = 2
	elif scol == kcol and (srow == krow or scol == 0):
		out = 1
	pen["shot"] = [scol, srow, kcol, krow, out]
	stats["shots"][sh] += 1
	if out == 1:
		stats["saves"][kp] += 1
	phase = "pen_shot"
	phase_t = K.PEN_SHOT_T
	events.append("pen_kick")


func _pen_result(out: int) -> void:
	var sh: int = pen["turn"]
	var goal := out == 0
	pen["res"][sh].append(1 if goal else 0)
	phase = "pen_res"
	phase_t = 1.4
	if goal:
		scorer = sh
		events.append("pen_goal:%d" % sh)
	elif out == 1:
		events.append("pen_save:%d" % sh)
	else:
		events.append("pen_miss:%d" % sh)


func _pen_next() -> void:
	var r0: Array = pen["res"][0]
	var r1: Array = pen["res"][1]
	var g0 := 0
	var g1 := 0
	for v in r0:
		g0 += v
	for v in r1:
		g1 += v
	var n0 := r0.size()
	var n1 := r1.size()
	var done := false
	if n0 <= 5 and n1 <= 5:
		if g0 > g1 + (5 - n1) or g1 > g0 + (5 - n0):
			done = true
	if n0 == n1 and n0 >= 5 and g0 != g1:
		done = true
	if done:
		for p: SimPlayer in players:
			p.h = p.h0
		winner = 0 if g0 > g1 else 1
		phase = "over"
		events.append("end")
		return
	pen["turn"] = 1 - pen["turn"]
	scorer = -1
	_pen_setup()


func _kickoff() -> void:
	for p: SimPlayer in players:
		p.reset()
	ball.reset(rng)
	shield = [0.0, 0.0]
	glove = [0.0, 0.0]
	phase = "ready"
	phase_t = 1.4
	last_touch = -1
	scorer = -1


func _end() -> void:
	phase = "over"
	if pen != null:
		return
	if score[0] > score[1]:
		winner = 0
	elif score[1] > score[0]:
		winner = 1
	else:
		winner = 2
	events.append("end")
	for p: SimPlayer in players:
		p.frozen = 0.0
		p.stun = 0.0


## Olaylari alip bosaltir (cizim/ses icin).
func take_events() -> Array:
	var ev := events
	events = []
	return ev


func take_shake() -> float:
	var s := shake
	shake = 0.0
	return s
