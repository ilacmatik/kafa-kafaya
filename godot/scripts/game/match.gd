## Mac sahnesi: simulasyonu 120 Hz calistirir, girdileri toplar, olaylardan efekt/ses uretir.
extends Node2D

const GOAL_LINES := {
	"super": ["SÜPER GÜÇ! DURDURULAMAZ!", "BU ŞUT DEĞİL, FÜZE!", "KALECİ ERİDİ GİTTİ!", "GÜÇ SENDE, GOL BİZDE!"],
	"head": ["KAFAYLA ÇAKTI!", "KAFA ÇALIŞIYOR MAŞALLAH!", "KAFA GOLÜ! NE YÜKSELDİ AMA!", "KAFANI KULLAN DEMİŞTİM!"],
	"lob": ["AŞIRTMA! BAKAKALDI!", "GÖKYÜZÜNDEN DÜŞTÜ!", "TOP KAFANIN ÜSTÜNDEN UÇTU!", "YAĞMUR GİBİ İNDİ!"],
	"flick": ["TOPUKLA! ŞOV YAPIYOR!", "TOPUK GOLÜ! AYIP OLDU!", "BAKMADAN ATTI!"],
	"own": ["KENDİ KALESİNE! TEŞEKKÜRLER!", "ÇOK AYIP, KENDİ KALENE!", "HEDİYE GOL! SAĞ OL!", "YANLIŞ KALE KARDEŞİM!"],
	"hard": ["ÇOK SERT! TUTABİLİRSEN TUT!", "FÜZE GİBİ GİRDİ!", "FİLEYİ YIRTTI!", "BU NE VURUŞ BE!", "ELİNİ YAKARDI!"],
	"volley": ["VOLE! HAVADA YAKALADI!", "NE VOLE AMA!", "DÜŞMEDEN VURDU!"],
	"curve": ["KAVİSLİ ŞUT! KIVRILDI GİRDİ!", "FALSO VERDİ, AĞLARA!", "MUZ GİBİ KIVRILDI!"],
	"bicycle": ["RÖVAŞATA! İNANILMAZ!", "TERS MAKAS! FİLELER!", "BU GOL YILIN GOLÜ!", "HAVADA TAKLA ATTI!"],
	"smash": ["SMAÇ KAFA! YERE GÖMDÜ!", "YUKARIDAN ÇAKTI!", "KAFAYI GÖMDÜ GİTTİ!", "VOLEYBOL MU OYNUYORUZ?"],
	"power": ["ŞARJLI FÜZE!", "BEKLEDİ, BEKLEDİ... BAM!", "TAM GÜÇ! FİLE DAYANMADI!", "BU ŞUTA KALE DAYANMAZ!"],
	"any": ["NASIL ATTIM AMA!", "KALECİ NEREDEYDİ?", "UYUMA, MAÇ VAR!", "TAM DOKSANA!", "BİR DAHA DENE!",
		"ÇOK KOLAY OLDU!", "BU DA MI GOL?", "DERS GİBİ GOL!"],
}
const PU_TEXT := {"speed": "HIZ!", "jump": "SÜPER ZIPLAMA!", "shield": "BUZ KALKAN!", "freeze": "DONDURMA!", "gold": "SÜPER DOLDU!"}
const GOLD := Color8(255, 205, 60)
const P_COLORS := [Color8(70, 160, 255), Color8(255, 85, 85)]

var world: SimWorld
var bot: SimBot
var mode := "bot"
var me := 0
var stadium := 1
var t := 0.0
var intro := 2.8
var touch_on := false
var paused := false
var over_t := 0.0
var shake := 0.0
var ref_x := 640.0
var ripple = null
var pstate := [{"sq": 0.0, "st": 0.0, "air": false}, {"sq": 0.0, "st": 0.0, "air": false}]
var parts: Array = []
var floaters: Array = []    # [metin, x, y, omur, renk]
var banner = null           # [metin, omur, renk, alt satir]
var goal_flash := 0.0
var press := {"k": false, "s": false, "o": false, "f": false}
var last_down := -9.0
var lob_until := -9.0
var rng := RandomNumberGenerator.new()

@onready var field: Node2D = $Field
@onready var hud: Node2D = $HUDLayer/HUD
@onready var touchc: Control = $TouchLayer/Touch
@onready var overlay: Node2D = $OverLayer/Overlay
@onready var sfx: Node = $Sfx


func _ready() -> void:
	R.init()
	rng.randomize()
	get_tree().quit_on_go_back = false
	touch_on = OS.has_feature("mobile") or OS.get_environment("KAFA_DOKUNMATIK") == "1"
	mode = Game.mode
	stadium = Game.stadium
	world = SimWorld.new(Game.chars[0], Game.chars[1], Game.duration, Game.weather, true)
	world.phase_t += intro
	bot = SimBot.new(1, Game.level)
	field.m = self
	hud.m = self
	overlay.draw.connect(_draw_overlay)
	touchc.m = self
	touchc.enabled = touch_on
	touchc.visible = touch_on
	touchc.pressed.connect(_on_touch_pressed)
	sfx.start_crowd()


# ---------------------------------------------------------------- yardimci (cizim icin)
func label_for(i: int) -> String:
	if mode == "local2":
		return "P%d" % (i + 1)
	return "SEN" if i == me else ""


func hud_tag(i: int) -> String:
	if mode == "local2":
		return "P%d" % (i + 1)
	if mode == "bot":
		return "SEN" if i == 0 else "CPU"
	return "SEN" if i == me else "RAKİP"


func is_local(i: int) -> bool:
	return mode == "local2" or i == me


func super_hint(_i: int) -> String:
	return "DOKUN" if touch_on else "R / ↓ ↓"


# ---------------------------------------------------------------- girdi
func _on_touch_pressed(a: String) -> void:
	match a:
		"k":
			press["k"] = true
		"d":
			press["f"] = true
		"s":
			press["s"] = true
		"o":
			press["o"] = true
		"p":
			_toggle_pause()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var kc: int = event.physical_keycode
		if paused:
			if kc == KEY_ESCAPE or kc == KEY_SPACE or kc == KEY_ENTER:
				_toggle_pause()
			elif kc == KEY_Q:
				_restart()
			return
		if world.phase == "over" and over_t > 1.2:
			if kc == KEY_ENTER or kc == KEY_SPACE:
				_restart()
			return
		match kc:
			KEY_ESCAPE, KEY_P:
				_toggle_pause()
			KEY_SPACE, KEY_K:
				press["k"] = true
			KEY_R:
				press["s"] = true
			KEY_E, KEY_CTRL:
				press["o"] = true
			KEY_Q, KEY_F:
				press["f"] = true
			KEY_S, KEY_DOWN:
				if t - last_down < 0.35:
					press["s"] = true
					last_down = -9.0
				else:
					last_down = t
	elif (event is InputEventScreenTouch and event.pressed) or (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT):
		var pos: Vector2 = overlay.get_global_transform_with_canvas().affine_inverse() * event.position
		if paused:
			if _btn_rect(0, 2).has_point(pos):
				_toggle_pause()
			elif _btn_rect(1, 2).has_point(pos):
				_restart()
		elif world.phase == "over" and over_t > 1.2:
			if _btn_rect(0, 1).has_point(pos):
				_restart()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_toggle_pause()
	elif what == NOTIFICATION_APPLICATION_FOCUS_OUT and touch_on and world != null and world.phase == "play":
		if not paused:
			_toggle_pause()


func _toggle_pause() -> void:
	paused = not paused
	touchc.release_all()
	sfx.play("click")


func _restart() -> void:
	get_tree().reload_current_scene()


func _held() -> Dictionary:
	var h := {
		"l": Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT),
		"r": Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT),
		"j": Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP),
		"k": Input.is_physical_key_pressed(KEY_SPACE) or Input.is_physical_key_pressed(KEY_K),
		"d": Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN),
	}
	if touch_on:
		var th: Dictionary = touchc.held()
		for k in th:
			h[k] = true
		if th.has("d"):
			h["d"] = true
	return h


# ---------------------------------------------------------------- dongu
func _physics_process(dt: float) -> void:
	if paused:
		return
	t += dt
	if world.phase == "over":
		over_t += dt
	var h := _held()
	if press["f"]:
		press["k"] = true
		lob_until = t + 0.25
	if t < lob_until:
		h["d"] = true
	world.apply_input(me, h["l"], h["r"], h["j"], press["k"], press["s"], h["k"], press["o"], h["d"], dt)
	for k in press:
		press[k] = false
	var a := bot.think(world, dt)
	world.apply_input(1, a[0], a[1], a[2], a[3], a[4], null, bot.shoulder, false, dt)
	world.step(dt)
	_process_events(world.take_events())
	shake = maxf(shake, world.take_shake())
	_update_fx(dt)


func _process(_d: float) -> void:
	_layout()
	overlay.queue_redraw()


func _layout() -> void:
	var vp := get_viewport_rect().size
	var strip := 190.0 if touch_on else 0.0
	var s := maxf(vp.x / K.W, vp.y / K.H)
	if not touch_on:
		s = minf(vp.x / K.W, vp.y / K.H)
	var ox := (vp.x - K.W * s) / 2.0
	var oy := (vp.y - K.H * s) / 2.0
	if touch_on:
		# zemin cizgisi kontrol seridinin hemen ustunde dursun
		oy = vp.y - strip - (K.GROUND + 4.0) * s
		oy = clampf(oy, vp.y - K.H * s - strip, 0.0)
	var sh := Vector2.ZERO
	if shake > 0.0:
		var mm := 10.0 * minf(1.0, shake * 2.5) * s
		sh = Vector2(rng.randf_range(-mm, mm), rng.randf_range(-mm, mm))
	field.position = Vector2(ox, oy) + sh
	field.scale = Vector2(s, s)


# ---------------------------------------------------------------- efektler
func _burst(pos: Vector2, n: int, colors: Array, speed: float = 300.0, life: float = 0.6, size: float = 5.0, g: float = 600.0, kind: String = "dot") -> void:
	for i in n:
		var a := rng.randf_range(0, TAU)
		var sp := rng.randf_range(0.3, 1.0) * speed
		parts.append({"p": pos, "v": Vector2(cos(a), sin(a) - 0.3) * sp, "life": life * rng.randf_range(0.6, 1.0),
			"max": life, "col": colors[rng.randi_range(0, colors.size() - 1)], "size": size * rng.randf_range(0.6, 1.2),
			"g": g, "kind": kind, "rot": rng.randf_range(0, TAU), "vr": rng.randf_range(-8, 8)})


func _ring(pos: Vector2, r: float, col: Color, life: float = 0.3) -> void:
	parts.append({"p": pos, "v": Vector2.ZERO, "life": life, "max": life, "col": col, "size": r, "g": 0.0, "kind": "ring", "rot": 0.0, "vr": 0.0})


func _say(txt: String, col: Color, x: float = K.W / 2.0, y: float = 240.0, dur: float = 1.6) -> void:
	floaters.append([txt, x, y, dur, col])


func _process_events(ev: Array) -> void:
	var b := world.ball
	for e in ev:
		var parts_e: PackedStringArray = String(e).split(":")
		var name := parts_e[0]
		match name:
			"kick":
				sfx.play("kick")
				_burst(Vector2(b.x, b.y), 8, [Color.WHITE, Color8(255, 240, 200)], 260.0, 0.3, 4.0, 300.0)
				_ring(Vector2(b.x, b.y), 30.0, Color(1, 1, 1, 0.8), 0.22)
			"kick_hard":
				sfx.play("kick", 3.0, 0.85)
				shake = maxf(shake, 0.15)
			"head":
				sfx.play("head")
				_ring(Vector2(b.x, b.y), 34.0, Color(1, 1, 1, 0.9), 0.25)
			"bounce":
				sfx.play("bounce", -6.0)
			"jump", "jump2":
				sfx.play("jump", -8.0)
			"land":
				sfx.play("land", -6.0)
				for p: SimPlayer in world.players:
					if p.on_ground:
						_burst(Vector2(p.x, K.GROUND), 6, [Color8(210, 200, 170)], 120.0, 0.4, 5.0, 80.0)
			"swing":
				sfx.play("swing", -10.0)
			"post":
				sfx.play("post")
				_say("DİREK!", Color.WHITE, b.x, b.y - 60.0, 1.0)
			"doksan_out":
				sfx.play("ooh")
				_say("DİREKTEN DÖNDÜ!", GOLD, K.W / 2.0, 240.0, 1.6)
			"whistle":
				sfx.play("whistle")
				if world.phase == "play":
					banner = ["BAŞLA!", 0.9, GOLD, ""]
			"pu_spawn":
				sfx.play("pu_spawn")
			"pu":
				sfx.play("pu")
				_say(PU_TEXT.get(parts_e[1], ""), GOLD, b.x, b.y - 50.0, 1.4)
			"freeze":
				sfx.play("freeze")
			"shield":
				sfx.play("shield")
			"armed":
				sfx.play("armed")
			"super_fire", "super_ice":
				sfx.play(name)
				shake = maxf(shake, 0.25)
			"fire_hit":
				sfx.play("fire_hit")
				_burst(Vector2(b.x, b.y), 18, [Color8(255, 140, 40), Color8(255, 220, 90)], 380.0, 0.5, 6.0)
			"block":
				sfx.play("block")
				_say("KURTARIŞ!", Color8(120, 230, 255), b.x, b.y - 60.0, 1.2)
			"pop":
				sfx.play("pop")
			"bump", "trip":
				sfx.play("block", -4.0)
			"magnet", "glove", "bolt", "quake":
				sfx.play("armed")
				var idx := int(parts_e[1])
				var pw: String = world.players[idx].stats["power"]
				_say(K.POWERS[pw][0] + "!", K.POWERS[pw][1], world.players[idx].x, world.players[idx].y - 220.0, 1.4)
				if name == "quake":
					shake = 0.6
			"net":
				ripple = [int(parts_e[1]), float(parts_e[2]), 0.0]
			"goal":
				_on_goal(parts_e)
			"golden":
				sfx.play("golden")
				banner = ["ALTIN GOL!", 1.6, GOLD, "İLK GOLÜ ATAN KAZANIR"]
			"pens":
				banner = ["PENALTILAR!", 1.6, GOLD, ""]
			"end":
				sfx.play("end")
				over_t = 0.0


func _on_goal(pe: PackedStringArray) -> void:
	var who := int(pe[1])
	var kind := pe[2]
	var sp := int(pe[3])
	var own := int(pe[4]) == 1
	sfx.play("goal")
	sfx.play("cheer", -2.0)
	goal_flash = 0.35
	var key := "any"
	if own:
		key = "own"
	elif GOAL_LINES.has(kind):
		key = kind
	elif sp > 1000:
		key = "hard"
	var lines: Array = GOAL_LINES[key]
	var line: String = lines[rng.randi_range(0, lines.size() - 1)]
	banner = ["GOOOL!", 2.2, P_COLORS[who], line]
	var gx := K.GOAL_D if who == 1 else K.W - K.GOAL_D
	for k in 4:
		_burst(Vector2(gx, K.GOAL_TOP + 60.0 * k), 22, [GOLD, Color.WHITE, P_COLORS[who], Color8(255, 120, 90)], 520.0, 1.4, 7.0, 500.0, "conf")


func _update_fx(dt: float) -> void:
	shake = maxf(0.0, shake - dt)
	goal_flash = maxf(0.0, goal_flash - dt)
	if ripple != null:
		ripple[2] += dt
		if ripple[2] > 1.2:
			ripple = null
	for q in parts:
		q["v"].y += q["g"] * dt
		q["p"] += q["v"] * dt
		q["life"] -= dt
		q["rot"] += q["vr"] * dt
		if q["kind"] == "conf":
			q["v"] *= pow(0.2, dt)
	parts = parts.filter(func(q): return q["life"] > 0.0)
	for f in floaters:
		f[2] -= 40.0 * dt
		f[3] -= dt
	floaters = floaters.filter(func(f): return f[3] > 0.0)
	if banner != null:
		banner[1] -= dt
		if banner[1] <= 0.0:
			banner = null
	# hakem topu uzaktan takip eder
	var tx := K.W / 2.0 + 60.0 if world.phase == "ready" else clampf(world.ball.x, 160.0, K.W - 160.0)
	ref_x += (tx - ref_x) * minf(1.0, dt * 1.2)
	# inis/sicrama ezilmesi
	for i in 2:
		var p: SimPlayer = world.players[i]
		var ps: Dictionary = pstate[i]
		ps["sq"] = maxf(0.0, ps["sq"] - dt)
		ps["st"] = maxf(0.0, ps["st"] - dt)
		if ps["air"] and p.on_ground:
			ps["sq"] = 0.16
		elif not ps["air"] and not p.on_ground and p.vy < -200.0:
			ps["st"] = 0.16
		ps["air"] = not p.on_ground


# ---------------------------------------------------------------- ust katman (ekran biriminde)
func _btn_rect(i: int, n: int) -> Rect2:
	var vp := get_viewport_rect().size
	var w := 420.0
	var h := 96.0
	var gap := 40.0
	var total := n * w + (n - 1) * gap
	var x := vp.x / 2.0 - total / 2.0 + i * (w + gap)
	return Rect2(x, vp.y * 0.64, w, h)


func _button(ci: CanvasItem, r: Rect2, label: String, col: Color) -> void:
	R.panel(ci, r.grow(4), Color(0, 0, 0, 0.5), 30)
	R.panel(ci, r, col, 26, Color(1, 1, 1, 0.9), 3)
	ci.draw_rect(Rect2(r.position + Vector2(16, 8), Vector2(r.size.x - 32, 14)), Color(1, 1, 1, 0.18))
	R.text(ci, label, 40, r.get_center(), Color.WHITE, 5)


func _draw_overlay() -> void:
	var ci: CanvasItem = overlay
	var vp := get_viewport_rect().size
	var s := vp.y / 720.0
	var cx := vp.x / 2.0
	# saha -> ekran donusumu (yuzen yazilar icin)
	var fx: Transform2D = field.get_transform()
	if goal_flash > 0.0:
		ci.draw_rect(Rect2(Vector2.ZERO, vp), Color(1, 1, 0.85, 0.35 * goal_flash / 0.35))
	for f in floaters:
		var p: Vector2 = fx * Vector2(f[1], f[2])
		var a := clampf(f[3] * 2.0, 0.0, 1.0)
		var c: Color = f[4]
		c.a = a
		R.text(ci, f[0], int(30 * s / 1.5 * 1.0), p, c, 4, HORIZONTAL_ALIGNMENT_CENTER, true, Color(0.04, 0.05, 0.12, a))
	# geri sayim
	if world.phase == "ready" and t > intro:
		var n := ceili(world.phase_t)
		if n >= 1 and n <= 3:
			var k: float = world.phase_t - floor(world.phase_t)
			R.text(ci, str(n), int(150 * s / 1.5 * (0.8 + 0.4 * k)), Vector2(cx, vp.y * 0.36), Color.WHITE, 10)
	if banner != null:
		var life: float = banner[1]
		var k2 := clampf(life * 3.0, 0.0, 1.0)
		var pop := 1.0 + 0.4 * maxf(0.0, (life - (banner[1])) )
		var big := 120 if banner[0] == "GOOOL!" else 80
		var c2: Color = banner[2]
		c2.a = k2
		R.text(ci, banner[0], int(big * s / 1.5), Vector2(cx, vp.y * 0.3), c2, 10, HORIZONTAL_ALIGNMENT_CENTER, true, Color(0.04, 0.05, 0.12, k2))
		if banner[3] != "":
			var lw := R.text_width(banner[3], int(32 * s / 1.5)) + 60.0
			R.panel(ci, Rect2(cx - lw / 2.0, vp.y * 0.39, lw, 56 * s / 1.5), Color(0.04, 0.05, 0.14, 0.8 * k2), 20, Color(c2.r, c2.g, c2.b, k2), 3)
			R.text(ci, banner[3], int(32 * s / 1.5), Vector2(cx, vp.y * 0.39 + 28 * s / 1.5), Color(1, 1, 1, k2), 4)
	if t < intro:
		_draw_intro(ci, vp)
	if world.phase == "over":
		_draw_over(ci, vp)
	if paused:
		ci.draw_rect(Rect2(Vector2.ZERO, vp), Color(0.02, 0.03, 0.08, 0.72))
		R.text(ci, "DURAKLATILDI", 100, Vector2(cx, vp.y * 0.38), GOLD, 8)
		_button(ci, _btn_rect(0, 2), "DEVAM", Color8(40, 160, 80))
		_button(ci, _btn_rect(1, 2), "YENİDEN BAŞLA", Color8(200, 70, 60))


func _draw_intro(ci: CanvasItem, vp: Vector2) -> void:
	var fade := clampf((intro - t) / 0.35, 0.0, 1.0)
	var bg := R.tex("vs_bg.jpg")
	var s := vp.y / 720.0
	var sc := maxf(vp.x / bg.get_width(), vp.y / bg.get_height())
	var bsz := Vector2(bg.get_width(), bg.get_height()) * sc
	ci.draw_texture_rect(bg, Rect2((vp - bsz) / 2.0, bsz), false, Color(1, 1, 1, fade))
	if fade < 1.0:
		return
	var k := minf(1.0, t / 0.45)
	var ease := 1.0 - pow(1.0 - k, 3.0)
	var tags := ["SEN", "BİLGİSAYAR"] if mode == "bot" else ["SEN", "RAKİP"]
	for side in 2:
		var c: int = world.players[side].char
		var tex := R.pose(c, "idle")
		var hh := 300.0 * s
		var ww := tex.get_width() * hh / tex.get_height()
		var d := -1.0 if side == 0 else 1.0
		var x := vp.x / 2.0 + d * 330.0 * s + d * 520.0 * s * (1.0 - ease)
		var bob := sin(t * 3.0 + side) * 3.0 * s
		R.glow(ci, Vector2(x, 440 * s), 200 * s, Color(0.16, 0.27, 0.55, 0.6) if side == 0 else Color(0.55, 0.16, 0.16, 0.6))
		var rr := Rect2(x - ww / 2.0, 560 * s + bob - hh, ww, hh)
		R.draw_tex(ci, tex, rr, side == 1)
		var plate := Rect2(x - 150 * s, 573 * s, 300 * s, 54 * s)
		R.panel(ci, plate, Color8(14, 18, 40), 20 * s, P_COLORS[side], 3 * s)
		R.text(ci, K.DISPLAY_NAMES[c], int(30 * s), plate.get_center(), Color.WHITE, int(3 * s))
		var cw := (150.0 if tags[side].length() > 4 else 90.0) * s
		var chip := Rect2(x - cw / 2.0, 632 * s, cw, 28 * s)
		R.panel(ci, chip, P_COLORS[side], 12 * s)
		R.text(ci, tags[side], int(16 * s), chip.get_center(), Color.WHITE, 2, HORIZONTAL_ALIGNMENT_CENTER, false)
		var pw: String = world.players[side].stats["power"]
		R.text(ci, K.POWERS[pw][0], int(18 * s), Vector2(x, 684 * s), K.POWERS[pw][1], 3)
	var kv := clampf((t - 0.35) / 0.3, 0.0, 1.0)
	if kv > 0.0:
		var em := R.tex("vs_emblem.png")
		var sc2 := (1.0 + 1.6 * pow(1.0 - kv, 2.0) + 0.04 * sin(t * 6.0)) * 250.0 * s
		var eh := em.get_height() * sc2 / em.get_width()
		R.glow(ci, Vector2(vp.x / 2.0, 330 * s), 160 * s, Color(0.35, 0.27, 0.08, 0.8))
		ci.draw_texture_rect(em, Rect2(vp.x / 2.0 - sc2 / 2.0, 330 * s - eh / 2.0, sc2, eh), false)
	R.text(ci, "RAKİP HAZIR", int(34 * s), Vector2(vp.x / 2.0, 70 * s), Color.WHITE, 5)


func _draw_over(ci: CanvasItem, vp: Vector2) -> void:
	var k := clampf(over_t / 0.5, 0.0, 1.0)
	ci.draw_rect(Rect2(Vector2.ZERO, vp), Color(0.02, 0.03, 0.08, 0.6 * k))
	if k < 1.0:
		return
	var cx := vp.x / 2.0
	var s := vp.y / 720.0
	var res := ""
	var col := GOLD
	if world.winner == 2:
		res = "BERABERE"
		col = Color.WHITE
	elif world.winner == me:
		res = "KAZANDIN!"
	else:
		res = "KAYBETTİN"
		col = Color8(255, 110, 100)
	R.text(ci, res, int(84 * s), Vector2(cx, 150 * s), col, 8)
	R.text(ci, "%d  -  %d" % [world.score[0], world.score[1]], int(64 * s), Vector2(cx, 240 * s), Color.WHITE, 6)
	var st := world.stats
	var rows := [["ŞUT", st["shots"]], ["KAFA", st["heads"]], ["KURTARIŞ", st["saves"]], ["EN HIZLI ŞUT", st["fast"]]]
	var panel := Rect2(cx - 330 * s, 290 * s, 660 * s, 150 * s)
	R.panel(ci, panel, Color(0.06, 0.08, 0.18, 0.92), 18 * s, GOLD, 2)
	for i in rows.size():
		var y := panel.position.y + (24 + i * 34) * s
		R.text(ci, str(rows[i][1][0]), int(24 * s), Vector2(cx - 220 * s, y), P_COLORS[0], 3)
		R.text(ci, rows[i][0], int(22 * s), Vector2(cx, y), Color(0.85, 0.9, 1.0), 3, HORIZONTAL_ALIGNMENT_CENTER, false)
		R.text(ci, str(rows[i][1][1]), int(24 * s), Vector2(cx + 220 * s, y), P_COLORS[1], 3)
	if over_t > 1.2:
		_button(ci, _btn_rect(0, 1), "RÖVANŞ", Color8(40, 160, 80))
