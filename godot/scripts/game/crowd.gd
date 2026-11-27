## Tribun taraftarlari (Python fx.Crowd birebir). Taraftarlar tek MultiMesh'te, GPU'da oynar.
class_name Crowd
extends Node2D

const TEAM := {
	"red": [Color8(225, 60, 60), Color8(250, 250, 250), Color8(185, 35, 40)],
	"blue": [Color8(60, 115, 225), Color8(245, 245, 252), Color8(35, 70, 165)],
	"yellow": [Color8(252, 205, 45), Color8(45, 45, 55), Color8(235, 165, 25)],
	"green": [Color8(70, 175, 70), Color8(250, 250, 250), Color8(35, 120, 50)],
	"white": [Color8(245, 245, 248), Color8(60, 165, 75), Color8(225, 228, 232)],
	# kahraman renkleri (forma, ikinci renk, koyu ton)
	"k0": [Color8(225, 70, 35), Color8(255, 200, 60), Color8(170, 40, 25)],     # Alev
	"k1": [Color8(95, 180, 235), Color8(245, 250, 255), Color8(45, 110, 175)],   # Buz
	"k2": [Color8(140, 146, 158), Color8(190, 140, 80), Color8(95, 100, 112)],   # Kaya
	"k3": [Color8(40, 60, 120), Color8(220, 45, 45), Color8(25, 38, 85)],        # Kilic
	"k4": [Color8(120, 60, 170), Color8(60, 200, 190), Color8(80, 35, 120)],     # Ejder
	"k5": [Color8(50, 160, 90), Color8(240, 200, 80), Color8(30, 110, 60)],      # Ruh
	"k6": [Color8(55, 45, 75), Color8(210, 40, 50), Color8(35, 28, 50)],         # Golge
	"k7": [Color8(90, 130, 55), Color8(160, 110, 60), Color8(60, 90, 35)],       # Okcu
}
const OUTC := Color8(30, 24, 30)

var fans: Array = []      # [x, y, col, shade, skin, hair, sc, ph, spd, thr, always, scarf, order]
var flags: Array = []     # [x, y, col, ph, sc, dir]
var oy := 225.0
var lh := 237.0
var t := 0.0
var excite := 0.15
var target := 0.15
var flash: Array = []
var boost_side := -1
var boost_t := 0.0
var fill := 1.0
var light := 0.82
var rng := RandomNumberGenerator.new()

var mm := MultiMesh.new()
var fan_node := MultiMeshInstance2D.new()
var mat := ShaderMaterial.new()
var top_node := Node2D.new()
var flash_node := Node2D.new()
var bn_node := Node2D.new()      # boyanan bez (shader)
var bn_top := Node2D.new()       # portre + isim (boyanmaz)
var banner_spots: Array = []     # [x, y, tier]
var banners: Array = []          # [kind, x, y, ph, side, char]
var teams_c := [0, 1]
static var _cloth_box := {}      # doku adi -> Rect2 (0..1 normalize)


func setup(data_file: String, mask_file: String, light_: float) -> void:
	light = light_
	var d = JSON.parse_string(FileAccess.get_file_as_string("res://assets/" + data_file))
	var secs: Array = d["secs"] if d is Dictionary else d
	oy = d["oy"] if d is Dictionary else 95.0
	var mask := R.tex(mask_file)
	lh = mask.get_height()
	# Python random.Random(42) ile ayni dagilim gerekmez; tohumlu, kararli bir dagilim yeter
	var r := RandomNumberGenerator.new()
	r.seed = 42
	for s: Dictionary in secs:
		var sc: float = s.get("sc", 0.78 if int(s["tier"]) == 0 else 0.92)
		var step := 10.5 * sc
		var rows: Array[float] = []
		var y: float = s["y0"] + 12.0 * sc
		while y < s["y1"] + 14.0 * sc:
			rows.append(y)
			y += 11.5 * sc
		for ri in rows.size():
			var x: float = s["x0"] - 4.0 + (step / 2.0 if ri % 2 == 1 else 0.0)
			while x < s["x1"] + 6.0:
				var shade: int = [0, 0, 0, 1, 2][r.randi_range(0, 4)]
				fans.append([x + r.randf_range(-2, 2), rows[ri] + r.randf_range(-1.5, 1.5), s["col"], shade,
					r.randi_range(0, 3), r.randi_range(0, 4), sc, r.randf_range(0, 6.28), r.randf_range(5.5, 9.0),
					r.randf_range(0.45, 0.98), r.randf() < 0.02, r.randf() < 0.18, r.randf()])
				x += step
		if r.randf() < 0.55:
			flags.append([r.randf_range(s["x0"] + 30.0, s["x1"] - 30.0), s["y0"] + 20.0, s["col"],
				r.randf_range(0, 6), sc, 1 if r.randf() < 0.5 else -1])
	# pankart yerleri: ust sira (tutulan pankart + tabela/flama), alt sira (bayrak)
	var y0s: Array = []
	for s2: Dictionary in secs:
		y0s.append(float(s2["y0"]))
	y0s.sort()
	var top_y: float = y0s[0]
	var low_y: float = top_y + 70.0
	for yy: float in y0s:
		if yy > top_y + 50.0:
			low_y = yy
			break
	for x: float in [250.0, 1030.0]:
		banner_spots.append([x, top_y + 26.0, 0])
	for x: float in [460.0, 820.0]:
		banner_spots.append([x, low_y + 30.0, 1])
	for x: float in [385.0, 895.0]:
		banner_spots.append([x, top_y + 30.0, 2])
	# fan y'leri tribun katmanina gore (Python: ry - oy); burada dunya koordinatinda tutuyoruz
	_build_mesh()
	mat.shader = load("res://shaders/crowd.gdshader")
	mat.set_shader_parameter("tint_tex", R.tex("crowd_tint.png"))
	mat.set_shader_parameter("mask_tex", mask)
	mat.set_shader_parameter("mask_origin", Vector2(0, oy))
	mat.set_shader_parameter("mask_size", Vector2(mask.get_width(), lh))
	mat.set_shader_parameter("light", Vector3(light, light, minf(1.0, light + 18.0 / 255.0)))
	fan_node.multimesh = mm
	fan_node.texture = R.tex("crowd_atlas.png")
	fan_node.material = mat
	add_child(fan_node)
	add_child(top_node)
	top_node.draw.connect(_draw_flags)
	var bm := ShaderMaterial.new()
	bm.shader = load("res://shaders/banner.gdshader")
	bn_node.material = bm
	add_child(bn_node)
	bn_node.draw.connect(_draw_banners)
	add_child(bn_top)
	bn_top.draw.connect(_draw_banner_tops)
	var am := CanvasItemMaterial.new()
	am.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	flash_node.material = am
	add_child(flash_node)
	flash_node.draw.connect(_draw_flash)
	set_teams(0, 1)


func _build_mesh() -> void:
	var q := ArrayMesh.new()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = PackedVector2Array([Vector2(-0.5, -1), Vector2(0.5, -1), Vector2(0.5, 0), Vector2(-0.5, 0)])
	arr[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	q.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	mm.transform_format = MultiMesh.TRANSFORM_2D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = q
	mm.instance_count = fans.size()


func set_teams(c0: int, c1: int) -> void:
	var teams := ["k%d" % c0, "k%d" % c1]
	var mid := K.W / 2.0
	for i in fans.size():
		var f: Array = fans[i]
		var sc: float = f[6]
		var key: int = (1 if f[3] == 1 else 0) * 20 + int(f[4]) * 5 + int(f[5])
		mm.set_instance_transform_2d(i, Transform2D(0.0, Vector2(22.0 * sc, 34.0 * sc), 0.0, Vector2(f[0], f[1])))
		mm.set_instance_color(i, Color(sc, f[12], f[3] / 2.0, 1.0))
		var w: float = key * 8 + (4.0 if f[11] else 0.0) + (2.0 if f[10] else 0.0) + f[9]
		mm.set_instance_custom_data(i, Color(f[0], f[1], floorf(f[8] * 100.0) * 8.0 + f[7], w))
	for fl: Array in flags:
		fl[2] = teams[0 if fl[0] < mid else 1]
	teams_c = [c0, c1]
	banners.clear()
	var r := RandomNumberGenerator.new()
	r.seed = 7
	var count := [0, 0]
	for sp: Array in banner_spots:
		var side := 0 if sp[0] < mid else 1
		var kind := "bn_hold"
		if sp[2] == 2:
			kind = "bn_sign" if side == 0 else "bn_pennant"
		elif count[side] % 2 == 1:
			kind = "bn_flag"
		count[side] += 1
		banners.append([kind, sp[0], sp[1], r.randf_range(0, 6.28), side, [c0, c1][side]])
	var sh := PackedColorArray()
	for tm: String in teams:
		for k in 3:
			sh.append(TEAM[tm][k])
	mat.set_shader_parameter("shirts", sh)
	boost_side = -1
	boost_t = 0.0


func kick(amount: float, side: int = -1) -> void:
	target = maxf(target, amount)
	if amount >= 0.9:
		excite = 1.0
		boost_side = side
		boost_t = 3.5 if side == 0 or side == 1 else 0.0
	for i in int(amount * 8):
		flash.append([rng.randf_range(0, K.W), rng.randf_range(30, lh - 20), rng.randf_range(0.1, 0.25)])


func update(dt: float) -> void:
	t += dt
	if boost_t > 0.0:
		boost_t -= dt
	target += (0.15 - target) * minf(1.0, dt * 0.35)
	excite += (target - excite) * minf(1.0, dt * 4.0)
	var n := (0.3 + excite * excite * 18.0) * dt
	while n > 0.0:
		if rng.randf() < n:
			flash.append([rng.randf_range(0, K.W), rng.randf_range(30, lh - 20), rng.randf_range(0.08, 0.2)])
		n -= 1.0
	for f: Array in flash:
		f[2] -= dt
	flash = flash.filter(func(f): return f[2] > 0.0)
	if flash.size() > 80:
		flash = flash.slice(flash.size() - 80)
	mat.set_shader_parameter("t", t)
	mat.set_shader_parameter("excite", excite)
	mat.set_shader_parameter("fill", fill)
	mat.set_shader_parameter("sad", boost_side if boost_t > 0.0 else -1)
	top_node.queue_redraw()
	flash_node.queue_redraw()
	bn_node.queue_redraw()
	bn_top.queue_redraw()


func _draw_flags() -> void:
	var ex := excite
	for fl: Array in flags:
		var px: float = fl[0]
		var py: float = fl[1]
		var sc: float = fl[4]
		var d: float = fl[5]
		var amp := 1.2 + ex * 1.8
		var top := py - 34.0 * sc
		top_node.draw_line(Vector2(px, py + 10), Vector2(px, top), Color8(60, 50, 50), 2.0, true)
		var lw := 34.0 * sc
		var hh := 20.0 * sc
		var pt := PackedVector2Array()
		var pb := PackedVector2Array()
		for k in 7:
			var u := k / 6.0
			var off := sin(t * (2.2 + ex * 1.5) + fl[3] - u * 3.0) * amp * u
			pt.append(Vector2(px + d * lw * u, top + off))
			pb.append(Vector2(px + d * lw * u, top + hh + off))
		var poly := pt.duplicate()
		var mid := PackedVector2Array()
		for k in 7:
			mid.append(pt[k] + Vector2(0, hh * 0.38))
		for k in range(6, -1, -1):
			poly.append(pb[k])
			mid.append(pt[k] + Vector2(0, hh * 0.62))
		top_node.draw_colored_polygon(poly, TEAM[fl[2]][0])
		top_node.draw_colored_polygon(mid, Color8(250, 250, 250))
		poly.append(poly[0])
		top_node.draw_polyline(poly, OUTC, 1.0, true)


func _draw_flash() -> void:
	for f: Array in flash:
		R.glow(flash_node, Vector2(f[0], f[1] + oy - 10.0), 5.0 + f[2] * 30.0, Color8(255, 255, 235))


# ---------------------------------------------------------------- pankartlar
const BN_H := {"bn_hold": 44.0, "bn_flag": 52.0, "bn_sign": 50.0, "bn_pennant": 50.0}


## Bez bolgesinin sinirlari (portre/isim yerlesimi icin), bir kez hesaplanir.
static func cloth_box(name: String) -> Rect2:
	if _cloth_box.has(name):
		return _cloth_box[name]
	var tx := R.tex(name)
	var box := Rect2(0.15, 0.15, 0.7, 0.7)
	if tx:
		var img := tx.get_image()
		if img.is_compressed():
			img.decompress()
		img.convert(Image.FORMAT_RGBA8)
		var w := img.get_width() / 4
		var h := img.get_height() / 4
		img.resize(w, h, Image.INTERPOLATE_BILINEAR)
		var x0 := w
		var x1 := 0
		var y0 := h
		var y1 := 0
		for yy in h:
			for xx in w:
				var c := img.get_pixel(xx, yy)
				var mn := minf(c.r, minf(c.g, c.b))
				var mx := maxf(c.r, maxf(c.g, c.b))
				if c.a > 0.3 and mn > 0.6 and mx - mn < 0.16:
					x0 = mini(x0, xx)
					x1 = maxi(x1, xx)
					y0 = mini(y0, yy)
					y1 = maxi(y1, yy)
		if x1 > x0 and y1 > y0:
			box = Rect2(float(x0) / w, float(y0) / h, float(x1 - x0) / w, float(y1 - y0) / h)
	_cloth_box[name] = box
	return box


func _banner_rect(b: Array) -> Array:
	var sad := boost_side if boost_t > 0.0 else -1
	var happy: bool = sad < 0 or sad == b[4]
	var rate := (0.8 + excite * 1.2) if happy else 0.4
	var fr := int(t * rate + b[3]) % 2
	var name := "%s%d.png" % [b[0], fr]
	var tx := R.tex(name)
	if tx == null:
		return []
	var lift := excite * 3.0 * absf(sin(t * 2.5 + b[3])) if happy else 0.0
	var h: float = BN_H[b[0]]
	var w := tx.get_width() * h / tx.get_height()
	var rect := Rect2(b[1] - w / 2.0, b[2] + 20.0 - lift - h, w, h)
	return [tx, rect, name]


func _draw_banners() -> void:
	if fill < 1.0:
		return
	for b: Array in banners:
		var d := _banner_rect(b)
		if d.is_empty():
			continue
		var col: Color = TEAM["k%d" % b[5]][0]
		bn_node.draw_texture_rect(d[0], d[1], false, col)


func _draw_banner_tops() -> void:
	if fill < 1.0:
		return
	for b: Array in banners:
		var d := _banner_rect(b)
		if d.is_empty():
			continue
		var r: Rect2 = d[1]
		var cb := cloth_box(d[2])
		var cr := Rect2(r.position + cb.position * r.size, cb.size * r.size)
		var ch := cr.size.y
		var dd := ch * 0.62
		var col: Color = TEAM["k%d" % b[5]][0]
		var light := col.r + col.g + col.b > 2.2
		var por := R.portrait(b[5], 96)
		if b[0] == "bn_hold":
			var pc := Vector2(cr.position.x + cr.size.x * 0.24, cr.get_center().y)
			bn_top.draw_texture_rect(por, Rect2(pc - Vector2(dd, dd) / 2.0, Vector2(dd, dd)), false)
			var nm: String = K.DISPLAY_NAMES[b[5]]
			var fs := int(maxf(6.0, ch * 0.34))
			var tw := R.text_width(nm, fs)
			var maxw := cr.size.x * 0.52
			if tw > maxw:
				fs = int(fs * maxw / tw)
			R.text(bn_top, nm, fs, Vector2(cr.position.x + cr.size.x * 0.66, cr.get_center().y),
				Color8(25, 30, 50) if light else Color.WHITE, 0)
		else:
			bn_top.draw_texture_rect(por, Rect2(cr.get_center() - Vector2(dd, dd) / 2.0, Vector2(dd, dd)), false)
