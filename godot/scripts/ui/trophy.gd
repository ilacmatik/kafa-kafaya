## Sampiyonluk ekrani: havai fisekler, podyum, kupa.
extends UIScreen

var fw: Array = []
var rng := RandomNumberGenerator.new()
var ch := 0


func _ready() -> void:
	super._ready()
	rng.randomize()
	ch = int(Game.cup.get("char", 0))
	play("golden")
	await get_tree().create_timer(0.3).timeout
	play("goal")


func tick(dt: float) -> void:
	if rng.randf() < dt * 3.5:
		fw.append([rng.randf_range(150, LW - 150), rng.randf_range(80, 320), ["fx_fw_gold.png", "fx_fw_red.png", "fx_fw_blue.png"][rng.randi_range(0, 2)], 1.0])
		play("pop")
	for f: Array in fw:
		f[3] -= dt
	fw = fw.filter(func(f): return f[3] > 0.0)


func on_tap(_name: String) -> void:
	_leave()


func on_key(_kc: int) -> void:
	_leave()


func on_back() -> void:
	_leave()


func _leave() -> void:
	if t < 1.5:
		return
	Game.cup = {}
	Game.save_profile()
	Game.go("res://scenes/menu.tscn")


func paint() -> void:
	cover(R.tex("m2_bg.jpg"))
	reg("any", Rect2(view_l, 0, view_r - view_l, LH))
	for f: Array in fw:
		var tx := R.tex(f[2])
		if tx:
			var k: float = 0.4 + 0.8 * minf(1.0, (1.0 - f[3]) * 2.5)
			var sz := 200.0 * k
			draw_texture_rect(tx, Rect2(Vector2(f[0], f[1]) - Vector2(sz, sz) / 2.0, Vector2(sz, sz)), false, Color(1, 1, 1, minf(1.0, f[3] * 2.0)))
	var pod := R.tex("podium.png")
	var base_y := 560.0
	if pod:
		var pw := 430.0
		var ph := pod.get_height() * pw / pod.get_width()
		draw_texture_rect(pod, Rect2(LW / 2.0 - pw / 2.0, 712 - ph, pw, ph), false)
		base_y = 712 - ph + ph * 0.12
	var hop := absf(sin(t * 6.0)) * 14.0
	var hero := R.pose(ch, "celeb")
	if hero:
		var hh := 230.0
		var hw := hero.get_width() * hh / hero.get_height()
		draw_texture_rect(hero, Rect2(LW / 2.0 - hw / 2.0, base_y - hop - hh, hw, hh), false)
	var cup := R.tex("cup_gold.png")
	if cup:
		R.glow(self, Vector2(LW / 2.0 + 150, 380), 150, Color(1, 0.8, 0.3, 0.45))
		var ch2 := 200.0
		var cw := cup.get_width() * ch2 / cup.get_height()
		draw_texture_rect(cup, Rect2(Vector2(LW / 2.0 + 160, 390 - hop * 0.5) - Vector2(cw, ch2) / 2.0, Vector2(cw, ch2)), false)
	R.text(self, "ŞAMPİYON!", 84, Vector2(LW / 2.0, 82), GOLD, 7)
	R.text(self, K.DISPLAY_NAMES[ch], 34, Vector2(LW / 2.0, 150), WHITE, 5)
	R.text(self, "Toplam kupa: %d     +200 ALTIN" % Game.profile["cups"], 22, Vector2(LW / 2.0, 188), Color8(255, 225, 140), 3, HORIZONTAL_ALIGNMENT_CENTER, false)
	if t > 1.5:
		R.text(self, "Devam etmek için dokun", 18, Vector2(LW / 2.0, LH - 20), WHITE, 2, HORIZONTAL_ALIGNMENT_CENTER, false)
