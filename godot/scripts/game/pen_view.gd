## Penalti kamerasi: kale karsidan, atici arkadan. Python _draw_pen_view'in karsiligi.
## 1280x720 mantiksal alanda cizilir; ekrana yukseklige gore oturur, yanlar arka planla dolar.
extends Node2D

const GOAL := [304.0, 976.0, 230.0, 507.0]   # sol, sag, ust direk alti, zemin
const LW := 1280.0
const LH := 720.0
const GOLD := Color8(255, 205, 60)

var m  # match.gd
var t := 0.0


func active() -> bool:
	return m != null and m.world != null and m.world.pen != null and String(m.world.phase).begins_with("pen")


func _process(dt: float) -> void:
	t += dt
	visible = active()
	if not visible:
		return
	var vp := get_viewport_rect().size
	var s := vp.y / LH
	if m.touch_on:
		# kontrol seridi altta: tum sahne seridin ustune sigsin
		s = (vp.y - 190.0) / 735.0
	position = Vector2((vp.x - LW * s) / 2.0, 0.0)
	scale = Vector2(s, s)
	queue_redraw()


func zone(col: int, row: int) -> Vector2:
	var cx := (GOAL[0] + GOAL[1]) / 2.0 + col * (GOAL[1] - GOAL[0]) * 0.33
	var cy := GOAL[3] - 62.0 if row == 0 else GOAL[2] + 72.0
	return Vector2(cx, cy)


func _tex_mb(tx: Texture2D, h: float, mb: Vector2, flip: bool = false, rot: float = 0.0, col: Color = Color.WHITE) -> void:
	if tx == null:
		return
	var w := tx.get_width() * h / tx.get_height()
	if rot != 0.0:
		draw_set_transform(mb - Vector2(0, h / 2.0), rot, Vector2(-1.0 if flip else 1.0, 1.0))
		draw_texture_rect(tx, Rect2(-w / 2.0, -h / 2.0, w, h), false, col)
	else:
		draw_set_transform(mb, 0.0, Vector2(-1.0 if flip else 1.0, 1.0))
		draw_texture_rect(tx, Rect2(-w / 2.0, -h, w, h), false, col)
	draw_set_transform(Vector2.ZERO)


func _draw() -> void:
	if not active():
		return
	var w: SimWorld = m.world
	var pen: Dictionary = w.pen
	var turn: int = pen["turn"]
	var keeper := 1 - turn
	var ph: String = w.phase
	var shot = pen["shot"]
	var x0: float = GOAL[0]
	var x1: float = GOAL[1]
	var y0: float = GOAL[2]
	var y1: float = GOAL[3]
	var gw := x1 - x0
	# arka plan (genis ekranda kenarlari da kapla)
	var vp := get_viewport_rect().size
	var vl := -position.x / scale.x
	var vr := vl + vp.x / scale.x
	var bg := R.tex("pen_bg.jpg")
	if bg:
		var k := maxf((vr - vl) / bg.get_width(), (vp.y / scale.y) / bg.get_height())
		var sz := Vector2(bg.get_width(), bg.get_height()) * k
		draw_texture_rect(bg, Rect2(Vector2((vl + vr) / 2.0 - sz.x / 2.0, 0), sz), false)
	var t_shot := 0.0
	if ph == "pen_shot":
		t_shot = K.PEN_SHOT_T - w.phase_t
	elif ph == "pen_res":
		t_shot = K.PEN_SHOT_T
	var kchar: int = w.players[keeper].char
	var schar: int = w.players[turn].char
	# kaleci
	var kimg := R.tex("sel_hero%d.png" % kchar)
	var kh := 185.0
	var kx := LW / 2.0
	var ky := y1 + 4.0
	var ang := 0.0
	var kflip := false
	if shot != null:
		var scol: int = shot[0]
		var kcol: int = shot[2]
		var krow: int = shot[3]
		var e := clampf((t_shot - 0.18) / 0.32, 0.0, 1.0)
		e = 1.0 - (1.0 - e) * (1.0 - e)
		if kcol != 0:
			kx += kcol * gw * 0.30 * e
			ky -= (120.0 if krow == 1 else 30.0) * e
			var dive := R.tex("pen_dive%d.png" % kchar)
			if dive and e > 0.2:
				kimg = dive
				kh = 165.0
				kflip = kcol < 0
			else:
				ang = deg_to_rad(kcol * 75.0 * e)
		else:
			ky -= (95.0 if krow == 1 else 0.0) * e
			var jp := R.tex("pen_jump%d.png" % kchar)
			if krow == 1 and jp and e > 0.2:
				kimg = jp
				kh = 205.0
	else:
		kx += sin(t * 3.2) * 18.0
	draw_set_transform(Vector2(kx, y1 + 8), 0.0, Vector2(1.0, 0.25))
	draw_circle(Vector2.ZERO, 46.0, Color(0, 0, 0, 0.35))
	draw_set_transform(Vector2.ZERO)
	_tex_mb(kimg, kh, Vector2(kx, ky), kflip, ang)
	# top
	var b0 := Vector2(LW / 2.0 + 34.0, 660.0)
	var bp := b0
	var bs := 1.0
	if shot != null:
		var scol2: int = shot[0]
		var srow: int = shot[1]
		var out: int = shot[4]
		var tp := zone(scol2, srow)
		if out == 2:
			tp = Vector2(tp.x + scol2 * 120.0, y0 - 70.0)
		var k := minf(1.0, t_shot / 0.42)
		bp = b0.lerp(tp, k) - Vector2(0, sin(k * PI) * 60.0)
		bs = 1.0 - 0.5 * k
		if out == 1 and t_shot > 0.42:
			var k2 := minf(1.0, (t_shot - 0.42) / 0.6)
			bp.x += (-scol2 * 140.0 * k2) if scol2 != 0 else 160.0 * k2
			bp.y += -80.0 * sin(k2 * PI) + 220.0 * k2 * k2
			bs = 0.5 + 0.15 * k2
		elif out == 0 and t_shot > 0.42:
			bp.y = tp.y + 10.0 * sin((t_shot - 0.42) * 12.0) * exp(-(t_shot - 0.42) * 4.0)
	var shooting := shot != null
	var simg := R.tex(("pen_kick%d.png" if shooting else "pen_back%d.png") % schar)
	var ball := R.tex("ball.png")
	if ball and (not shooting or t_shot > 0.06):
		var br := 26.0 * 1.5 * bs
		draw_set_transform(bp, t_shot * 15.0, Vector2.ONE)
		draw_texture_rect(ball, Rect2(-br, -br, br * 2.0, br * 2.0), false)
		draw_set_transform(Vector2.ZERO)
	_tex_mb(simg, 215.0, Vector2(LW / 2.0, 722.0))
	# nisan (sadece kendi secimin)
	var me: int = m.me
	var c: Array = pen["c"]
	if ph == "pen_aim":
		var tip := ""
		if c[me] == null:
			var h: Dictionary = m.aim_input()
			var col := (1 if h["r"] else 0) - (1 if h["l"] else 0)
			var row := 1 if h["j"] else 0
			for cc in [-1, 0, 1]:
				for rr in [0, 1]:
					var z := zone(cc, rr)
					var on: bool = cc == col and rr == row
					var rad := 30.0 if on else 16.0
					if on:
						R.glow(self, z, 50.0, Color(1, 0.8, 0.3, 0.6))
					draw_arc(z, rad + 2.0, 0, TAU, 40, Color8(12, 14, 34), 6.0 if on else 5.0, true)
					draw_arc(z, rad, 0, TAU, 40, GOLD if on else Color8(120, 160, 220), 4.0 if on else 3.0, true)
					if on:
						draw_circle(z, 5.0, GOLD)
			if me == turn:
				tip = "ATIYORSUN  ·  sağ/sol ve ZIPLA ile köşe seç, ŞUT ile vur" if m.touch_on else "ATIYORSUN  ·  ←/→ ve ↑ ile yön seç, ŞUT ile vur"
			else:
				tip = "KALECİSİN  ·  atlayacağın yeri seç, ŞUT ile kilitle"
		else:
			tip = "SEÇİMİN KİLİTLENDİ  ·  rakip bekleniyor..."
		var frac := clampf(w.phase_t / K.PEN_AIM_T, 0.0, 1.0)
		var bar := Rect2(LW / 2.0 - 210, 232, 420, 16)
		R.panel(self, bar.grow(3), Color8(12, 14, 34), 11)
		if frac > 0.01:
			R.panel(self, Rect2(bar.position, Vector2(bar.size.x * frac, bar.size.y)), GOLD if frac > 0.3 else Color8(255, 90, 60), 9)
		R.text(self, tip, 20, Vector2(LW / 2.0, 212), Color.WHITE, 3)
		for who in 2:
			var nm := "SEN" if who == me else "RAKİP"
			var ready: bool = c[who] != null
			var tag := Rect2((170.0 if who == 0 else LW - 170.0) - 110, 225, 220, 30)
			R.panel(self, tag, Color8(40, 160, 70) if ready else (Color8(70, 160, 255) if who == 0 else Color8(255, 85, 85)).darkened(0.2), 12)
			R.text(self, "%s · %s" % [nm, "HAZIR ✓" if ready else "seçiyor..."], 15, tag.get_center() - Vector2(0, 1), Color.WHITE, 2)
	# penalti skoru
	var box := Rect2(vl + 30, 112, 330, 74)
	R.panel(self, box, Color(0.05, 0.08, 0.2, 0.9), 18, GOLD, 2)
	R.text(self, "PENALTILAR", 16, Vector2(box.get_center().x, box.position.y + 16), GOLD, 2)
	var res: Array = pen["res"]
	for i in 2:
		var r: Array = res[i]
		var n := maxi(5, r.size())
		var g := 0
		for v in r:
			g += int(v)
		for k3 in mini(n, 7):
			var cx := box.position.x + 30 + k3 * 20 if i == 0 else box.end.x - 30 - k3 * 20
			var cy := box.position.y + 46
			draw_circle(Vector2(cx, cy), 9, Color8(12, 14, 34))
			var col2 := Color8(50, 60, 95)
			if k3 < r.size():
				col2 = Color8(60, 210, 90) if int(r[k3]) == 1 else Color8(230, 70, 60)
			draw_circle(Vector2(cx, cy), 7, col2)
		R.text(self, str(g), 26, Vector2(box.get_center().x + (-24 if i == 0 else 24), box.position.y + 46), Color.WHITE, 3)
	if ph == "pen_ready":
		var who2 := "SEN" if turn == me else "RAKİP"
		R.text(self, "%s ATIYOR · %s" % [who2, K.DISPLAY_NAMES[schar]], 30, Vector2(LW / 2.0, 330), Color.WHITE, 4)
