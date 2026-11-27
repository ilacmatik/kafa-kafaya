## Hava efektleri (yagmur, kar, ruzgar). Saha koordinatinda, oyuncularin onunde cizilir.
extends Node2D

var m  # match.gd
var drops: Array = []     # [x, y, k]
var t := 0.0
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	rng.randomize()
	for i in 220:
		drops.append([rng.randf_range(0, K.W), rng.randf_range(0, K.H), rng.randf_range(0.6, 1.25)])


func _process(dt: float) -> void:
	if m == null or m.world == null or m.paused:
		return
	t += dt
	var wx: String = m.world.weather
	var wd: float = m.world.wind
	for r: Array in drops:
		r[1] += (900.0 if wx == "rain" else 70.0) * r[2] * dt
		r[0] += wd * dt * (0.3 if wx == "rain" else 0.6)
		if wx == "snow":
			r[0] += sin(t * 1.5 + r[2] * 9.0) * 20.0 * dt
		if r[1] > K.H:
			r[1] -= K.H + 20.0
			r[0] = rng.randf_range(-40, K.W + 40)
		r[0] = fposmod(r[0] + 40.0, K.W + 80.0) - 40.0
	queue_redraw()


func _tex_h(name: String, h: float, pos: Vector2, col: Color = Color.WHITE, rot: float = 0.0, flip: bool = false) -> void:
	var tx := R.tex(name)
	if tx == null:
		return
	var w := tx.get_width() * h / tx.get_height()
	draw_set_transform(pos, rot, Vector2(-1.0 if flip else 1.0, 1.0))
	draw_texture_rect(tx, Rect2(-w / 2.0, -h / 2.0, w, h), false, col)
	draw_set_transform(Vector2.ZERO)


func _draw() -> void:
	if m == null or m.world == null:
		return
	var wx: String = m.world.weather
	var themed: bool = m.stadium == 1 and wx in ["rain", "snow"]
	match wx:
		"rain":
			if not themed:
				draw_rect(Rect2(-40, -40, K.W + 80, K.H + 80), Color8(10, 20, 40, 70))
			var wd: float = m.world.wind * 0.02
			for i in 140:
				var r: Array = drops[i]
				var k: float = r[2]
				var a := 0.35 + 0.4 * (k - 0.6) / 0.65
				draw_line(Vector2(r[0], r[1] - 14.0 * k), Vector2(r[0] - 2.0 - wd, r[1]), Color(0.75, 0.82, 0.95, a), 1.2 + k * 0.6, true)
				if r[1] > K.GROUND - 16.0 and int(r[0] * 7.0) % 4 == 0:
					_tex_h("wx_splash.png", 10.0, Vector2(r[0], K.GROUND - 2.0), Color(1, 1, 1, 0.8))
		"snow":
			if not themed:
				draw_rect(Rect2(-40, -40, K.W + 80, K.H + 80), Color8(200, 215, 240, 26))
			for i in 150:
				var r2: Array = drops[i]
				var k2: float = r2[2]
				if i % 5 == 0:
					_tex_h("wx_flake.png", 8.0 * k2, Vector2(r2[0], r2[1]), Color.WHITE, t * k2)
				else:
					draw_circle(Vector2(r2[0], r2[1]), 1.0 + 0.9 * k2, Color(0.93, 0.95, 1.0, 0.55 + 0.35 * (k2 - 0.6)))
			draw_rect(Rect2(-40, K.GROUND + 2.0, K.W + 80, 6), Color8(235, 242, 252))
			for px in [150.0, 420.0, 860.0, 1130.0]:
				_tex_h("wx_snowpile.png", 26.0, Vector2(px, K.GROUND - 5.0))
		"wind":
			var wd2: float = m.world.wind
			var d := 1.0 if wd2 >= 0.0 else -1.0
			for i in 36:
				var r3: Array = drops[i]
				var k3: float = r3[2]
				var yy := 140.0 + fposmod(r3[1], 420.0)
				var xx := fposmod(r3[0] + t * absf(wd2) * 1.6 * k3, K.W + 80.0) - 40.0
				if d < 0.0:
					xx = K.W - xx
				if i % 4 == 0:
					_tex_h("wx_gust.png", 40.0, Vector2(xx, yy), Color(1, 1, 1, 0.42), 0.0, d < 0.0)
				elif i % 4 == 1:
					_tex_h("wx_leaf.png", 18.0, Vector2(xx, yy + sin(t * 3.0 + k3 * 5.0) * 18.0), Color.WHITE, t * 3.5 * k3)
				else:
					draw_line(Vector2(xx, yy), Vector2(xx + d * 50.0 * k3, yy), Color(0.9, 0.94, 1.0, 0.55), 2.0, true)
