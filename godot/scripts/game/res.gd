## Varlik yukleyici ve onbellek (dokular, pozlar, yazi tipleri, portreler).
class_name R
extends RefCounted

const POSES := ["idle", "run1", "run2", "kick", "jump", "shoulder", "bike", "celeb"]

static var _tex := {}
static var _anchors := {}
static var _portraits := {}
static var font_title: FontFile
static var font_body: FontFile
static var _ready := false


static func init() -> void:
	if _ready:
		return
	_ready = true
	font_title = load("res://assets/fonts/FiraSans-BlackItalic.ttf")
	font_body = load("res://assets/fonts/FiraSans-Black.ttf")
	for f in [font_title, font_body]:
		f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
		f.hinting = TextServer.HINTING_LIGHT
		f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_AUTO
	var fa := FileAccess.open("res://assets/anchors.json", FileAccess.READ)
	if fa:
		var d = JSON.parse_string(fa.get_as_text())
		if d is Dictionary:
			_anchors = d


static func tex(name: String) -> Texture2D:
	if _tex.has(name):
		return _tex[name]
	var path := "res://assets/" + name
	var t: Texture2D = null
	if ResourceLoader.exists(path):
		t = load(path)
	_tex[name] = t
	return t


static func pose(char: int, p: String) -> Texture2D:
	var t := tex("p%d_%s.png" % [char, p])
	if t == null and p != "idle":
		t = tex("p%d_idle.png" % char)
	return t


static func anchor(char: int, key: String, default_v: float) -> float:
	return float(_anchors.get("p%d_%s" % [char, key], default_v))


## Kahramanin rig kafasi: yuzu ortalayan kare (ust: sac payi, alt: cene + biraz boyun)
static func _head_square(char: int) -> Image:
	var rig: String = K.CHARACTERS[char]["rig"]
	var img: Image = tex("rig/%s/head.png" % rig).get_image()
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	var c: Vector2 = Rig.def(rig)["head_c"]
	var side := int(maxf(img.get_width(), img.get_height() * 0.8) * 1.04)
	var out := Image.create(side, side, false, Image.FORMAT_RGBA8)
	var ox := int(side / 2.0 - c.x)
	var oy := int(side * 0.54 - c.y)
	out.blend_rect(img, Rect2i(0, 0, img.get_width(), img.get_height()), Vector2i(ox, oy))
	return out


## Karakterin kafasindan yuvarlak portre (bir kez uretilir).
static func portrait(char: int, size: int = 128) -> Texture2D:
	var key := "%d:%d" % [char, size]
	if _portraits.has(key):
		return _portraits[key]
	var head := _head_square(char)
	head.resize(size, size, Image.INTERPOLATE_LANCZOS)
	var c := size / 2.0
	for yy in size:
		for xx in size:
			var d := Vector2(xx + 0.5 - c, yy + 0.5 - c).length()
			if d > c - 1.0:
				var col := head.get_pixel(xx, yy)
				col.a *= clampf(c - d, 0.0, 1.0)
				head.set_pixel(xx, yy, col)
	var t := ImageTexture.create_from_image(head)
	_portraits[key] = t
	return t


## Daireden tasan portre: alt kisim daireye kirpilir, sac/kafa ustten biraz disari tasar (3B etkisi).
## Doku SxS; daire merkezi (S/2, S*0.6), yaricapi S*0.35. Cizerken daire kutusunu pop_rect() ile al.
static func portrait_pop(char: int, size: int = 192) -> Texture2D:
	var key := "pop%d:%d" % [char, size]
	if _portraits.has(key):
		return _portraits[key]
	var head := _head_square(char)
	var cx := size / 2.0
	var cy := size * 0.6
	var rc := size * 0.35
	var box := int(rc * 2.0 * 1.12)
	head.resize(box, box, Image.INTERPOLATE_LANCZOS)
	var out := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var ox := int(cx - box / 2.0)
	var oy := int(cy - rc * 1.0 - rc * 0.24)
	out.blend_rect(head, Rect2i(0, 0, box, box), Vector2i(ox, oy))
	for yy in size:
		for xx in size:
			var col := out.get_pixel(xx, yy)
			if col.a <= 0.0:
				continue
			var d := Vector2(xx + 0.5 - cx, yy + 0.5 - cy).length()
			var k := clampf(rc - d, 0.0, 1.0)
			# merkezin ustunde: daire disina tasmaya izin ver (yanlardan fazla genislemeden)
			if yy + 0.5 < cy and absf(xx + 0.5 - cx) < rc * 1.04:
				k = 1.0
			if k < 1.0:
				col.a *= k
				out.set_pixel(xx, yy, col)
	var t := ImageTexture.create_from_image(out)
	_portraits[key] = t
	return t


## portrait_pop dokusunu, daire merkezi c ve yaricapi r olacak sekilde yerlestiren dikdortgen
static func pop_rect(c: Vector2, r: float) -> Rect2:
	var s := r / 0.35
	return Rect2(c.x - s / 2.0, c.y - s * 0.6, s, s)


## Yazi ciz: dis cizgili (oyun basligi stili).
static func text(ci: CanvasItem, s: String, size: int, pos: Vector2, col: Color = Color.WHITE,
		outline: int = 4, align: int = HORIZONTAL_ALIGNMENT_CENTER, title: bool = true,
		ocol: Color = Color(0.04, 0.05, 0.12, 0.95)) -> void:
	var f: Font = font_title if title else font_body
	var w := f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var x := pos.x
	if align == HORIZONTAL_ALIGNMENT_CENTER:
		x -= w / 2.0
	elif align == HORIZONTAL_ALIGNMENT_RIGHT:
		x -= w
	var base := pos.y + f.get_ascent(size) / 2.0 - f.get_descent(size) / 2.0
	if outline > 0:
		ci.draw_string_outline(f, Vector2(x, base), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, outline * 2, ocol)
	ci.draw_string(f, Vector2(x, base), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)


static func text_width(s: String, size: int, title: bool = true) -> float:
	var f: Font = font_title if title else font_body
	return f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x


## Dokuyu ciz; flip=true ise dikdortgen icinde yatay aynala (ust donusum kullanilmamaliysa).
static func draw_tex(ci: CanvasItem, t: Texture2D, r: Rect2, flip: bool = false, col: Color = Color.WHITE) -> void:
	if flip:
		ci.draw_set_transform(Vector2(r.position.x + r.end.x, 0.0), 0.0, Vector2(-1.0, 1.0))
		ci.draw_texture_rect(t, r, false, col)
		ci.draw_set_transform(Vector2.ZERO)
	else:
		ci.draw_texture_rect(t, r, false, col)


## Yuvarlak koseli panel.
static func panel(ci: CanvasItem, r: Rect2, bg: Color, radius: float = 14.0, border: Color = Color(0, 0, 0, 0),
		bw: float = 0.0) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.set_corner_radius_all(int(radius))
	sb.anti_aliasing = true
	if bw > 0.0:
		sb.border_color = border
		sb.set_border_width_all(int(bw))
	ci.draw_style_box(sb, r)


## Yumusak isik halkasi (radyal gradyan).
static var _glow: Texture2D
static func glow_tex() -> Texture2D:
	if _glow == null:
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1))
		g.set_color(1, Color(1, 1, 1, 0))
		g.add_point(0.35, Color(1, 1, 1, 0.55))
		var gt := GradientTexture2D.new()
		gt.gradient = g
		gt.fill = GradientTexture2D.FILL_RADIAL
		gt.fill_from = Vector2(0.5, 0.5)
		gt.fill_to = Vector2(1.0, 0.5)
		gt.width = 128
		gt.height = 128
		_glow = gt
	return _glow


static func glow(ci: CanvasItem, pos: Vector2, radius: float, col: Color) -> void:
	ci.draw_texture_rect(glow_tex(), Rect2(pos - Vector2(radius, radius), Vector2(radius, radius) * 2.0), false, col)
