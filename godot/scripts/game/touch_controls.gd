## Dokunmatik kontroller: solda serbest joystick (yukari = zipla), sagda PUBG tarzi dugmeler.
## Ekran biriminde (taban 1920x1080, genis ekranlarda yatayda genisler).
extends Control

signal pressed(action: String)

const JOY_R := 110.0
const DEAD := 0.28
const JUMP_T := 0.55

var enabled := true
var m  # match.gd
# eylem -> [sagdan uzaklik, alttan uzaklik, yaricap]
var layout := {
	"k": [324.0, 87.0, 93.0],
	"d": [129.0, 111.0, 75.0],
	"s": [129.0, 282.0, 62.0],
	"o": [498.0, 60.0, 57.0],
}
var fingers := {}        # index -> eylem
var joy = null           # {"id","c","k"}
var held_actions := {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)


func btn_pos(a: String) -> Vector2:
	var vp := size
	var l: Array = layout[a]
	return Vector2(vp.x - l[0], vp.y - l[1])


func pause_pos() -> Vector2:
	return Vector2(size.x / 2.0, 196.0)


func joy_home() -> Vector2:
	return Vector2(230.0, size.y - 150.0)


func _hit(p: Vector2) -> String:
	var best := ""
	var bd := 1e9
	for a in layout:
		var r: float = layout[a][2]
		var d := p.distance_to(btn_pos(a))
		if d < r * 1.25 and d < bd:
			best = a
			bd = d
	if p.distance_to(pause_pos()) < 52.0:
		return "p"
	return best


func _input(event: InputEvent) -> void:
	if not enabled or not visible:
		return
	if event is InputEventScreenTouch:
		var pos: Vector2 = get_global_transform_with_canvas().affine_inverse() * event.position
		if event.pressed:
			_down(event.index, pos)
		else:
			_up(event.index)
	elif event is InputEventScreenDrag:
		var pos2: Vector2 = get_global_transform_with_canvas().affine_inverse() * event.position
		if joy != null and joy["id"] == event.index:
			_joy_move(pos2)


func _down(id: int, p: Vector2) -> void:
	var a := _hit(p)
	if a != "":
		fingers[id] = a
		pressed.emit(a)
		get_viewport().set_input_as_handled()
		return
	var zone := Rect2(0, size.y * 0.42, size.x * 0.42, size.y * 0.58)
	if joy == null and zone.has_point(p):
		var c := Vector2(clampf(p.x, JOY_R + 16.0, zone.end.x - JOY_R), clampf(p.y, zone.position.y + JOY_R, size.y - JOY_R - 12.0))
		joy = {"id": id, "c": c, "k": c}
		_joy_move(p)
		get_viewport().set_input_as_handled()


func _up(id: int) -> void:
	if joy != null and joy["id"] == id:
		joy = null
	fingers.erase(id)


func _joy_move(p: Vector2) -> void:
	var d: Vector2 = p - joy["c"]
	if d.length() > JOY_R:
		d = d.normalized() * JOY_R
	joy["k"] = joy["c"] + d


func release_all() -> void:
	fingers.clear()
	joy = null


func held() -> Dictionary:
	var h := {}
	for id in fingers:
		h[fingers[id]] = true
	if joy != null:
		var v: Vector2 = (joy["k"] - joy["c"]) / JOY_R
		if v.x < -DEAD:
			h["l"] = true
		elif v.x > DEAD:
			h["r"] = true
		if v.y < -JUMP_T:
			h["j"] = true
	return h


func _process(_d: float) -> void:
	queue_redraw()


func _draw() -> void:
	if not enabled:
		return
	# alt kontrol seridi
	var strip := 190.0
	draw_rect(Rect2(0, size.y - strip, size.x, strip), Color(0.06, 0.16, 0.08, 0.92))
	draw_rect(Rect2(0, size.y - strip, size.x, 5), Color(0.92, 0.94, 0.92))
	var h := held()
	# joystick
	var c: Vector2 = joy_home() if joy == null else joy["c"]
	var kpos: Vector2 = c if joy == null else joy["k"]
	var on := joy != null
	draw_circle(c, JOY_R + 10, Color(0.04, 0.06, 0.13, 0.55 if on else 0.35))
	draw_arc(c, JOY_R + 10, 0, TAU, 64, Color(1, 1, 1, 0.85 if on else 0.5), 5.0, true)
	draw_arc(c, JOY_R * 0.55, 0, TAU, 48, Color(1, 1, 1, 0.3), 2.5, true)
	for k in 4:
		var a := k * PI / 2.0
		var dir := Vector2(cos(a), -sin(a))
		var tip := c + dir * (JOY_R - 6)
		var side := Vector2(-dir.y, dir.x)
		draw_colored_polygon(PackedVector2Array([tip + dir * 12, tip - dir * 4 + side * 12, tip - dir * 4 - side * 12]), Color(1, 1, 1, 0.8 if on else 0.5))
	draw_circle(kpos + Vector2(0, 4), 50, Color(0.03, 0.05, 0.12, 0.7))
	draw_circle(kpos, 50, Color8(70, 140, 235, 245 if on else 160))
	draw_circle(kpos - Vector2(0, 10), 32, Color8(140, 195, 255, 245 if on else 160))
	draw_circle(kpos + Vector2(0, 3), 33, Color8(80, 150, 240, 245 if on else 160))
	draw_arc(kpos, 50, 0, TAU, 48, Color(1, 1, 1, 0.95 if on else 0.6), 4.0, true)
	# super bilgisi
	var meter := 0.0
	var pw := "fire"
	if m != null and m.world != null:
		var me: SimPlayer = m.world.players[m.me]
		meter = me.meter
		pw = me.stats["power"]
		if me.armed > 0.0:
			meter = 100.0
	var pcol: Color = K.POWERS[pw][1]
	var full := meter >= 100.0
	for a in layout:
		var p := btn_pos(a)
		var r: float = layout[a][2]
		var tex := R.tex("tc_%s.png" % a)
		var is_on: bool = h.has(a) or (a == "s" and full)
		if a == "s":
			if full:
				R.glow(self, p, r * 1.9 + 6.0 * sin(Time.get_ticks_msec() / 125.0), Color(pcol.r, pcol.g, pcol.b, 0.5))
			draw_arc(p, r + 9, 0, TAU, 64, Color8(10, 14, 30), 8.0, true)
			var k2 := clampf(meter / 100.0, 0.0, 1.0)
			if k2 > 0.01:
				draw_arc(p, r + 9, -PI / 2.0, -PI / 2.0 + TAU * k2, 64, pcol, 8.0, true)
		var dy := 4.0 if h.has(a) else 0.0
		if tex:
			draw_texture_rect(tex, Rect2(p - Vector2(r, r) + Vector2(0, dy), Vector2(r, r) * 2.0), false, Color(1, 1, 1, 1.0 if is_on else 0.68))
		if a == "s":
			var ic := R.tex("pw_%s.png" % pw)
			if ic == null:
				ic = R.tex("fx_%s.png" % pw)
			if ic:
				var s := r * 0.7
				draw_texture_rect(ic, Rect2(p + Vector2(r * 0.62, r * 0.62) - Vector2(s, s) / 2.0, Vector2(s, s)), false)
			var lab: String = K.POWERS[pw][0] if full else "SÜPER %d%%" % int(meter)
			R.text(self, lab, 22, p + Vector2(0, r + 26), pcol if full else Color.WHITE, 4)
		elif a == "d":
			R.text(self, "AŞIRTMA", 22, p + Vector2(0, r + 22), Color.WHITE, 4)
	# duraklat
	var pp := pause_pos()
	var pt := R.tex("tc_p.png")
	if pt:
		draw_texture_rect(pt, Rect2(pp - Vector2(36, 36), Vector2(72, 72)), false, Color(1, 1, 1, 0.8))
