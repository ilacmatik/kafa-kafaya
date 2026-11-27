## Dokunmatik kontroller: solda serbest joystick (sag/sol/asagi), sagda PUBG tarzi dugmeler.
## Tum dugmelerin yeri ve boyutu kullanici tarafindan duzenlenebilir (user://controls.json).
## Ekran biriminde (taban 1920x1080, genis ekranlarda yatayda genisler).
extends Control

signal pressed(action: String)
signal edit_closed

const SAVE_PATH := "user://controls.json"
const DEAD := 0.28
const DOWN_T := 0.55
const STRIP := 190.0
const MIN_R := 40.0
const MAX_R := 140.0
const LABELS := {"j": "ZIPLA", "k": "ŞUT", "d": "AŞIRTMA", "s": "SÜPER", "o": "OMUZ", "joy": "YÖN"}

## eylem -> [sagdan uzaklik, alttan uzaklik, yaricap]; "joy" icin [soldan, alttan, yaricap]
const DEFAULT_LAYOUT := {
	"j": [150.0, 120.0, 84.0],
	"k": [345.0, 92.0, 90.0],
	"d": [300.0, 285.0, 62.0],
	"s": [130.0, 305.0, 62.0],
	"o": [520.0, 70.0, 54.0],
	"joy": [230.0, 150.0, 110.0],
}
const BTN_ORDER := ["o", "d", "s", "k", "j"]

var enabled := true
var m  # match.gd
var layout := {}
var fingers := {}        # index -> eylem
var joy = null           # {"id","c","k"}

# --- duzenleme modu
var editing := false
var sel := "j"
var drag = null          # {"id", "a", "off"}
var pinch := {}          # index -> konum (iki parmakla boyut)
var pinch_d0 := 0.0
var pinch_r0 := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_load()


# ---------------------------------------------------------------- kayit
func _load() -> void:
	layout = DEFAULT_LAYOUT.duplicate(true)
	if FileAccess.file_exists(SAVE_PATH):
		var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
		if d is Dictionary:
			for a in d:
				if layout.has(a) and d[a] is Array and d[a].size() == 3:
					layout[a] = [float(d[a][0]), float(d[a][1]), float(d[a][2])]


func _save() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(layout))


# ---------------------------------------------------------------- geometri
func btn_pos(a: String) -> Vector2:
	var l: Array = layout[a]
	if a == "joy":
		return Vector2(l[0], size.y - l[1])
	return Vector2(size.x - l[0], size.y - l[1])


func _set_pos(a: String, p: Vector2) -> void:
	var r: float = layout[a][2]
	p.x = clampf(p.x, r, size.x - r)
	p.y = clampf(p.y, size.y * 0.25, size.y - r * 0.6)
	if a == "joy":
		layout[a][0] = p.x
	else:
		layout[a][0] = size.x - p.x
	layout[a][1] = size.y - p.y


func joy_r() -> float:
	return layout["joy"][2]


func pause_pos() -> Vector2:
	return Vector2(size.x / 2.0, 196.0)


func joy_home() -> Vector2:
	return btn_pos("joy")


func _hit(p: Vector2) -> String:
	var best := ""
	var bd := 1e9
	for a in BTN_ORDER:
		var r: float = layout[a][2]
		var d := p.distance_to(btn_pos(a))
		if d < r * 1.2 and d < bd:
			best = a
			bd = d
	if p.distance_to(pause_pos()) < 52.0:
		return "p"
	return best


# duzenleme ekranindaki ust dugmeler
func _edit_buttons() -> Dictionary:
	var cx := size.x / 2.0
	var y := size.y * 0.3
	return {
		"minus": Rect2(cx - 330, y, 110, 84),
		"plus": Rect2(cx - 200, y, 110, 84),
		"reset": Rect2(cx - 60, y, 190, 84),
		"save": Rect2(cx + 150, y, 190, 84),
	}


# ---------------------------------------------------------------- girdi
func _input(event: InputEvent) -> void:
	if not visible or not (enabled or editing):
		return
	var tr := get_global_transform_with_canvas().affine_inverse()
	if editing:
		_edit_input(event, tr)
		return
	if event is InputEventScreenTouch:
		var pos: Vector2 = tr * event.position
		if event.pressed:
			_down(event.index, pos)
		else:
			_up(event.index)
	elif event is InputEventScreenDrag:
		if joy != null and joy["id"] == event.index:
			_joy_move(tr * event.position)


func _down(id: int, p: Vector2) -> void:
	var a := _hit(p)
	if a != "":
		fingers[id] = a
		pressed.emit(a)
		get_viewport().set_input_as_handled()
		return
	var jr := joy_r()
	var zone := Rect2(0, size.y * 0.42, size.x * 0.42, size.y * 0.58)
	if joy == null and zone.has_point(p):
		var c := Vector2(clampf(p.x, jr + 16.0, zone.end.x - jr), clampf(p.y, zone.position.y + jr, size.y - jr - 12.0))
		joy = {"id": id, "c": c, "k": c}
		_joy_move(p)
		get_viewport().set_input_as_handled()


func _up(id: int) -> void:
	if joy != null and joy["id"] == id:
		joy = null
	fingers.erase(id)


func _joy_move(p: Vector2) -> void:
	var d: Vector2 = p - joy["c"]
	var jr := joy_r()
	if d.length() > jr:
		d = d.normalized() * jr
	joy["k"] = joy["c"] + d


func release_all() -> void:
	fingers.clear()
	joy = null


func held() -> Dictionary:
	var h := {}
	if editing:
		return h
	for id in fingers:
		h[fingers[id]] = true
	if joy != null:
		var v: Vector2 = (joy["k"] - joy["c"]) / joy_r()
		if v.x < -DEAD:
			h["l"] = true
		elif v.x > DEAD:
			h["r"] = true
		if v.y > DOWN_T:
			h["d"] = true
	return h


# ---------------------------------------------------------------- duzenleme
func start_edit() -> void:
	release_all()
	editing = true
	visible = true
	drag = null
	pinch.clear()


func _edit_input(event: InputEvent, tr: Transform2D) -> void:
	var idx := -1
	var pos := Vector2.ZERO
	var down := false
	var up := false
	var move := false
	if event is InputEventScreenTouch:
		idx = event.index
		pos = tr * event.position
		down = event.pressed
		up = not event.pressed
	elif event is InputEventScreenDrag:
		idx = event.index
		pos = tr * event.position
		move = true
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		idx = 99
		pos = tr * event.position
		down = event.pressed
		up = not event.pressed
	elif event is InputEventMouseMotion and drag != null and drag["id"] == 99:
		idx = 99
		pos = tr * event.position
		move = true
	elif event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		_resize(sel, 6.0 if event.button_index == MOUSE_BUTTON_WHEEL_UP else -6.0)
		return
	else:
		return
	get_viewport().set_input_as_handled()
	if down:
		pinch[idx] = pos
		if pinch.size() == 2:
			var ps: Array = pinch.values()
			pinch_d0 = maxf(1.0, (ps[0] as Vector2).distance_to(ps[1]))
			pinch_r0 = layout[sel][2]
			drag = null
			return
		var eb := _edit_buttons()
		for k in eb:
			if (eb[k] as Rect2).has_point(pos):
				_edit_action(k)
				return
		var best := ""
		var bd := 1e9
		for a in layout:
			var d := pos.distance_to(btn_pos(a))
			if d < layout[a][2] * 1.2 and d < bd:
				best = a
				bd = d
		if best != "":
			sel = best
			drag = {"id": idx, "a": best, "off": btn_pos(best) - pos}
	elif up:
		pinch.erase(idx)
		if drag != null and drag["id"] == idx:
			drag = null
	elif move:
		if pinch.has(idx):
			pinch[idx] = pos
		if pinch.size() == 2:
			var ps2: Array = pinch.values()
			var dd := (ps2[0] as Vector2).distance_to(ps2[1])
			layout[sel][2] = clampf(pinch_r0 * dd / pinch_d0, MIN_R, MAX_R)
			_set_pos(sel, btn_pos(sel))
		elif drag != null and drag["id"] == idx:
			_set_pos(drag["a"], pos + drag["off"])


func _resize(a: String, dr: float) -> void:
	layout[a][2] = clampf(layout[a][2] + dr, MIN_R, MAX_R)
	_set_pos(a, btn_pos(a))


func _edit_action(k: String) -> void:
	match k:
		"minus":
			_resize(sel, -8.0)
		"plus":
			_resize(sel, 8.0)
		"reset":
			layout = DEFAULT_LAYOUT.duplicate(true)
		"save":
			_save()
			editing = false
			drag = null
			pinch.clear()
			edit_closed.emit()


# ---------------------------------------------------------------- cizim
func _process(_d: float) -> void:
	queue_redraw()


func _draw() -> void:
	if not enabled and not editing:
		return
	if editing:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.02, 0.03, 0.08, 0.55))
	# alt kontrol seridi
	draw_rect(Rect2(0, size.y - STRIP, size.x, STRIP), Color(0.06, 0.16, 0.08, 0.92))
	draw_rect(Rect2(0, size.y - STRIP, size.x, 5), Color(0.92, 0.94, 0.92))
	var h := held()
	_draw_joy()
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
	for a in BTN_ORDER:
		var p := btn_pos(a)
		var r: float = layout[a][2]
		var tex := R.tex("tc_%s.png" % a)
		var is_on: bool = editing or h.has(a) or (a == "s" and full)
		if a == "s":
			if full and not editing:
				R.glow(self, p, r * 1.9 + 6.0 * sin(Time.get_ticks_msec() / 125.0), Color(pcol.r, pcol.g, pcol.b, 0.5))
			draw_arc(p, r + 9, 0, TAU, 64, Color8(10, 14, 30), 8.0, true)
			var k2 := clampf(meter / 100.0, 0.0, 1.0)
			if k2 > 0.01:
				draw_arc(p, r + 9, -PI / 2.0, -PI / 2.0 + TAU * k2, 64, pcol, 8.0, true)
		var dy := 4.0 if h.has(a) else 0.0
		if tex:
			draw_texture_rect(tex, Rect2(p - Vector2(r, r) + Vector2(0, dy), Vector2(r, r) * 2.0), false, Color(1, 1, 1, 1.0 if is_on else 0.68))
		var fs := int(clampf(r * 0.27, 16.0, 26.0))
		if a == "s":
			var ic := R.tex("pw_%s.png" % pw)
			if ic == null:
				ic = R.tex("fx_%s.png" % pw)
			if ic:
				var s := r * 0.7
				draw_texture_rect(ic, Rect2(p + Vector2(r * 0.62, r * 0.62) - Vector2(s, s) / 2.0, Vector2(s, s)), false)
			var lab: String = K.POWERS[pw][0] if full else "SÜPER %d%%" % int(meter)
			R.text(self, lab, fs, p + Vector2(0, r + fs + 4), pcol if full else Color.WHITE, 4)
		elif a == "d" or a == "j" or editing:
			var ly := r + fs
			if editing:
				ly = r * 0.62
			R.text(self, LABELS[a], fs, p + Vector2(0, ly), Color.WHITE, 4)
		if editing:
			_draw_sel_ring(a, p, r)
	if not editing:
		var pp := pause_pos()
		var pt := R.tex("tc_p.png")
		if pt:
			draw_texture_rect(pt, Rect2(pp - Vector2(36, 36), Vector2(72, 72)), false, Color(1, 1, 1, 0.8))
	else:
		_draw_edit_ui()


func _draw_sel_ring(a: String, p: Vector2, r: float) -> void:
	var on := a == sel
	var col := Color8(255, 205, 60) if on else Color(1, 1, 1, 0.45)
	var n := 28
	for i in n:
		if i % 2 == 0:
			var a0 := TAU * i / n
			draw_arc(p, r + 16, a0, a0 + TAU / n, 6, col, 4.0 if on else 2.5, true)


func _draw_joy() -> void:
	var jr := joy_r()
	var c: Vector2 = joy_home() if joy == null else joy["c"]
	var kpos: Vector2 = c if joy == null else joy["k"]
	var on := joy != null or editing
	var kr := jr * 0.45
	draw_circle(c, jr + 10, Color(0.04, 0.06, 0.13, 0.55 if on else 0.35))
	draw_arc(c, jr + 10, 0, TAU, 64, Color(1, 1, 1, 0.85 if on else 0.5), 5.0, true)
	draw_arc(c, jr * 0.55, 0, TAU, 48, Color(1, 1, 1, 0.3), 2.5, true)
	# yon oklari: sol, sag, asagi (yukari yok; ziplama sagdaki dugmede)
	for dir: Vector2 in [Vector2.LEFT, Vector2.RIGHT, Vector2.DOWN]:
		var tip := c + dir * (jr - 6)
		var side := Vector2(-dir.y, dir.x)
		draw_colored_polygon(PackedVector2Array([tip + dir * 12, tip - dir * 4 + side * 12, tip - dir * 4 - side * 12]), Color(1, 1, 1, 0.8 if on else 0.5))
	draw_circle(kpos + Vector2(0, 4), kr, Color(0.03, 0.05, 0.12, 0.7))
	draw_circle(kpos, kr, Color8(70, 140, 235, 245 if on else 160))
	draw_circle(kpos - Vector2(0, kr * 0.2), kr * 0.64, Color8(140, 195, 255, 245 if on else 160))
	draw_circle(kpos + Vector2(0, 3), kr * 0.66, Color8(80, 150, 240, 245 if on else 160))
	draw_arc(kpos, kr, 0, TAU, 48, Color(1, 1, 1, 0.95 if on else 0.6), 4.0, true)
	if editing:
		R.text(self, LABELS["joy"], 22, c + Vector2(0, -jr - 34), Color.WHITE, 4)
		_draw_sel_ring("joy", c, jr + 10)


func _draw_edit_ui() -> void:
	var y0 := size.y * 0.3
	R.text(self, "TUŞ DÜZENİ", 64, Vector2(size.x / 2.0, y0 - 120), Color8(255, 205, 60), 6)
	R.text(self, "Sürükle: taşı  •  İki parmak / + − : boyut", 26, Vector2(size.x / 2.0, y0 - 56), Color.WHITE, 3, HORIZONTAL_ALIGNMENT_CENTER, false)
	var eb := _edit_buttons()
	var labs := {"minus": "−", "plus": "+", "reset": "SIFIRLA", "save": "KAYDET"}
	var cols := {"minus": Color8(40, 70, 150), "plus": Color8(40, 70, 150), "reset": Color8(200, 70, 60), "save": Color8(40, 160, 80)}
	for k in eb:
		var r: Rect2 = eb[k]
		R.panel(self, r, cols[k], 18, Color(1, 1, 1, 0.9), 3)
		R.text(self, labs[k], 44 if k in ["minus", "plus"] else 30, r.get_center(), Color.WHITE, 4)
	R.text(self, "Seçili: " + LABELS[sel], 28, Vector2(size.x / 2.0, y0 + 120), Color8(255, 205, 60), 3)
