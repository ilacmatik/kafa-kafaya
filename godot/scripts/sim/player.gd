## Oyuncu durumu (sim.py Player ile ayni).
class_name SimPlayer
extends RefCounted

var idx: int
var char: int
var stats: Dictionary
var h: float
var h0: float
var head_r: float
var body_r: float
var dir: int

var x := 0.0
var y := 0.0
var vx := 0.0
var vy := 0.0
var face := 1
var on_ground := true
var kick_t := 0.0
var kick_hit := false
var frozen := 0.0
var stun := 0.0
var speed_t := 0.0
var jump_t := 0.0
var armed := 0.0
var run_t := 0.0
var touch_cd := 0.0
var contact := -9.0
var jump_prev := false
var air_jumps := 0
var charging := false
var charge := 0.0
var kick_power := 1.0
var magnet_t := 0.0
var shoulder_t := 0.0
var shoulder_cd := 0.0
var slide_t := 0.0
var sl_dir := 1
var sl_hit := false
var jump_cut := true
var sh_dir := 1
var sh_hit := false
var bike_t := 0.0
var lob := false
var lob_shot := false
var move := 0
var meter := 0.0


func _init(i: int, c: int) -> void:
	idx = i
	char = c
	stats = K.CHARACTERS[c]
	h = K.BASE_H * stats["scale"]
	h0 = h
	head_r = 27.0 * stats["head"] * stats["scale"] * K.SIZE
	body_r = 29.0 * stats["scale"] * K.SIZE
	dir = 1 if i == 0 else -1
	reset()
	meter = 0.0


func reset() -> void:
	x = 330.0 if idx == 0 else K.W - 330.0
	y = K.GROUND
	vx = 0.0
	vy = 0.0
	face = dir
	on_ground = true
	kick_t = 0.0
	kick_hit = false
	frozen = 0.0
	stun = 0.0
	speed_t = 0.0
	jump_t = 0.0
	armed = 0.0
	run_t = 0.0
	touch_cd = 0.0
	contact = -9.0
	jump_prev = false
	air_jumps = 0
	charging = false
	charge = 0.0
	kick_power = 1.0
	magnet_t = 0.0
	shoulder_t = 0.0
	shoulder_cd = 0.0
	slide_t = 0.0
	sl_dir = 1
	sl_hit = false
	jump_cut = true
	sh_dir = 1
	sh_hit = false
	bike_t = 0.0
	lob = false
	lob_shot = false
	move = 0


func jump_cap() -> float:
	# o anki yukseklikten (ikinci ziplama dahil) kafa kirise top capi kadar yaklasabilir, fazlasi degil
	return K.jump_cap_from(y - h)


# carpisma daireleri: Vector3(x, y, r)
func head() -> Vector3:
	return Vector3(x + face * 3.0, y - h + head_r + 4.0 * K.SIZE, head_r)


func body() -> Vector3:
	return Vector3(x, y - h * 0.47, 22.0 * stats["scale"] * K.SIZE)


func legs() -> Vector3:
	return Vector3(x, y - 20.0 * K.SIZE, 17.0 * stats["scale"] * K.SIZE)


func foot() -> Vector3:
	return Vector3(x + face * 38.0 * stats["scale"] * K.SIZE, y - 32.0 * K.SIZE, 44.0 * K.SIZE)


func disabled() -> bool:
	return frozen > 0.0 or stun > 0.0
