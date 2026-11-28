## Saha cizimi (dunya biriminde: 1280x720). Python'daki MatchScene._draw_main sirasini izler.
extends Node2D

var m  # match.gd
var add_layer: Node2D   # toplamali (isik) katman
var glows: Array = []   # [pos, r, col]

const STADIUMS := [
	{"bg": "stadium_night_clean.jpg", "boards": false, "crowd": "crowd_night.json",
		"mask": "crowd_mask_night.png", "light": 0.82, "ref_y": 494.0,
		"lamps": [Vector2(90, 80), Vector2(435, 194), Vector2(851, 194), Vector2(1180, 80)]},
	{"bg": "stadium_timsah_clean.jpg", "boards": true, "wx": {"rain": "stadium_timsah_rain_clean.jpg",
		"snow": "stadium_timsah_snow_clean.jpg"}, "crowd": "crowd_timsah.json",
		"mask": "crowd_mask_timsah.png", "light": 0.95, "lamps": [], "ref_y": 562.0},
]
const ADS := [["ULUDAĞ GAZOZ", Color8(255, 214, 60)], ["MATLI", Color8(255, 120, 90)],
	["TURKCELL", Color8(255, 205, 40)], ["ÖZDİLEK", Color8(255, 255, 255)],
	["KÖFTECİ YUSUF", Color8(255, 90, 80)]]
const P_COLORS := [Color8(70, 160, 255), Color8(255, 85, 85)]

var goal_back: Texture2D
var goal_front: Texture2D
# ahsap kale gorseli (goal_wood.png 1552x1036, inceltilmis): on direk sol kenari x=1405, kiris alti y=129, direk tabani y=1019
const GW_POST := 1405.0
const GW_BAR := 129.0
const GW_FOOT := 1019.0
var gsx := 0.21
var gsy := 1.0
var bg_node := Node2D.new()
var crowd: Crowd
var weather: Node2D


func _ready() -> void:
	goal_back = R.tex("goal_wood.png")
	goal_front = R.tex("goal_wood_post.png")
	gsy = (K.GROUND - K.GOAL_TOP) / (GW_FOOT - GW_BAR)
	add_layer = Node2D.new()
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	add_layer.material = mat
	add_layer.z_index = 5
	add_child(add_layer)
	add_layer.draw.connect(_draw_add)
	# arka plan ve taraftarlar sahnenin geri kalanindan once cizilir
	bg_node.show_behind_parent = true
	add_child(bg_node)
	bg_node.draw.connect(_draw_bg)
	crowd = Crowd.new()
	crowd.show_behind_parent = true
	add_child(crowd)
	weather = preload("res://scripts/game/weather.gd").new()
	weather.z_index = 4
	add_child(weather)


## match.gd stadyum belli olunca cagirir
func setup_stadium(idx: int, c0: int, c1: int) -> void:
	var st: Dictionary = STADIUMS[idx]
	weather.m = m
	crowd.setup(st["crowd"], st["mask"], st["light"])
	crowd.set_teams(c0, c1)
	crowd.fill = 0.0


func _draw_bg() -> void:
	if m == null or m.world == null:
		return
	var st: Dictionary = STADIUMS[m.stadium]
	var bgname: String = st["bg"]
	if st.has("wx") and st["wx"].has(m.world.weather):
		bgname = st["wx"][m.world.weather]
	# arka plan sahayi asagi/yukari tasarsa bos kalmasin diye biraz genis ciz
	bg_node.draw_texture_rect(R.tex(bgname), Rect2(-2, -2, K.W + 4, K.H + 4), false)


func glow(p: Vector2, r: float, c: Color) -> void:
	glows.append([p, r, c])


func _draw_add() -> void:
	for g in glows:
		R.glow(add_layer, g[0], g[1], g[2])


var last_dt := 1.0 / 60.0


func _process(dt: float) -> void:
	last_dt = dt
	glows.clear()
	if crowd.fans.size() > 0 and not (m != null and m.paused):
		crowd.update(dt)
		if crowd.fill < 1.0:
			crowd.fill = minf(1.0, crowd.fill + dt / 2.3)
	bg_node.queue_redraw()
	queue_redraw()


func _draw() -> void:
	if m == null or m.world == null:
		return
	var w: SimWorld = m.world
	var t: float = m.t
	var st: Dictionary = STADIUMS[m.stadium]
	if st["boards"]:
		_draw_boards(w)
	var li := 0
	for lp: Vector2 in st["lamps"]:
		glow(lp, 95.0 + 8.0 * sin(t * 2.0 + li), Color8(110, 110, 120))
		li += 1
	_draw_goal_back(w)
	# golgeler
	for p: SimPlayer in w.players:
		_shadow(p.x, p.y, 70.0)
	_shadow(w.ball.x, w.ball.y + K.BALL_R, 44.0)
	# guc topu
	if w.pu != null:
		_draw_pu(w.pu, t)
	_draw_ref(w, t)
	for i in 2:
		_draw_player(i, w.players[i], w, t)
	_draw_ball(w.ball, t)
	_draw_goal_front(w, t)
	_draw_particles()
	add_layer.queue_redraw()


func _shadow(x: float, y: float, wdt: float) -> void:
	var hgt := maxf(0.0, K.GROUND - y)
	var k := maxf(0.25, 1.0 - hgt / 420.0)
	var rw := wdt * k
	draw_set_transform(Vector2(x, K.GROUND + 3.0), 0.0, Vector2(1.0, 0.28))
	draw_circle(Vector2.ZERO, rw / 2.0 + 2.0, Color(0, 0, 0, 0.42 * k))
	draw_set_transform(Vector2.ZERO)


func _draw_boards(w: SimWorld) -> void:
	var y := 527.0
	var h := 24.0
	draw_rect(Rect2(0, y, K.W, h), Color8(12, 16, 34))
	var goal := w.phase == "goal"
	var x0 := 130.0
	var cell := (K.W - 2.0 * x0) / ADS.size()
	for i in ADS.size():
		var lab: String = "GOOOL!" if goal else ADS[i][0]
		var col: Color = Color8(255, 205, 60) if goal else ADS[i][1]
		R.text(self, lab, 15, Vector2(x0 + cell * (i + 0.5), y + h / 2.0), col, 0)
		if i > 0:
			draw_line(Vector2(x0 + cell * i, y + 3), Vector2(x0 + cell * i, y + h - 3), Color8(60, 80, 120), 1.5)
	for yy in range(0, int(h), 3):
		draw_line(Vector2(0, y + yy), Vector2(K.W, y + yy), Color(0, 0, 0, 0.25), 1.0)


func _goal_rect(side: int, tex: Texture2D, left_x: float) -> Rect2:
	var sz := Vector2(tex.get_width() * gsx, tex.get_height() * gsy)
	var gy := K.GOAL_TOP - GW_BAR * gsy
	if side == 0:
		return Rect2(left_x, gy, sz.x, sz.y)
	return Rect2(K.W - left_x - sz.x, gy, sz.x, sz.y)


func _draw_goal_back(w: SimWorld) -> void:
	var gx := K.GOAL_D - 4.0 - GW_POST * gsx
	for side in 2:
		var off := 0.0
		var rp = m.ripple
		if rp != null and rp[0] == side:
			off = 5.0 * exp(-rp[2] * 4.0) * sin(rp[2] * 40.0) * (-1.0 if side == 0 else 1.0)
		var r := _goal_rect(side, goal_back, gx)
		r.position.x += off
		R.draw_tex(self, goal_back, r, side == 1)
	# buz kalkani
	for i in 2:
		if w.glove[i] > 0.0 or w.shield[i] <= 0.0:
			continue
		var x := K.GOAL_D + 2.0 if i == 0 else K.W - K.GOAL_D - 2.0
		var al := 0.55 if (w.shield[i] > 1.5 or int(m.t * 10) % 2 == 0) else 0.25
		draw_rect(Rect2(x - 13, K.GOAL_TOP, 26, K.GROUND - K.GOAL_TOP), Color(0.55, 0.86, 1.0, al))
		draw_line(Vector2(x - 7, K.GOAL_TOP + 10), Vector2(x - 7, K.GROUND - 10), Color(1, 1, 1, 0.8), 2.0)
		glow(Vector2(x, (K.GOAL_TOP + K.GROUND) / 2.0), 90.0, Color(0.12, 0.27, 0.4))


func _draw_goal_front(w: SimWorld, t: float) -> void:
	for i in 2:
		if w.glove[i] <= 0.0 or not (w.glove[i] > 1.2 or int(t * 10) % 2 == 0):
			continue
		var x := K.GOAL_D + 26.0 if i == 0 else K.W - K.GOAL_D - 26.0
		var img := R.tex("fx_glove.png")
		glow(Vector2(x, K.GOAL_TOP + (K.GROUND - K.GOAL_TOP) * 0.5), 120.0, Color(0.24, 0.2, 0.04))
		if img:
			var hh := (K.GROUND - K.GOAL_TOP) * 0.92
			var ww := img.get_width() * hh / img.get_height()
			var bob := sin(t * 4.0) * 4.0
			var rr := Rect2(x - ww / 2.0, K.GROUND + 4.0 + bob - hh, ww, hh)
			R.draw_tex(self, img, rr, i == 1)
	# on direk oyuncu/topun onunde; top arkasindayken yari saydam olur (top kaybolmaz)
	var px := K.GOAL_D - 4.0 - 10.0 * gsx
	for side in 2:
		var r := _goal_rect(side, goal_front, px)
		var b := w.ball
		var behind := b.x + K.BALL_R > r.position.x and b.x - K.BALL_R < r.end.x and b.y > K.GOAL_TOP - K.ROOF_T
		R.draw_tex(self, goal_front, r, side == 1, Color(1, 1, 1, 0.55 if behind else 1.0))


func _draw_pu(pu: Array, t: float) -> void:
	var kind: String = pu[0]
	var img := R.tex("pu_%s.png" % kind)
	if img == null or not (pu[3] > 2.0 or int(t * 8) % 2 == 0):
		return
	var bob := sin(t * 3.0) * 8.0
	var c := Vector2(pu[1], pu[2] + bob)
	glow(c, 62.0 + 6.0 * sin(t * 6.0), Color(0.43, 0.39, 0.2))
	var s := 64.0 * (1.0 + 0.05 * sin(t * 6.0))
	draw_set_transform(c, deg_to_rad(sin(t * 2.5) * 10.0), Vector2.ONE)
	draw_texture_rect(img, Rect2(-s / 2.0, -s / 2.0, s, s), false)
	draw_set_transform(Vector2.ZERO)


func _draw_ref(w: SimWorld, t: float) -> void:
	# Hakem sahaya girmez: reklam panolarinin onunde, kucuk boyda topu uzaktan takip eder (Python ile ayni).
	var pose: String = m.ref_pose[0] if m.ref_pose[1] > 0.0 else "idle"
	var img := R.tex("ref_%s.png" % pose)
	if img == null:
		img = R.tex("ref_idle.png")
	if img == null:
		return
	var h := 132.0 * 0.46
	var ww := img.get_width() * h / img.get_height()
	var x: float = m.ref_x
	# ayaklar reklam panolarinin hemen onunde (sahanin uzak kenari)
	var y: float = STADIUMS[m.stadium]["ref_y"]
	draw_set_transform(Vector2(x, y + 2.0), 0.0, Vector2(1.0, 0.28))
	draw_circle(Vector2.ZERO, 17.0, Color(0, 0, 0, 0.35))
	draw_set_transform(Vector2.ZERO)
	R.draw_tex(self, img, Rect2(x - ww / 2.0, y - h, ww, h), w.ball.x < x)


# ---------------------------------------------------------------- oyuncular
func _player_pose(p: SimPlayer, w: SimWorld, i: int) -> Array:
	var ice := p.frozen > 0.0
	var celebrate: bool = (w.phase == "goal" and w.scorer == i) or (w.phase == "over" and w.winner == i)
	if p.slide_t > 0.0:
		return ["kick", "slide", "kick"]
	if p.bike_t > 0.0:
		return ["bike", "bike", "bike"]
	if p.shoulder_t > 0.0:
		return ["shoulder", "shoulder", "shoulder"]
	if p.kick_t > 0.04:
		return ["kick", "kick", "kick"]
	if celebrate:
		return ["celeb", "celeb", "celeb"]
	if not p.on_ground:
		return ["jump", "jump", "jump"]
	if p.on_ground and absf(p.vx) > 40.0 and not ice:
		var fr := "run1" if int(p.run_t * 9.0) % 2 == 0 else "run2"
		return [fr, "run", fr]
	return ["idle", "idle", "idle"]


## Sut aninda ayagin arkasinda hafif bir ruzgar izi (hizli bacak savurma hissi).
func _kick_swoosh(p: SimPlayer, h: float) -> void:
	var k := clampf(1.0 - p.kick_t / 0.24, 0.0, 1.0)
	var e := 1.0 - pow(1.0 - minf(1.0, k * 1.6), 3.0)
	var fdir := float(p.face)
	var hip := Vector2(p.x + fdir * h * 0.02, p.y - h * 0.4)
	var rad := h * 0.36
	var a0 := PI / 2.0 + fdir * 0.55      # arkada-asagi
	var a1 := PI / 2.0 - fdir * 1.45      # onde, kalca hizasi
	var cur := lerpf(a0, a1, e)
	var fade := 1.0 - maxf(0.0, (k - 0.55) / 0.45)
	var n := 12
	for layer in 3:
		var rr := rad * (1.0 + 0.09 * layer)
		var prev := hip + Vector2(cos(a0), sin(a0)) * rr
		for j in range(1, n + 1):
			var u := float(j) / n
			var ang := lerpf(a0, cur, u)
			var pt := hip + Vector2(cos(ang), sin(ang)) * rr
			var al := 0.42 * u * fade * (1.0 - 0.3 * layer)
			draw_line(prev, pt, Color(1, 1, 1, al), (1.0 + 3.5 * u) * (1.0 - 0.25 * layer), true)
			prev = pt


## Poz resimlerinden hareketler (sut, kafa/ziplama, kayma, omuz, rovasata, sevinc, sersemleme).
## Bir hareket cizildiyse true. Pozlar arasi yumusak gecis; yerdeyken ayaktan, havadayken yuzden (fizik kafasi) hizalanir.
func _hero_poses(p: SimPlayer, w: SimWorld, i: int, ps: Dictionary, rn: String, hc: float, flip: bool, modr: Color) -> bool:
	var ft := Vector2(p.x, p.y)
	var air := not p.on_ground
	if p.stun > 0.0 and Anim.is_poses(rn, "hurt"):
		ps["stun_max"] = maxf(float(ps.get("stun_max", 0.0)), p.stun)
		var u: float = 1.0 - p.stun / maxf(0.05, float(ps["stun_max"]))
		var sh: float
		if u < 0.18:
			sh = 0.0
		elif u < 0.32:
			sh = (u - 0.18) / 0.14
		elif u < 0.8:
			sh = 1.5 + 0.5 * sin(u * 26.0)    # sendeleme: 1 ile 2 arasi sallanir
		else:
			sh = 2.0 + (u - 0.8) / 0.2
		var ha := mini(int(floor(sh)), 3)
		Anim.draw_pose(self, rn, "hurt", ha, mini(ha + 1, 3), sh - ha, ft, hc, flip, air, modr)
		return true
	ps["stun_max"] = 0.0
	if p.slide_t > 0.0 and Anim.is_poses(rn, "special"):
		Anim.draw_pose(self, rn, "special", 0, 0, 0.0, ft, hc, flip, false, modr)
		return true
	if p.shoulder_t > 0.0 and Anim.is_poses(rn, "special"):
		Anim.draw_pose(self, rn, "special", 1, 1, 0.0, ft, hc, flip, air, modr)
		return true
	if p.bike_t > 0.0 and Anim.is_poses(rn, "special"):
		var ub: float = clampf((1.0 - p.bike_t / 0.5) * 2.0, 0.0, 1.0)
		Anim.draw_pose(self, rn, "special", 2, 3, ub, ft + Vector2(0, -hc * 0.35), hc, flip, false, modr)
		return true
	if p.kick_t > 0.0 and Anim.is_poses(rn, "kick"):
		# 0.24 sn: geri cekis (1) -> vurus (2) -> takip (3) -> toparlanma (4)
		var uk: float = clampf(1.0 - p.kick_t / 0.24, 0.0, 1.0)
		var sk: float = 1.0 + 3.0 * uk
		var ka := mini(int(floor(sk)), 4)
		Anim.draw_pose(self, rn, "kick", ka, mini(ka + 1, 4), sk - ka, ft, hc, flip, air, modr)
		return true
	var celebrate: bool = (w.phase == "goal" and w.scorer == i) or (w.phase == "over" and w.winner == i)
	if celebrate and not air and Anim.is_poses(rn, "celeb"):
		var tc: float = float(ps.get("an_t", 0.0)) / 0.42
		var ca := posmod(int(floor(tc)), 4)
		var cf: float = clampf((fmod(tc, 1.0) - 0.7) / 0.3, 0.0, 1.0)    # pozda dur, sonra hizli gecis
		var hop := 18.0 if ca == 1 else 0.0
		Anim.draw_pose(self, rn, "celeb", ca, (ca + 1) % 4, cf, ft + Vector2(0, -hop * (1.0 - cf)), hc, flip, false, modr)
		return true
	if Anim.is_poses(rn, "jump"):
		if air:
			# yukselirken 1 (sicrama), tepede 2 (topuk toplu kafa), duserken 3 (inise hazir)
			var uj: float = clampf(-p.vy / 600.0, -0.35, 0.35)
			var sj: float = 1.0 + 2.0 * (0.35 - uj) / 0.7
			var ja := int(floor(sj))
			Anim.draw_pose(self, rn, "jump", ja, mini(ja + 1, 3), sj - ja, ft, hc, flip, true, modr)
			return true
		if float(ps.get("land_t", 0.0)) > 0.0:
			Anim.draw_pose(self, rn, "jump", 0, 0, 0.0, ft, hc, flip, false, modr)
			return true
	return false


## Video animasyonu durumu
func _anim_state(p: SimPlayer, w: SimWorld, i: int) -> String:
	var celebrate: bool = (w.phase == "goal" and w.scorer == i) or (w.phase == "over" and w.winner == i)
	if p.stun > 0.0:
		return "hurt"
	if p.kick_t > 0.0 or p.bike_t > 0.0 or p.slide_t > 0.0:
		return "kick"
	if celebrate:
		return "celeb"
	if not p.on_ground:
		return "jump"
	if absf(p.vx) > 40.0 and p.frozen <= 0.0:
		return "run"
	return "idle"


func _draw_player(i: int, p: SimPlayer, w: SimWorld, t: float) -> void:
	var pr := _player_pose(p, w, i)
	var pose: String = pr[1]
	var akey: String = pr[2]
	var tex: Texture2D = null
	var f := 1.0
	if not Rig.has(p.char):
		tex = R.pose(p.char, pr[0])
		f = K.BASE_H * p.stats["scale"] / R.pose(p.char, "idle").get_height()
	var h: float = K.BASE_H * p.stats["scale"]
	var flip := p.face < 0
	# geriye kosarken arkasi donuk "ay yuruyusu" olmasin: kostugu yone baksin (sut/kafa aninda yine rakibe doner)
	if p.on_ground and absf(p.vx) > 40.0 and p.kick_t <= 0.0 and p.slide_t <= 0.0 and p.shoulder_t <= 0.0 and p.frozen <= 0.0:
		flip = p.vx < 0.0
	var tilt := 0.0
	var bob := 0.0
	var ps: Dictionary = m.pstate[i]
	if p.kick_t > 0.0:
		_kick_swoosh(p, h)
	if (pose == "idle" or pose == "run") and p.on_ground and absf(p.vx) > 40.0 and p.frozen <= 0.0:
		bob = absf(sin(p.run_t * 14.0)) * (5.0 if pose == "idle" else 3.0)
		tilt = sin(p.run_t * 14.0) * (4.0 if pose == "idle" else 2.0) + (3.0 if pose == "run" else 0.0) * (1.0 if p.vx > 0 else -1.0)
	if pose == "idle" and p.frozen <= 0.0 and p.on_ground and absf(p.vx) <= 40.0:
		bob = sin(t * 3.0 + i) * 1.2
	if pose == "celeb" or (w.phase == "goal" and w.scorer == i and p.on_ground):
		bob = absf(sin(t * 9.0)) * 16.0
	if p.stun > 0.0:
		tilt = sin(t * 30.0) * 12.0
	if not p.on_ground and pose != "kick":
		tilt = (-6.0 * p.face) if p.vx * p.face > 0 else 0.0
	if pose == "slide":
		tilt = 28.0 * p.face
	var sx := 1.0
	var sy := 1.0
	if p.h < p.h0 - 1.0 and pose == "idle":
		sy = 0.74
		sx = 1.12
	if ps["sq"] > 0.0:
		var k: float = ps["sq"] / 0.16
		sx = 1.0 + 0.16 * k
		sy = 1.0 - 0.14 * k
	elif ps["st"] > 0.0:
		var k2: float = ps["st"] / 0.16
		sx = 1.0 - 0.08 * k2
		sy = 1.0 + 0.1 * k2
	if p.armed > 0.0:
		var pc: Color = K.POWERS[p.stats["power"]][1]
		glow(Vector2(p.x, p.y - h * 0.5), 95.0 + 8.0 * sin(t * 12.0), pc * 0.45)
	if Rig.has(p.char):
		# iskelet animasyonu
		if not ps.has("rig"):
			ps["rig"] = Rig.rest()
		var tq := Rig.target(p, w, i, t)
		Rig.blend(ps["rig"], tq, last_dt, p.kick_t > 0.0 or p.bike_t > 0.0)
		var modr := Color(0.7, 0.88, 1.0) if p.frozen > 0.0 else Color.WHITE
		var rrot := deg_to_rad(tilt * (1.0 if not flip else -1.0)) * 0.5 if (p.stun > 0.0 or pose == "slide") else 0.0
		# cizim boyu: gorsel kafa merkezi = fizik kafa merkezi
		var hc: float = p.h0 - p.head_r - 4.0 * K.SIZE
		var rname := Rig.rig_of(p.char)
		var an := _anim_state(p, w, i)
		if an != ps.get("an", ""):
			ps["an"] = an
			ps["an_t"] = 0.0
		var rate := 1.0
		if an == "run":
			var gs := Anim.ground_speed(rname, an, hc)
			if gs > 0.0:
				rate = clampf(absf(p.vx) / gs, 0.5, 2.2)
		ps["an_t"] = float(ps.get("an_t", 0.0)) + last_dt * rate
		# inis: yere degdikten sonra kisa bir comelme pozu
		var was_air: bool = ps.get("air", false)
		ps["air"] = not p.on_ground
		if was_air and p.on_ground:
			ps["land_t"] = 0.13
		ps["land_t"] = maxf(0.0, float(ps.get("land_t", 0.0)) - last_dt)
		if _hero_poses(p, w, i, ps, rname, hc, flip, modr):
			pass
		elif an == "jump" and not Anim.has(rname, "jump") and Anim.air_frame(rname) >= 0:
			# gecici ziplama: kosu videosunun iki ayagin da havada oldugu karesi + fizik yonlu egim/esneme
			var up: float = clampf(-p.vy / 600.0, -1.0, 1.0)
			var jtilt: float = (-0.10 * up if up > 0.0 else 0.12 * -up) * (-1.0 if flip else 1.0)
			var st := Vector2(sx * (1.0 - 0.05 * absf(up)), sy * (1.0 + 0.07 * absf(up)))
			Anim.draw(self, rname, "run", Anim.air_frame(rname) / Anim.fps(rname, "run"), Vector2(p.x, p.y), hc, flip, modr, st, rrot + jtilt)
		elif Anim.has(rname, an):
			Anim.draw(self, rname, an, ps["an_t"] + i * 0.37, Vector2(p.x, p.y), hc, flip, modr, Vector2(sx, sy), rrot)
		else:
			Rig.draw(self, p.char, ps["rig"], Vector2(p.x, p.y - bob * 0.3), Rig.fit_h(Rig.rig_of(p.char), hc), flip, modr, Vector2(sx, sy), rrot)
	else:
		var size: Vector2 = Vector2(tex.get_width(), tex.get_height()) * f * Vector2(sx, sy)
		var ax := R.anchor(p.char, akey, 0.40 if pose == "kick" else 0.5)
		# kafa hizasi: her pozda kafa oyuncunun x konumunda dursun; ayna icin olcek -1
		var pivot := Vector2(p.x, p.y - bob)
		var rot := deg_to_rad(tilt * (1.0 if not flip else -1.0)) if tilt != 0.0 else 0.0
		draw_set_transform(pivot, rot, Vector2(-1.0 if flip else 1.0, 1.0))
		var rr := Rect2(-size.x * ax, -size.y, size.x, size.y)
		var modc := Color(0.7, 0.88, 1.0) if p.frozen > 0.0 else Color.WHITE
		draw_texture_rect(tex, rr, false, modc)
		draw_set_transform(Vector2.ZERO)
	if p.frozen > 0.0:
		var blk := Rect2(p.x - 48, p.y + 4 - (h + 26), 96, h + 26)
		R.panel(self, blk, Color(0.59, 0.86, 1.0, 0.27), 14, Color8(220, 245, 255), 3)
		R.text(self, "%.1f" % p.frozen, 20, Vector2(p.x, blk.position.y - 14), Color8(110, 220, 255), 3)
	if p.stun > 0.0:
		var stars := R.tex("fx_stars.png")
		if stars:
			var sw := 46.0
			var sh := stars.get_height() * sw / stars.get_width() * 0.45
			draw_texture_rect(stars, Rect2(p.x - sw / 2 + sin(t * 6.0) * 4.0, p.y - h - 6 - sh / 2, sw, sh), false)
	if p.jump_t > 0.0:
		draw_set_transform(Vector2(p.x, p.y), 0.0, Vector2(1.0, 0.22))
		draw_arc(Vector2.ZERO, 32.0, 0, TAU, 32, Color8(120, 255, 160), 3.0 / 0.22 * 0.3)
		draw_set_transform(Vector2.ZERO)
	# sarj cubugu
	if p.charging:
		var cb := Rect2(p.x - 35, p.y - h - 58 - bob - 6, 70, 12)
		R.panel(self, cb.grow(2), Color(0.05, 0.06, 0.14, 0.9), 7)
		var col := Color8(120, 230, 120) if p.charge < 0.5 else (Color8(255, 200, 60) if p.charge < 0.95 else Color8(255, 90, 50))
		R.panel(self, Rect2(cb.position, Vector2(cb.size.x * p.charge, cb.size.y)), col, 6)
		if p.lob and p.on_ground:
			R.text(self, "AŞIRTMA", 12, Vector2(cb.get_center().x, cb.position.y - 10), Color8(150, 235, 255), 2)
	# etiket
	var label: String = m.label_for(i)
	if label != "":
		var ty: float = p.y - h - 30.0 + sin(t * 5.0) * 3.0 - bob
		var tw := 52.0 if label.length() <= 3 else 64.0
		var tg := Rect2(p.x - tw / 2.0, ty - 11.0, tw, 22.0)
		var pc2: Color = P_COLORS[i]
		draw_colored_polygon(PackedVector2Array([Vector2(p.x - 9, tg.end.y - 2), Vector2(p.x + 9, tg.end.y - 2), Vector2(p.x, tg.end.y + 9)]), Color8(12, 14, 34))
		draw_colored_polygon(PackedVector2Array([Vector2(p.x - 6, tg.end.y - 2), Vector2(p.x + 6, tg.end.y - 2), Vector2(p.x, tg.end.y + 6)]), pc2)
		R.panel(self, tg, pc2, 9, Color8(12, 14, 34), 2)
		R.text(self, label, 13, Vector2(p.x, ty), Color.WHITE, 2, HORIZONTAL_ALIGNMENT_CENTER, false)


func _draw_ball(b: SimBall, t: float) -> void:
	var sp := maxf(1.0, Vector2(b.vx, b.vy).length())
	var img: Texture2D
	var d := K.BALL_R * 2.0 + 2.0
	if b.mode == 1 or b.mode == 2:
		var dirv := Vector2(-b.vx, -b.vy) / sp
		glow(Vector2(b.x, b.y), 80.0, Color(0.59, 0.27, 0.04) if b.mode == 1 else Color(0.16, 0.43, 0.63))
		var trail := R.tex("fx_fire.png" if b.mode == 1 else "fx_ice.png")
		if trail:
			var tw := 150.0
			var th := trail.get_height() * tw / trail.get_width()
			var c := Vector2(b.x, b.y) + dirv * tw * 0.38
			draw_set_transform(c, atan2(dirv.y, dirv.x), Vector2.ONE)
			draw_texture_rect(trail, Rect2(-tw / 2.0, -th / 2.0, tw, th), false)
			draw_set_transform(Vector2.ZERO)
		img = R.tex("ball_fire.png" if b.mode == 1 else "ball_ice.png")
	else:
		img = R.tex("ball.png")
	if b.mode == 0 and sp > 750.0:
		var k := minf(1.0, (sp - 750.0) / 700.0)
		for jj in [[3, 0.2], [2, 0.31], [1, 0.47]]:
			var gpos := Vector2(b.x - b.vx * 0.011 * jj[0], b.y - b.vy * 0.011 * jj[0])
			draw_set_transform(gpos, b.ang, Vector2.ONE)
			draw_texture_rect(img, Rect2(-d / 2, -d / 2, d, d), false, Color(1, 1, 1, jj[1] * k))
	draw_set_transform(Vector2(b.x, b.y), b.ang, Vector2.ONE)
	draw_texture_rect(img, Rect2(-d / 2, -d / 2, d, d), false)
	draw_set_transform(Vector2.ZERO)


func _draw_particles() -> void:
	for q in m.parts:
		var life: float = q["life"]
		var mx: float = q["max"]
		var a := clampf(life / mx * 1.6, 0.0, 1.0)
		var c: Color = q["col"]
		c.a *= a
		match q["kind"]:
			"dot":
				draw_circle(q["p"], q["size"] * (0.5 + 0.5 * life / mx), c)
			"ring":
				var k := 1.0 - life / mx
				draw_arc(q["p"], 10.0 + q["size"] * k, 0, TAU, 40, c, maxf(1.0, 5.0 * (1.0 - k)))
			"conf":
				draw_set_transform(q["p"], q["rot"], Vector2.ONE)
				draw_rect(Rect2(-5, -3, 10, 6), c)
				draw_set_transform(Vector2.ZERO)
			"tex":
				var tx: Texture2D = q["tex"]
				var s: float = q["size"] * (1.0 + (1.0 - life / mx) * 0.6)
				var ww := s
				var hh := tx.get_height() * s / tx.get_width()
				draw_texture_rect(tx, Rect2(q["p"] - Vector2(ww, hh) / 2.0, Vector2(ww, hh)), false, Color(1, 1, 1, a))
