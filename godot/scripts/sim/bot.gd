## Bilgisayar rakip (sim.py Bot ile ayni mantik, kare hizindan bagimsiz).
class_name SimBot
extends RefCounted

var idx: int
var level: int
var react: float
var err: float
var t := 0.0
var offset := 0.0
var jump_hold := 0.0          # saniye (Python'da 14 kare)
var shoulder := false
var guess := false
var react_d := 150.0
var pen_key := ""
var pen_c := [0, 0]
var pen_delay := 1.0
var pen_plan := [-1, false, 0.5]


func _init(i: int, lvl: int = 1) -> void:
	idx = i
	level = lvl
	react = [0.22, 0.12, 0.05][lvl]
	err = [70.0, 35.0, 12.0][lvl]


## Dondurur: [left, right, jump, kick, super]
func think(w: SimWorld, dt: float) -> Array:
	var p: SimPlayer = w.players[idx]
	var b := w.ball
	var rng := w.rng
	if w.phase == "pen_aim":
		var key := "%d:%d" % [w.pen["res"][0].size(), w.pen["res"][1].size()]
		if pen_key != key:
			pen_key = key
			pen_c = [rng.randi_range(-1, 1), rng.randi_range(0, 1)]
			pen_delay = rng.randf_range(0.6, 2.5)
		var col: int = pen_c[0]
		var row: int = pen_c[1]
		var go := (K.PEN_AIM_T - w.phase_t) > pen_delay
		return [col < 0, col > 0, row == 1, go, false]
	if w.phase in ["pen", "pen_ready", "pen_res"] and w.pen != null and w.pen["turn"] != idx:
		if w.last_touch < 0:
			guess = rng.randf() < 0.5
			react_d = rng.randf_range(80.0, 200.0) + 60.0 * (2 - level)
		var dist_b := absf(b.x - p.x)
		var j := w.last_touch >= 0 and guess and dist_b < react_d
		return [false, false, j, false, false]
	t -= dt
	if t <= 0.0:
		t = react
		offset = rng.randf_range(-err, err) * 0.5
	var d := p.dir
	var own_goal_x := 0.0 if idx == 0 else K.W
	var look := 0.18 + 0.1 * level
	var px := clampf(b.x + b.vx * look, 40.0, K.W - 40.0)
	var target := px - d * (38.0 + offset)
	var ball_behind := (b.x - p.x) * d < -10.0
	var danger := absf(b.x - own_goal_x) < 420.0
	if ball_behind and danger:
		target = px - d * 55.0
	var coming := b.vx * d < -250.0 and (b.x - own_goal_x) * d < 640.0
	if coming and not ball_behind:
		target = minf(px, p.x) if d == 1 else maxf(px, p.x)
		target = clampf(target - d * 60.0, K.GOAL_D + 20.0, K.W - K.GOAL_D - 20.0)
	if b.mode != 0 and b.owner != idx:
		target = p.x
	var left := target < p.x - 12.0
	var right := target > p.x + 12.0
	var dx := b.x - p.x
	var dist := Vector2(dx, b.y - (p.y - p.h * 0.6)).length()
	var jump := false
	if absf(dx) < 110.0 and b.y < p.y - p.h * 0.75 and b.vy > -250.0 and b.y > p.y - p.h - 190.0:
		# Python'da kare basina olasilik; 60 Hz'e gore olcekle
		jump = rng.randf() < _per_frame(0.35 + 0.25 * level, dt)
	if b.mode != 0 and b.owner != idx and absf(dx) < 260.0:
		jump = rng.randf() < _per_frame(0.15 * (level + 1), dt)
	var kick := false
	if dist < 95.0 and dx * d > -5.0:
		kick = rng.randf() < _per_frame(0.25 + 0.2 * level, dt)
	if b.mode != 0 and b.owner != idx and absf(dx) < 120.0 and level >= 1:
		kick = rng.randf() < _per_frame(0.3 * level, dt)
	var pw: String = p.stats["power"]
	var sup := false
	if p.meter >= 100.0:
		if pw in ["fire", "ice", "magnet"]:
			sup = dist < 140.0 and dx * d > 0.0
		elif pw == "bolt":
			sup = absf(dx) > 320.0 and (b.x - own_goal_x) * d > 200.0
		elif pw == "glove":
			sup = b.vx * d < -300.0 and absf(b.x - own_goal_x) < 520.0
		elif pw == "quake":
			var o2: SimPlayer = w.players[1 - idx]
			sup = absf(o2.x - b.x) < 120.0 and absf(p.x - b.x) < 260.0
	var o: SimPlayer = w.players[1 - idx]
	if p.shoulder_cd <= 0.0 and absf(o.x - p.x) < 140.0 and absf(b.x - o.x) < 90.0 and p.on_ground:
		shoulder = rng.randf() < _per_frame(0.02 * (level + 1), dt)
	else:
		shoulder = false
	if jump:
		jump_hold = 14.0 / 60.0
	if jump_hold > 0.0:
		jump_hold -= dt
		jump = true
	return [left, right, jump, kick, sup]


## 60 Hz'de kare basina olasiligi dt'lik adima cevirir.
static func _per_frame(p60: float, dt: float) -> float:
	return 1.0 - pow(1.0 - clampf(p60, 0.0, 0.999), dt * 60.0)
