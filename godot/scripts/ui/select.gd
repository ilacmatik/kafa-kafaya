## Karakter secimi (bilgisayara karsi): 1. adim kendi karakterin, 2. adim rakibin.
## Secilen karakter one cikar; maç ayarlari (zorluk, sure, stadyum, hava) ortada.
extends UIScreen

const PODIUMS := [147.0, 344.0, 541.0, 738.0, 936.0, 1133.0]
const STAT_LABELS := ["HIZ", "ZIPLAMA", "ŞUT"]
const STAT_ICONS := ["st_speed.png", "st_jump.png", "st_shot.png"]

var pick := [0, 3]
var step := 0
var focus_k := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
var anim := [[-1, 0.0], [-1, 0.0]]
var roll := 0.0
var roll_tick := 0.0
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	rng.randomize()
	pick = Game.chars.duplicate()
	if pick[0] == pick[1]:
		pick[1] = (pick[0] + 3) % 6


func tick(dt: float) -> void:
	for i in 6:
		var tgt := 1.0 if (pick[0] == i or pick[1] == i) else 0.0
		focus_k[i] += (tgt - focus_k[i]) * minf(1.0, dt * 10.0)
	for w in 2:
		if anim[w][0] != pick[w]:
			anim[w] = [pick[w], 0.0]
		anim[w][1] += dt
	if roll > 0.0:
		roll -= dt
		roll_tick -= dt
		if roll_tick <= 0.0:
			roll_tick = 0.06 + (0.75 - roll) * 0.12
			pick[step] = (pick[step] + 1 + rng.randi_range(0, 4)) % 6
			play("click")


# ---------------------------------------------------------------- girdi
func on_tap(name: String) -> void:
	if name.begins_with("hero"):
		var i := int(name.substr(4))
		if roll > 0.0:
			return
		if pick[step] == i:
			_next()
		else:
			pick[step] = i
			play("click")
		return
	match name:
		"back":
			on_back()
		"next":
			_next()
		"rand":
			if roll <= 0.0:
				roll = 0.75
		"lvl":
			Game.level = (Game.level + 1) % 3
			play("click")
		"dur":
			var i := Game.DURATIONS.find(Game.duration)
			Game.duration = Game.DURATIONS[(i + 1) % Game.DURATIONS.size()]
			play("click")
		"stad":
			Game.stadium = (Game.stadium + 1) % Game.STADIUM_NAMES.size()
			play("click")
		"wx":
			var j := 0
			for k in Game.WEATHERS.size():
				if Game.WEATHERS[k][0] == Game.weather:
					j = k
			Game.weather = Game.WEATHERS[(j + 1) % Game.WEATHERS.size()][0]
			play("click")


func on_key(kc: int) -> void:
	match kc:
		KEY_LEFT, KEY_A:
			pick[step] = (pick[step] + 5) % 6
			play("click")
		KEY_RIGHT, KEY_D:
			pick[step] = (pick[step] + 1) % 6
			play("click")
		KEY_ENTER, KEY_SPACE, KEY_KP_ENTER:
			_next()
		KEY_R:
			on_tap("rand")
		KEY_Z:
			on_tap("lvl")
		KEY_T:
			on_tap("dur")
		KEY_Y:
			on_tap("stad")
		KEY_H:
			on_tap("wx")


func on_back() -> void:
	play("click")
	if step == 1:
		step = 0
	else:
		Game.go("res://scenes/menu.tscn")


func _next() -> void:
	if roll > 0.0:
		return
	play("kick")
	if step == 0:
		step = 1
		if pick[1] == pick[0]:
			pick[1] = (pick[0] + 3) % 6
	else:
		Game.chars = pick.duplicate()
		Game.start_match()


# ---------------------------------------------------------------- cizim
func paint() -> void:
	fit_mirror(R.tex("sel_bg.jpg"))
	for who in 2:
		_panel(who)
	# orta amblem
	R.glow(self, Vector2(640, 118), 90, Color(0.25, 0.45, 0.85, 0.45))
	R.text(self, "VS", 64, Vector2(640, 116 + sin(t * 3.0) * 3.0), GOLD, 6)
	_chips()
	_heroes()
	_bottom()


func _panel(who: int) -> void:
	var c: int = pick[who]
	var left := who == 0
	var pc := Vector2(118, 124) if left else Vector2(LW - 118, 124)
	var col: Color = P_COLORS[who]
	var active := step == who
	R.glow(self, pc, 80, Color(col.r, col.g, col.b, 0.35 if active else 0.18))
	draw_circle(pc, 60, Color8(8, 12, 30))
	draw_circle(pc, 57, col)
	draw_circle(pc, 52, Color8(14, 22, 50))
	draw_arc(pc, 57, 0, TAU, 64, Color8(140, 210, 255), 2.0, true)
	R.draw_tex(self, R.portrait_pop(c, 192), R.pop_rect(pc + Vector2(0, 2), 53.0), not left)
	var tx := 196.0 if left else 800.0
	R.text(self, K.DISPLAY_NAMES[c], 30, Vector2(tx, 66), WHITE, 4, HORIZONTAL_ALIGNMENT_LEFT)
	var prog: float = anim[who][1]
	for j in 3:
		var y := 104.0 + j * 25.0
		var ic := R.tex(STAT_ICONS[j])
		if ic:
			draw_texture_rect(ic, Rect2(tx, y - 12, 24, 24), false)
		R.text(self, STAT_LABELS[j], 14, Vector2(tx + 30, y), Color8(205, 218, 245), 2, HORIZONTAL_ALIGNMENT_LEFT)
		var val: int = K.STAT_BARS[c][j]
		for k in 5:
			var on := k < val and prog * 10.0 > j * 2 + k
			var seg := "seg_empty.png"
			if on:
				seg = "seg_green_glow.png" if val >= 5 else "seg_gold.png"
			var st := R.tex(seg)
			if st:
				draw_texture_rect(st, Rect2(tx + 116 + k * 27 - 11, y - 11, 22, 22), false)
	var pw: String = K.CHARACTERS[c]["power"]
	var pi := R.tex("pw_%s.png" % pw)
	if pi == null:
		pi = R.tex("fx_%s.png" % pw)
	if pi:
		draw_texture_rect(pi, Rect2(tx, 172, 24, 24), false)
	R.text(self, K.POWERS[pw][0], 18, Vector2(tx + 30, 184), K.POWERS[pw][1], 3, HORIZONTAL_ALIGNMENT_LEFT)
	# durum hapi
	var lab := "SEN" if left else "BİLGİSAYAR"
	var st2 := ""
	var scol := col.darkened(0.15)
	if who == 0:
		st2 = "HAZIR" if step == 1 else "SEÇİYOR" + ".".repeat(int(t * 2.0) % 4)
		if step == 1:
			scol = Color8(40, 170, 70)
	else:
		st2 = "SEÇİLİYOR" + ".".repeat(int(t * 2.0) % 4) if step == 1 else "ZORLUK: " + Game.LEVELS[Game.level]
		if step == 0:
			scol = Color8(120, 70, 200)
	var tag := Rect2((277.0 if left else LW - 277.0) - 135, 221, 270, 34)
	R.panel(self, tag, scol, 15, Color(1, 1, 1, 0.7), 2)
	R.text(self, "%s  ·  %s" % [lab, st2], 16, tag.get_center() - Vector2(0, 1), WHITE, 2)


func _chips() -> void:
	var items := [
		["lvl", "ZORLUK", Game.LEVELS[Game.level], [Color8(60, 160, 80), Color8(200, 140, 30), Color8(200, 60, 60)][Game.level]],
		["dur", "SÜRE", "%d SN" % int(Game.duration), Color8(40, 70, 150)],
		["stad", "STADYUM", Game.STADIUM_NAMES[Game.stadium], Color8(30, 120, 60) if Game.stadium == 1 else Color8(40, 60, 130)],
		["wx", "HAVA", Game.weather_name(Game.weather),
			{"clear": Color8(200, 140, 30), "rain": Color8(50, 90, 160), "snow": Color8(120, 150, 190),
			"wind": Color8(60, 140, 150), "random": Color8(110, 70, 160)}.get(Game.weather, Color8(60, 60, 90))],
	]
	for n in items.size():
		var it: Array = items[n]
		var r := Rect2(463 + (n % 2) * 182, 214 + (n / 2) * 52, 172, 44)
		reg(it[0], r)
		var pk := pressed_k(it[0])
		var rr := r.grow(-3.0 * pk)
		R.panel(self, rr.grow(2), Color(0, 0, 0, 0.5), 18)
		R.panel(self, rr, it[3], 16, GOLD if focus == it[0] else Color(1, 1, 1, 0.75), 2)
		R.text(self, it[1], 11, Vector2(rr.get_center().x, rr.position.y + 11), Color(1, 1, 1, 0.8), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
		R.text(self, it[2], 17, Vector2(rr.get_center().x, rr.position.y + 29), WHITE, 2)


func _heroes() -> void:
	var order := [0, 1, 2, 3, 4, 5]
	order.sort_custom(func(a, b): return focus_k[a] < focus_k[b])
	for i: int in order:
		var cx: float = PODIUMS[i]
		var sel0: bool = pick[0] == i
		var sel1: bool = pick[1] == i and step == 1
		var f: float = focus_k[i]
		reg("hero%d" % i, Rect2(cx - 90, 340, 180, 330))
		var cur: bool = pick[step] == i
		if sel0 or sel1:
			var col: Color = P_COLORS[0] if (sel0 and (step == 0 or not sel1)) else P_COLORS[1]
			if cur:
				col = P_COLORS[step]
			R.glow(self, Vector2(cx, 600), 130 + 8 * sin(t * 5.0), Color(col.r, col.g, col.b, 0.45))
			draw_set_transform(Vector2(cx, 607), 0.0, Vector2(1.0, 0.15))
			draw_arc(Vector2.ZERO, 92, 0, TAU, 64, col, 5.0 / 0.15 * 0.2, true)
			draw_set_transform(Vector2.ZERO)
		var img := R.tex("sel_hero%d.png" % i)
		var sc := 0.9 + 0.22 * f
		var hh: float = 236.0 * K.CHARACTERS[i]["scale"] * sc
		var ww := img.get_width() * hh / img.get_height() if img else 0.0
		var bob := sin(t * 3.0 + i) * 2.0 if (sel0 or sel1) else 0.0
		if step == 1 and sel0 and not sel1:
			bob = absf(sin(t * 8.0 + i)) * 6.0   # hazir: hoplar
		var foot := 602.0 + 14.0 * f
		var al := 0.55 + 0.45 * f
		if img:
			# rakip sagda: ona bakacak sekilde aynala
			R.draw_tex(self, img, Rect2(cx - ww / 2.0, foot - bob - hh, ww, hh), sel1 and not sel0, Color(al, al, al + 0.04, 1.0))
		R.text(self, K.DISPLAY_NAMES[i], int(19 + 5 * f), Vector2(cx, 632 + 4 * f), GOLD if (sel0 or sel1) else Color8(200, 205, 220), 3)
		var tags := []
		if sel0:
			tags.append([0, "SEN"])
		if sel1:
			tags.append([1, "RAKİP"])
		for n in tags.size():
			var who: int = tags[n][0]
			var ty := 340.0 - n * 32.0 + sin(t * 5.0) * 3.0 - 30.0 * f
			var tg := Rect2(cx - 55, ty - 13, 110, 26)
			draw_colored_polygon(PackedVector2Array([Vector2(cx - 9, tg.end.y - 2), Vector2(cx + 9, tg.end.y - 2), Vector2(cx, tg.end.y + 9)]), P_COLORS[who])
			R.panel(self, tg, P_COLORS[who], 11, WHITE, 2)
			R.text(self, tags[n][1], 14, tg.get_center() - Vector2(0, 1), WHITE, 2)


func _bottom() -> void:
	var y := 668.0
	flat_button("back", Rect2(maxf(view_l + 14, -200) , y, 130, 44), "GERİ", Color8(60, 70, 110), 22)
	var nr := Rect2(minf(view_r - 14, LW + 200) - 250, y - 6, 250, 54)
	reg("next", nr)
	var on := focus == "next"
	var pk := pressed_k("next")
	var rr := nr.grow(-4.0 * pk + 2.0 * sin(t * 4.0))
	R.glow(self, rr.get_center(), 150, Color(1, 0.8, 0.3, 0.35))
	slice3(R.tex("m2_gold.png"), rr)
	R.text(self, "DEVAM ▶" if step == 0 else "MAÇA BAŞLA ▶", 24, rr.get_center(), Color8(40, 26, 6), 0)
	flat_button("rand", Rect2(maxf(view_l + 14, -200) + 142, y, 150, 44), "RASTGELE", Color8(150, 60, 170), 20)
	var msg := "1. ADIM: KENDİ KARAKTERİNİ SEÇ" if step == 0 else "2. ADIM: RAKİBİNİ SEÇ"
	R.text(self, msg, 22, Vector2(LW / 2.0 + 40, y + 22), GOLD if step == 0 else Color8(255, 140, 120), 4)
