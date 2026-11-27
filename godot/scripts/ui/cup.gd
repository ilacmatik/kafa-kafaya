## Kupa yolu: 5 tur, her turda farkli rakip, hava ve stadyum. Kaybedersen ayni turu tekrar denersin.
extends UIScreen

const CHAMP_BONUS := 200

var msg := ["", Color.WHITE]
var sparks: Array = []
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	rng.randomize()
	for i in 30:
		sparks.append([rng.randf_range(0, LW), rng.randf_range(0, LH), rng.randf_range(10, 30), rng.randf_range(0, TAU)])
	var c := Game.cup
	if Game.cup_result != null:
		if Game.cup_result:
			c["stage"] = int(c["stage"]) + 1
			c["lost"] = false
			msg = ["KAZANDIN! SIRADAKİ TURA GEÇTİN", Color8(120, 255, 140)]
			play("cheer")
			if int(c["stage"]) >= Game.CUP_STAGES.size():
				Game.profile["cups"] += 1
				Game.profile["coins"] += CHAMP_BONUS
				Game.cup_result = null
				Game.save_profile()
				Game.go("res://scenes/trophy.tscn")
				return
		else:
			c["lost"] = true
			msg = ["ELENDİN! TEKRAR DENE", Color8(255, 120, 110)]
			play("ooh")
		Game.cup_result = null
		Game.save_profile()
	focus = "play"


func tick(dt: float) -> void:
	for sp: Array in sparks:
		sp[1] -= sp[2] * dt
		if sp[1] < -10:
			sp[1] = LH + 10
			sp[0] = rng.randf_range(view_l, view_r)


func on_tap(name: String) -> void:
	match name:
		"play":
			if int(Game.cup.get("stage", 0)) < Game.CUP_STAGES.size():
				play("kick")
				Game.start_cup_match()
		"new":
			play("click")
			Game.mode = "cup"
			Game.go("res://scenes/select.tscn")
		"back":
			on_back()


func on_key(kc: int) -> void:
	if kc in [KEY_ENTER, KEY_SPACE, KEY_KP_ENTER]:
		on_tap("play")


func on_back() -> void:
	play("click")
	Game.go("res://scenes/menu.tscn")


func paint() -> void:
	cover(R.tex("m2_bg.jpg"))
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.01, 0.02, 0.07, 0.6))
	for sp: Array in sparks:
		R.glow(self, Vector2(sp[0], sp[1]), 6.0, Color(1, 0.85, 0.45, 0.3 + 0.3 * sin(t * 2.0 + sp[3])))
	var c := Game.cup
	if c.is_empty():
		return
	var frame := Rect2(70, 90, LW - 140, 560)
	R.panel(self, frame, Color(0.05, 0.08, 0.2, 0.85), 34, GOLD, 3)
	R.text(self, "KUPA YOLU", 50, Vector2(LW / 2.0, 140), GOLD, 6)
	# oyuncu ve kupa
	var mc: int = int(c["char"])
	var pc := Vector2(190, 190)
	draw_circle(pc, 62, Color8(8, 12, 30))
	draw_circle(pc, 58, P_COLORS[0])
	draw_circle(pc, 53, Color8(14, 22, 50))
	R.draw_tex(self, R.portrait_pop(mc, 192), R.pop_rect(pc + Vector2(0, 2), 54.0))
	R.text(self, K.DISPLAY_NAMES[mc], 22, pc + Vector2(0, 84), WHITE, 3)
	var tr := R.tex("cup_gold.png")
	if tr:
		var th := 130.0
		var tw := tr.get_width() * th / tr.get_height()
		var tp := Vector2(LW - 190, 190 + sin(t * 2.0) * 4.0)
		R.glow(self, tp, 110, Color(1, 0.8, 0.3, 0.35))
		draw_texture_rect(tr, Rect2(tp - Vector2(tw, th) / 2.0, Vector2(tw, th)), false)
	# yol
	var n := Game.CUP_STAGES.size()
	var stage: int = int(c["stage"])
	var x0 := 190.0
	var x1 := LW - 190.0
	var y := 390.0
	draw_line(Vector2(x0, y), Vector2(x1, y), Color8(12, 14, 34), 12.0, true)
	draw_line(Vector2(x0, y), Vector2(x1, y), Color8(80, 90, 130), 6.0, true)
	if stage > 0:
		var dx := x0 + (x1 - x0) * minf(stage, n - 1) / (n - 1)
		draw_line(Vector2(x0, y), Vector2(dx, y), GOLD, 6.0, true)
	for k in n:
		var st: Array = Game.CUP_STAGES[k]
		var x := x0 + (x1 - x0) * k / (n - 1)
		var cur := k == stage
		var won := k < stage
		var r := 46.0 if cur else 38.0
		if cur:
			R.glow(self, Vector2(x, y), 90 + 8 * sin(t * 4.0), Color(1, 0.8, 0.3, 0.4))
		draw_circle(Vector2(x, y), r + 4, Color8(12, 14, 34))
		draw_circle(Vector2(x, y), r + 1, GOLD if cur else (Color8(60, 200, 90) if won else Color8(70, 80, 120)))
		draw_circle(Vector2(x, y), r - 3, Color8(18, 26, 56))
		var opp: int = int(c["opps"][k])
		if won or cur:
			R.draw_tex(self, R.portrait_pop(opp, 192), R.pop_rect(Vector2(x, y + 1), r - 4), true)
		else:
			R.text(self, "?", int(r), Vector2(x, y), Color(1, 1, 1, 0.5), 3)
		var badge := "st_check.png" if won else ("st_skull.png" if k == n - 1 else ("st_swords.png" if cur else "st_lock.png"))
		var bt := R.tex(badge)
		if bt:
			draw_texture_rect(bt, Rect2(Vector2(x + r * 0.7, y - r * 0.7) - Vector2(15, 15), Vector2(30, 30)), false)
		R.text(self, st[0], 17 if cur else 15, Vector2(x, y + r + 22), GOLD if cur else WHITE, 2)
		R.text(self, "%s · %s" % [Game.weather_name(st[2]), Game.STADIUM_NAMES[st[3]]], 12, Vector2(x, y + r + 44),
			Color8(190, 205, 235), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
		R.text(self, Game.LEVELS[st[1]], 13, Vector2(x, y - r - 18), Color8(255, 200, 120), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
	if msg[0] != "":
		R.text(self, msg[0], 26, Vector2(LW / 2.0, 518), msg[1], 3)
	if stage < n:
		var opp2: int = int(c["opps"][stage])
		R.text(self, "%s:  %s  vs  %s" % [Game.CUP_STAGES[stage][0], K.DISPLAY_NAMES[mc], K.DISPLAY_NAMES[opp2]], 22,
			Vector2(LW / 2.0, 556), WHITE, 3)
	# dugmeler
	var pr := Rect2(LW / 2.0 - 160, 600, 320, 64)
	reg("play", pr)
	var rr := pr.grow(-4.0 * pressed_k("play") + 2.0 * sin(t * 4.0))
	R.glow(self, rr.get_center(), 170, Color(1, 0.8, 0.3, 0.35))
	slice3(R.tex("m2_gold.png"), rr)
	R.text(self, "TEKRAR DENE ▶" if c.get("lost", false) else "MAÇA BAŞLA ▶", 26, rr.get_center(), Color8(40, 26, 6), 0)
	flat_button("back", Rect2(view_l + 20, 20, 150, 48), "ANA MENÜ", Color8(60, 70, 110), 20)
	flat_button("new", Rect2(view_r - 190, 20, 170, 48), "YENİ KUPA", Color8(150, 60, 170), 20)
