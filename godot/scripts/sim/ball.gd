## Top durumu (sim.py Ball ile ayni).
class_name SimBall
extends RefCounted

var x := 0.0
var y := 0.0
var vx := 0.0
var vy := 0.0
var ang := 0.0
var spin := 0.0        # + ust falso, - ters falso
var ignore_t := 0.0
var ignore_p := -1
var squeeze_cd := 0.0
var curve := 0.0
var cdir := 1
var post_cd := 0.0
var px := 0.0
var mode := 0          # 0 normal, 1 ates, 2 buz
var mode_t := 0.0
var owner := -1
var hit_cd := [0.0, 0.0]


func reset(rng: RandomNumberGenerator, nx: float = K.W / 2.0, ny: float = 250.0) -> void:
	x = nx
	y = ny
	vx = (1.0 if rng.randf() < 0.5 else -1.0) * rng.randf_range(20.0, 60.0)
	vy = 0.0
	ang = 0.0
	spin = 0.0
	ignore_t = 0.0
	ignore_p = -1
	squeeze_cd = 0.0
	curve = 0.0
	cdir = 1
	post_cd = 0.0
	px = nx
	mode = 0
	mode_t = 0.0
	owner = -1
	hit_cd = [0.0, 0.0]
