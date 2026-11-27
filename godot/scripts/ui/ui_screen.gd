## Menu ekranlari icin taban: 1280x720 mantiksal koordinat, yukseklige gore olceklenir ve
## yatayda ortalanir (genis ekranda kenarlar acilir). Dugmeler her cizimde hit[] icine kaydedilir.
class_name UIScreen
extends Node2D

const LW := 1280.0
const LH := 720.0
const GOLD := Color8(255, 205, 60)
const WHITE := Color.WHITE
const DARK := Color8(14, 18, 40)
const P_COLORS := [Color8(70, 160, 255), Color8(255, 85, 85)]

var s := 1.0
var vp := Vector2.ZERO
var t := 0.0
var view_l := 0.0
var view_r := LW
var hit := {}          # ad -> Rect2 (mantiksal)
var _hit_next := {}
var focus := ""
var focus_t := 0.0
var press := ""
var press_t := 0.0
var sfx: AudioStreamPlayer
var toast := ["", 0.0]


func _ready() -> void:
	R.init()
	get_tree().quit_on_go_back = false
	sfx = AudioStreamPlayer.new()
	add_child(sfx)
	_layout()


func _layout() -> void:
	vp = get_viewport_rect().size
	s = vp.y / LH
	position = Vector2((vp.x - LW * s) / 2.0, 0.0)
	scale = Vector2(s, s)
	view_l = -position.x / s
	view_r = view_l + vp.x / s


func _process(dt: float) -> void:
	t += dt
	focus_t += dt
	press_t += dt
	toast[1] = maxf(0.0, toast[1] - dt)
	_layout()
	tick(dt)
	queue_redraw()


func _draw() -> void:
	_hit_next = {}
	paint()
	if toast[1] > 0.0:
		var a := clampf(toast[1] / 0.3, 0.0, 1.0)
		var w := R.text_width(toast[0], 26) + 70.0
		var r := Rect2(LW / 2.0 - w / 2.0, 600, w, 56)
		R.panel(self, r, Color(0.04, 0.06, 0.16, 0.92 * a), 24, Color(GOLD.r, GOLD.g, GOLD.b, a), 3)
		R.text(self, toast[0], 26, r.get_center(), Color(1, 1, 1, a), 3)
	hit = _hit_next


# ---- alt siniflarin dolduracagi
func tick(_dt: float) -> void:
	pass


func paint() -> void:
	pass


func on_tap(_name: String) -> void:
	pass


func on_key(_kc: int) -> void:
	pass


func on_back() -> void:
	pass


# ---- yardimcilar
func reg(name: String, r: Rect2) -> void:
	_hit_next[name] = r


func say(msg: String, dur: float = 1.8) -> void:
	toast = [msg, dur]


func play(name: String) -> void:
	var st := load("res://assets/sfx/%s.wav" % name) if ResourceLoader.exists("res://assets/sfx/%s.wav" % name) else null
	if st:
		sfx.stream = st
		sfx.play()


func set_focus(name: String) -> void:
	if name != focus:
		focus = name
		focus_t = 0.0
		if name != "":
			play("click")


## Basma animasyonu katsayisi (0..1)
func pressed_k(name: String) -> float:
	if press != name:
		return 0.0
	return clampf(1.0 - press_t / 0.18, 0.0, 1.0)


## Dokuyu gorunur alani kaplayacak sekilde (en-boy korunarak) ciz.
func cover(tex: Texture2D, tint: Color = Color.WHITE) -> void:
	if tex == null:
		return
	var w := view_r - view_l
	var k := maxf(w / tex.get_width(), LH / tex.get_height())
	var sz := Vector2(tex.get_width(), tex.get_height()) * k
	draw_texture_rect(tex, Rect2(Vector2((view_l + view_r) / 2.0, LH / 2.0) - sz / 2.0, sz), false, tint)


## Arka plani mantiksal alana (1280x720) tam oturt; genis ekranda yanlari aynalanmis kopyayla doldur.
## Boylece arka plandaki paneller/podyumlar ustune cizilen ogelerle hizali kalir.
func fit_mirror(tex: Texture2D) -> void:
	if tex == null:
		return
	var tw := float(tex.get_width())
	var k := tw / LW
	draw_texture_rect(tex, Rect2(0, 0, LW, LH), false)
	var wl := -view_l
	if wl > 0.5:
		var src := minf(wl, LW) * k
		draw_set_transform(Vector2(0, 0), 0.0, Vector2(-1, 1))
		draw_texture_rect_region(tex, Rect2(0, 0, minf(wl, LW), LH), Rect2(0, 0, src, tex.get_height()))
		draw_set_transform(Vector2.ZERO)
	var wr := view_r - LW
	if wr > 0.5:
		var src2 := minf(wr, LW) * k
		draw_set_transform(Vector2(2.0 * LW, 0), 0.0, Vector2(-1, 1))
		draw_texture_rect_region(tex, Rect2(LW - minf(wr, LW), 0, minf(wr, LW), LH), Rect2(tw - src2, 0, src2, tex.get_height()))
		draw_set_transform(Vector2.ZERO)
	# kenar gecisini yumusat
	if wl > 0.5:
		_edge_shade(0.0, -1.0)
	if wr > 0.5:
		_edge_shade(LW, 1.0)


func _edge_shade(x: float, d: float) -> void:
	for i in 8:
		var w := 6.0
		draw_rect(Rect2(x + d * i * w - (w if d < 0 else 0.0), 0, w, LH), Color(0.01, 0.02, 0.06, 0.28 * (1.0 - i / 8.0)))
	var wide := (view_r - view_l - LW) / 2.0
	# disa dogru koyulasan gecis (aynali kopya fark edilmesin)
	var n := 12
	for i in n:
		var w2 := wide / n
		var xx := x + i * w2 if d > 0 else x - (i + 1) * w2
		draw_rect(Rect2(xx, 0, w2 + 0.5, LH), Color(0.01, 0.02, 0.06, 0.3 + 0.45 * float(i) / n))


## Hap seklindeki dugme dokusunu kenarlarini bozmadan genislet (3 parca).
func slice3(tex: Texture2D, r: Rect2, mod: Color = Color.WHITE) -> void:
	if tex == null:
		return
	var tw := float(tex.get_width())
	var th := float(tex.get_height())
	var f := r.size.y / th
	var cap := minf(th * 0.6, tw / 2.0 - 1.0)
	var capw := minf(cap * f, r.size.x / 2.0)
	var capsrc := capw / f
	draw_texture_rect_region(tex, Rect2(r.position, Vector2(capw, r.size.y)), Rect2(0, 0, capsrc, th), mod)
	draw_texture_rect_region(tex, Rect2(r.end.x - capw, r.position.y, capw, r.size.y), Rect2(tw - capsrc, 0, capsrc, th), mod)
	if r.size.x > capw * 2.0:
		draw_texture_rect_region(tex, Rect2(r.position.x + capw, r.position.y, r.size.x - 2.0 * capw, r.size.y),
			Rect2(capsrc, 0, tw - 2.0 * capsrc, th), mod)


## Basit renkli dugme (yuvarlak koseli, parlak serit)
func flat_button(name: String, r: Rect2, label: String, col: Color, fs: int = 26, enabled: bool = true) -> void:
	var on := focus == name
	var pk := pressed_k(name)
	var rr := r.grow(-pk * 4.0 + (2.0 if on else 0.0))
	reg(name, r)
	R.panel(self, rr.grow(3), Color(0, 0, 0, 0.45), rr.size.y * 0.4)
	var c := col if enabled else col.lerp(Color(0.25, 0.27, 0.33), 0.7)
	R.panel(self, rr, c, rr.size.y * 0.36, GOLD if on else Color(1, 1, 1, 0.85), 3.0 if on else 2.0)
	draw_rect(Rect2(rr.position + Vector2(rr.size.y * 0.3, 5), Vector2(rr.size.x - rr.size.y * 0.6, rr.size.y * 0.16)), Color(1, 1, 1, 0.16))
	R.text(self, label, fs, rr.get_center(), WHITE if enabled else Color(1, 1, 1, 0.6), 3)


# ---- girdi
func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
		var p := to_local(e.position)
		var name := _hit_at(p)
		if name != "":
			press = name
			press_t = 0.0
			focus = name
			on_tap(name)
			get_viewport().set_input_as_handled()
	elif e is InputEventMouseMotion and not DisplayServer.is_touchscreen_available():
		var n2 := _hit_at(to_local(e.position))
		if n2 != "":
			set_focus(n2)
	elif e is InputEventKey and e.pressed and not e.echo:
		if e.physical_keycode == KEY_ESCAPE:
			on_back()
		else:
			on_key(e.physical_keycode)


func _hit_at(p: Vector2) -> String:
	var keys := hit.keys()
	for i in range(keys.size() - 1, -1, -1):
		if (hit[keys[i]] as Rect2).has_point(p):
			return keys[i]
	return ""


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		on_back()
