## Ana menu: solda buyuk dugmeler, sagda isikli sahnede karsi karsiya iki karakter.
extends UIScreen

const BIG := ["bot", "online", "cup"]
const SMALL := ["settings", "exit"]
const INFO := {
	"bot": ["BİLGİSAYARA KARŞI", "Bilgisayara karşı tek maç oyna. Zorluğu sen seç.", "bot"],
	"online": ["ARKADAŞINLA", "Aynı Wi-Fi'de ya da hotspot ile arkadaşına karşı oyna.", "host"],
	"cup": ["KUPA YOLU", "5 maçlık kupa yolunu tamamla, kupayı kaldır.", "cup"],
	"keys": ["KONTROLLER", "Tuşlar, özel hareketler ve süper güçler.", "keys"],
	"settings": ["AYARLAR", "Ses, titreşim, kare hızı, kontroller ve istatistikler.", "keys"],
	"exit": ["ÇIKIŞ", "Oyundan çık.", "exit"],
}
const VERSION := "Godot 2.0 önizleme"

var pair := [0, 3]
var pair_t := 0.0
var sparks: Array = []
var help_open := false
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	rng.randomize()
	_new_pair()
	focus = "bot"
	for i in 26:
		sparks.append([rng.randf_range(0, LW), rng.randf_range(0, LH), rng.randf_range(10, 30), rng.randf_range(0, TAU), rng.randf_range(1.5, 3.5)])


func _new_pair() -> void:
	var a := rng.randi_range(0, K.CHARACTERS.size() - 1)
	pair = [a, (a + 1 + rng.randi_range(0, K.CHARACTERS.size() - 2)) % K.CHARACTERS.size()]


func tick(dt: float) -> void:
	pair_t += dt
	if pair_t > 5.5:
		_new_pair()
		pair_t = 0.0
	for sp: Array in sparks:
		sp[1] -= sp[2] * dt
		if sp[1] < -10:
			sp[1] = LH + 10
			sp[0] = rng.randf_range(view_l, view_r)


func _order() -> Array:
	return BIG + SMALL


func on_tap(name: String) -> void:
	if help_open:
		help_open = false
		play("click")
		return
	_go(name)


func on_key(kc: int) -> void:
	if help_open:
		help_open = false
		return
	var o := _order()
	var i := o.find(focus)
	match kc:
		KEY_DOWN, KEY_S, KEY_TAB, KEY_RIGHT, KEY_D:
			set_focus(o[(i + 1) % o.size()])
		KEY_UP, KEY_W, KEY_LEFT, KEY_A:
			set_focus(o[(i - 1 + o.size()) % o.size()])
		KEY_ENTER, KEY_SPACE, KEY_KP_ENTER:
			_go(focus)


func on_back() -> void:
	if help_open:
		help_open = false
	else:
		get_tree().quit()


func _go(name: String) -> void:
	match name:
		"bot":
			play("kick")
			Game.mode = "bot"
			Game.go("res://scenes/select.tscn")
		"online":
			play("kick")
			Game.go("res://scenes/online.tscn")
		"cup":
			play("kick")
			if not Game.cup.is_empty() and int(Game.cup.get("stage", 0)) < Game.CUP_STAGES.size():
				Game.mode = "cup"
				Game.go("res://scenes/cup.tscn")
			else:
				Game.mode = "cup"
				Game.go("res://scenes/select.tscn")
		"keys":
			play("click")
			help_open = true
		"settings":
			play("click")
			Game.go("res://scenes/settings.tscn")
		"exit":
			get_tree().quit()


func paint() -> void:
	fit_mirror(R.tex("m2_bg.jpg"))
	for sp: Array in sparks:
		var a := 0.35 + 0.35 * sin(t * sp[4] + sp[3])
		R.glow(self, Vector2(sp[0], sp[1]), 7.0, Color(1, 0.85, 0.45, a))
	_stage()
	var lg := R.tex("logo.png")
	if lg:
		var w := 300.0
		draw_texture_rect(lg, Rect2(40, 12, w, lg.get_height() * w / lg.get_width()), false)
	var y := 182.0
	for i in BIG.size():
		var k: String = BIG[i]
		var h := 84.0 if i == 0 else 70.0
		_big_button(k, Rect2(58, y, 430.0 if i == 0 else 410.0, h), i == 0)
		y += h + 16.0
	for i in SMALL.size():
		_round_button(SMALL[i], Vector2(100 + i * 128, 500))
	R.text(self, INFO.get(focus, ["", ""])[1], 18, Vector2(60, 668), Color8(225, 232, 245), 3, HORIZONTAL_ALIGNMENT_LEFT, false)
	R.text(self, VERSION, 12, Vector2(view_r - 14, LH - 14), Color8(150, 165, 200), 2, HORIZONTAL_ALIGNMENT_RIGHT, false)
	_profile_bar()
	if help_open:
		_help()


## Sag ust: seviye rozeti, XP cubugu, altin
func _profile_bar() -> void:
	var li := Game.level_info()
	var x1 := view_r - 24.0
	var box := Rect2(x1 - 380, 18, 380, 64)
	R.panel(self, box, Color(0.04, 0.06, 0.16, 0.85), 22, Color(1, 1, 1, 0.35), 2)
	var bc := Vector2(box.position.x + 34, box.get_center().y)
	draw_circle(bc, 25, Color8(10, 14, 30))
	draw_circle(bc, 22, Color8(60, 110, 230))
	draw_arc(bc, 22, 0, TAU, 40, GOLD, 2.5, true)
	R.text(self, str(li[0]), 22, bc, WHITE, 3)
	R.text(self, "SEVİYE", 13, Vector2(box.position.x + 66, box.position.y + 18), Color8(190, 205, 235), 2, HORIZONTAL_ALIGNMENT_LEFT, false)
	var bar := Rect2(box.position.x + 66, box.position.y + 32, 170, 14)
	R.panel(self, bar, Color8(16, 22, 46), 7)
	var k := float(li[1]) / float(li[2])
	if k > 0.02:
		R.panel(self, Rect2(bar.position, Vector2(bar.size.x * k, bar.size.y)), Color8(90, 200, 255), 7)
	R.text(self, "%d/%d XP" % [li[1], li[2]], 11, Vector2(bar.end.x, box.position.y + 18), Color8(170, 190, 225), 2, HORIZONTAL_ALIGNMENT_RIGHT, false)
	var cc := Vector2(box.end.x - 110, box.get_center().y)
	draw_circle(cc, 15, Color8(150, 100, 10))
	draw_circle(cc, 13, Color8(255, 200, 50))
	draw_arc(cc, 9, 0, TAU, 24, Color8(200, 140, 20), 2.0, true)
	R.text(self, str(Game.profile["coins"]), 24, Vector2(cc.x + 24, cc.y), Color8(255, 220, 110), 3, HORIZONTAL_ALIGNMENT_LEFT)


func _big_button(key: String, r: Rect2, primary: bool) -> void:
	reg(key, r)
	var on := focus == key
	var pop := 1.0 + (0.05 * maxf(0.0, 1.0 - focus_t * 5.0) if on else 0.0) - 0.04 * pressed_k(key)
	var rr := Rect2(r.get_center() - r.size * pop / 2.0, r.size * pop)
	if on:
		R.glow(self, rr.get_center(), rr.size.x * 0.45, Color(1, 0.8, 0.3, 0.3) if primary else Color(0.3, 0.55, 1, 0.3))
	slice3(R.tex("m2_gold.png" if primary else "m2_navy.png"), rr, Color(1, 1, 1, 1.0 if (on or primary) else 0.9))
	var ic := R.tex("m2_ic_%s.png" % INFO[key][2])
	if ic:
		var isz := 50.0
		draw_texture_rect(ic, Rect2(rr.position.x + 52 - isz / 2.0, rr.get_center().y - isz / 2.0, isz, isz), false)
	var tcol := Color8(40, 26, 6) if primary else (GOLD if on else WHITE)
	R.text(self, INFO[key][0], 30 if primary else 25, Vector2(rr.position.x + 96, rr.get_center().y), tcol,
		0 if primary else 3, HORIZONTAL_ALIGNMENT_LEFT)
	if key == "cup" and not Game.cup.is_empty() and int(Game.cup.get("stage", 0)) < Game.CUP_STAGES.size():
		var chip := Rect2(rr.end.x - 124, rr.position.y - 8, 112, 24)
		R.panel(self, chip, Color8(40, 150, 70), 10, WHITE, 2)
		R.text(self, "TUR %d/5" % (int(Game.cup["stage"]) + 1), 13, chip.get_center(), WHITE, 2, HORIZONTAL_ALIGNMENT_CENTER, false)
	if on and not primary:
		R.panel(self, rr.grow(2), Color(0, 0, 0, 0), rr.size.y * 0.45, GOLD, 3)


func _round_button(key: String, c: Vector2) -> void:
	var r := Rect2(c - Vector2(42, 42), Vector2(84, 84))
	reg(key, r)
	var on := focus == key
	if on:
		R.glow(self, c, 62, Color(1, 0.8, 0.3, 0.35))
	var rb := R.tex("m2_round.png")
	var sz := 78.0 * (1.0 - 0.06 * pressed_k(key))
	if rb:
		draw_texture_rect(rb, Rect2(c - Vector2(sz, sz) / 2.0, Vector2(sz, sz)), false)
	var ic := R.tex("m2_ic_%s.png" % INFO[key][2])
	if ic:
		draw_texture_rect(ic, Rect2(c - Vector2(20, 20), Vector2(40, 40)), false)
	R.text(self, INFO[key][0], 15, c + Vector2(0, 56), GOLD if on else Color8(215, 222, 240), 3)


func _stage() -> void:
	var cx := 908.0
	var gy := 532.0
	R.glow(self, Vector2(cx, gy - 40), 260 + 12 * sin(t * 1.3), Color(1, 0.8, 0.3, 0.22))
	var k := minf(1.0, pair_t / 0.5)
	var out := maxf(0.0, (pair_t - 5.1) / 0.4)
	var ease := 1.0 - pow(1.0 - k, 3.0)
	for side in 2:
		var c: int = pair[side]
		var h: float = 300.0 * K.CHARACTERS[c]["scale"]
		var d := -1.0 if side == 0 else 1.0
		var x := cx + d * 118.0 + d * 260.0 * (1.0 - ease) + d * 260.0 * out
		var bob := sin(t * 2.2 + side * 1.7) * 3.0
		var al := clampf(minf(ease, 1.0 - out), 0.0, 1.0)
		Rig.draw(self, c, Rig.pose_named("idle", t + side), Vector2(x, gy + bob), h, side == 1, Color(1, 1, 1, al))
		R.text(self, K.DISPLAY_NAMES[c], 22, Vector2(x, gy + 26), Color(1, 1, 1, al), 4)
		if al > 0.8:
			draw_line(Vector2(x - 36, gy + 44), Vector2(x + 36, gy + 44), P_COLORS[side], 3.0, true)
	if ease > 0.6 and out <= 0.0:
		var pul := 1.0 + 0.06 * sin(t * 5.0)
		R.text(self, "VS", int(46 * pul), Vector2(cx, gy - 150), GOLD, 6)


func _help() -> void:
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.01, 0.02, 0.07, 0.8))
	var r := Rect2(LW / 2.0 - 430, 70, 860, 560)
	R.panel(self, r, Color8(16, 24, 56), 30, GOLD, 3)
	reg("help_close", Rect2(view_l, 0, view_r - view_l, LH))
	R.text(self, "KONTROLLER", 44, Vector2(LW / 2.0, 120), GOLD, 5)
	var rows := [
		["Hareket", "Sol joystick  ·  A / D  ·  ← / →"],
		["Zıpla", "Yeşil tuş  ·  W / ↑"],
		["Şut", "Kırmızı tuş  ·  BOŞLUK / K"],
		["Aşırtma", "Turuncu tuş  ·  Q / F"],
		["Süper güç", "Dolunca sarı tuş  ·  R  ·  ↓↓"],
		["Omuz", "Mor tuş  ·  E / CTRL"],
		["Tuş düzeni", "Maçta duraklat → TUŞ DÜZENİ: tuşları taşı, büyüt"],
	]
	var y := 190.0
	for row: Array in rows:
		R.text(self, row[0], 26, Vector2(r.position.x + 60, y), GOLD, 3, HORIZONTAL_ALIGNMENT_LEFT)
		R.text(self, row[1], 22, Vector2(r.position.x + 260, y), WHITE, 3, HORIZONTAL_ALIGNMENT_LEFT, false)
		y += 56.0
	R.text(self, "Kapatmak için dokun", 18, Vector2(LW / 2.0, r.end.y - 28), Color8(180, 195, 225), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
