## Skor tablosu ve oyuncu panelleri (ekranin ust ortasina sabit, 1280 mantiksal birimde cizilir).
extends Node2D

var m  # match.gd
const P_COLORS := [Color8(70, 160, 255), Color8(255, 85, 85)]
const GOLD := Color8(255, 205, 60)
const DARK := Color8(12, 14, 34)


func _process(_d: float) -> void:
	var vp := get_viewport_rect().size
	var s := vp.y / 720.0
	scale = Vector2(s, s)
	position = Vector2(vp.x / 2.0, 0)
	queue_redraw()


func _seg_meter(r: Rect2, k: float, col: Color, right: bool, flash: bool) -> void:
	R.panel(self, r.grow(3), Color(0.05, 0.06, 0.14, 0.92), 10)
	var n := 10
	var gap := 3.0
	var sw := (r.size.x - gap * (n - 1)) / n
	var filled := k * n
	for i in n:
		var idx := (n - 1 - i) if right else i
		var x := r.position.x + idx * (sw + gap)
		var seg := Rect2(x, r.position.y, sw, r.size.y)
		var f := clampf(filled - i, 0.0, 1.0)
		R.panel(self, seg, Color(0.16, 0.2, 0.33), 4)
		if f > 0.0:
			var c := col.lightened(0.35) if flash else col
			var fs := Rect2(seg.position, Vector2(seg.size.x * f, seg.size.y))
			if right:
				fs = Rect2(seg.position + Vector2(seg.size.x * (1.0 - f), 0), Vector2(seg.size.x * f, seg.size.y))
			R.panel(self, fs, c, 4)
			draw_rect(Rect2(fs.position + Vector2(2, 2), Vector2(maxf(0.0, fs.size.x - 4), 4)), Color(1, 1, 1, 0.35))


func _draw() -> void:
	if m == null or m.world == null:
		return
	var w: SimWorld = m.world
	var t: float = m.t
	# skor tablosu
	var board := Rect2(-230, 10, 460, 78)
	R.panel(self, board.grow(4), Color(0.02, 0.03, 0.08, 0.6), 26)
	R.panel(self, board, Color8(22, 30, 64), 22, GOLD, 3)
	draw_rect(Rect2(board.position + Vector2(14, 6), Vector2(board.size.x - 28, 10)), Color(1, 1, 1, 0.06))
	var tt := ""
	var tc := Color.WHITE
	if w.pen != null:
		tt = "PEN"
		tc = GOLD
	elif w.golden:
		tt = "ALTIN GOL"
		tc = GOLD
	else:
		var sec := maxi(0, ceili(w.time_left))
		tt = "%d:%02d" % [sec / 60, sec % 60]
		tc = Color8(255, 90, 80) if sec <= 10 else Color.WHITE
	var tw := 124.0 if not w.golden else 160.0
	var timer := Rect2(-tw / 2.0, board.get_center().y - 23, tw, 46)
	R.panel(self, timer, Color8(36, 52, 110), 14)
	R.text(self, tt, 28 if not w.golden else 22, timer.get_center(), tc, 3)
	R.text(self, str(w.score[0]), 54, Vector2(-118, board.get_center().y), Color.WHITE, 5)
	R.text(self, str(w.score[1]), 54, Vector2(118, board.get_center().y), Color.WHITE, 5)
	for i in 2:
		var p: SimPlayer = w.players[i]
		var px := board.position.x - 50.0 if i == 0 else board.end.x + 50.0
		var cy := board.get_center().y
		R.glow(self, Vector2(px, cy), 56.0, Color(P_COLORS[i].r, P_COLORS[i].g, P_COLORS[i].b, 0.35))
		draw_circle(Vector2(px, cy), 42, DARK)
		draw_circle(Vector2(px, cy), 39, P_COLORS[i])
		draw_circle(Vector2(px, cy), 34, Color8(16, 24, 52))
		draw_arc(Vector2(px, cy), 39, 0, TAU, 48, GOLD, 3.0, true)
		# kafa dairenin ustunden hafifce tasar
		R.draw_tex(self, R.portrait_pop(p.char, 192), R.pop_rect(Vector2(px, cy + 1.0), 35.0), i == 1)
		var name: String = K.DISPLAY_NAMES[p.char]
		var tag: String = m.hud_tag(i)
		var plate := Rect2(px - 48 - 214, 12, 214, 32) if i == 0 else Rect2(px + 48, 12, 214, 32)
		R.panel(self, plate, Color8(20, 28, 60), 12)
		var cw := 62.0 if tag.length() > 3 else 50.0
		var chip := Rect2(plate.position.x + 5, plate.get_center().y - 12, cw, 24) if i == 0 \
			else Rect2(plate.end.x - 5 - cw, plate.get_center().y - 12, cw, 24)
		R.panel(self, chip, P_COLORS[i], 9)
		R.text(self, tag, 13, chip.get_center(), Color.WHITE, 2, HORIZONTAL_ALIGNMENT_CENTER, false)
		if i == 0:
			R.text(self, name, 19, Vector2(chip.end.x + 10, plate.get_center().y), Color.WHITE, 2, HORIZONTAL_ALIGNMENT_LEFT)
		else:
			R.text(self, name, 19, Vector2(chip.position.x - 10, plate.get_center().y), Color.WHITE, 2, HORIZONTAL_ALIGNMENT_RIGHT)
		var pw: String = p.stats["power"]
		var col: Color = K.POWERS[pw][1]
		var bar := Rect2(px - 52 - 176, 50, 176, 20) if i == 0 else Rect2(px + 52, 50, 176, 20)
		var full := p.meter >= 100.0 or p.armed > 0.0
		_seg_meter(bar, p.meter / 100.0, col, i == 1, full and int(t * 6) % 2 == 0)
		var ic := R.tex("pw_%s.png" % pw)
		if ic == null:
			ic = R.tex("fx_%s.png" % pw)
		if ic:
			var icx := bar.position.x - 18.0 if i == 0 else bar.end.x + 18.0
			draw_texture_rect(ic, Rect2(icx - 15, bar.get_center().y - 15, 30, 30), false)
		if full and m.is_local(i):
			var msg: String = "SÜPER AKTİF!" if (p.armed > 0.0 or p.magnet_t > 0.0) else K.POWERS[pw][0] + " HAZIR · " + m.super_hint(i)
			R.text(self, msg, 16, Vector2(bar.get_center().x, bar.end.y + 14), col, 3)
		var icons := []
		if p.speed_t > 0.0:
			icons.append("speed")
		if p.jump_t > 0.0:
			icons.append("jump")
		if w.shield[i] > 0.0:
			icons.append("shield")
		for k in icons.size():
			var img := R.tex("pu_%s.png" % icons[k])
			if img:
				var ix := (bar.position.x + 16 + k * 34) if i == 0 else (bar.end.x - 16 - k * 34)
				draw_texture_rect(img, Rect2(ix - 14, bar.end.y + 32, 28, 28), false)
