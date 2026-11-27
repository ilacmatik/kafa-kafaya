extends SceneTree
# Rig demo videosu: kosu, ziplama, sut, sevinc
var node: Node2D
var t := 0.0
func _initialize():
	R.init()
	var sc := GDScript.new()
	sc.source_code = """
extends Node2D
var w: SimWorld
var p: SimPlayer
var q := {}
var t := 0.0
var bg: Texture2D
func _ready():
	p = SimPlayer.new(0, 0)
	q = Rig.rest()
	bg = R.tex('stadium_timsah_clean.jpg')
func step(dt: float) -> void:
	t += dt
	var tt := fmod(t, 9.0)
	p.on_ground = true; p.vx = 0.0; p.kick_t = 0.0; p.shoulder_t = 0.0; p.vy = 0.0
	w.phase = 'play'
	var y := 0.0
	if tt < 3.0:
		p.vx = 330.0; p.face = 1; p.x += 330.0 * dt
	elif tt < 4.2:
		var u := (tt - 3.0) / 1.2
		p.on_ground = u >= 1.0; p.vy = -650.0 + 1100.0 * u; y = -sin(u * PI) * 170.0
	elif tt < 6.0:
		var u2 := fmod(tt - 4.2, 0.9)
		if u2 < 0.24: p.kick_t = 0.24 - u2
	elif tt < 7.5:
		w.phase = 'goal'; w.scorer = 0
	else:
		p.vx = -330.0; p.face = -1; p.x -= 330.0 * dt
	p.y = 860.0 + y
	var tgt := Rig.target(p, w, 0, t)
	Rig.blend(q, tgt, dt, p.kick_t > 0.0)
	queue_redraw()
func _draw():
	draw_texture_rect(bg, Rect2(-300, -60, 1880, 1058), false)
	draw_set_transform(Vector2(640, 863), 0, Vector2(1, 0.25))
	draw_circle(Vector2.ZERO, 70, Color(0, 0, 0, 0.35))
	draw_set_transform(Vector2.ZERO)
	var hop := 0.0
	if w.phase == 'goal': hop = absf(sin(t * 9.0)) * 30.0
	Rig.draw(self, 0, q, Vector2(640, p.y - hop), 520.0, p.face < 0)
"""
	sc.reload()
	node = Node2D.new()
	node.set_script(sc)
	node.w = SimWorld.new(0, 3)
	root.add_child(node)
	var k: float = float(OS.get_environment("RIG_K")) if OS.get_environment("RIG_K") != "" else 1.0
	node.scale = Vector2(0.75, 0.75) * k
	node.position = Vector2(0, -130) * k
func _process(d):
	t += d
	node.step(d)
	if t > 9.0:
		quit()
	return false
