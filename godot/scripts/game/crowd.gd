## Tribun taraftarlari (Python fx.Crowd birebir). Taraftarlar tek MultiMesh'te, GPU'da oynar.
class_name Crowd
extends Node2D

const TEAM := {
	"red": [Color8(225, 60, 60), Color8(250, 250, 250), Color8(185, 35, 40)],
	"blue": [Color8(60, 115, 225), Color8(245, 245, 252), Color8(35, 70, 165)],
	"yellow": [Color8(252, 205, 45), Color8(45, 45, 55), Color8(235, 165, 25)],
	"green": [Color8(70, 175, 70), Color8(250, 250, 250), Color8(35, 120, 50)],
	"white": [Color8(245, 245, 248), Color8(60, 165, 75), Color8(225, 228, 232)],
	"k0": [Color8(225, 55, 55), Color8(250, 250, 250), Color8(180, 30, 35)],
	"k1": [Color8(50, 105, 220), Color8(245, 245, 252), Color8(30, 65, 160)],
	"k2": [Color8(140, 146, 158), Color8(250, 210, 50), Color8(100, 106, 118)],
	"k3": [Color8(246, 246, 250), Color8(235, 195, 60), Color8(215, 220, 228)],
	"k4": [Color8(252, 205, 45), Color8(40, 40, 50), Color8(235, 165, 25)],
	"k5": [Color8(40, 140, 60), Color8(250, 250, 250), Color8(25, 95, 40)],
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
