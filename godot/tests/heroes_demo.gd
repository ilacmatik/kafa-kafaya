extends SceneTree
# 8 kahraman demo videosu: kosu, ziplama, sut, kafa, sevinc, sersemleme
var node: Node2D
var t := 0.0
func _initialize():
	R.init()
	var sc := GDScript.new()
	sc.source_code = """
extends Node2D
var w: SimWorld
var ps := []
var qs := []
var t := 0.0
var bg: Texture2D
func _ready():
	for n in 8:
		ps.append(SimPlayer.new(0, 0))
		qs.append(Rig.rest())
	bg = R.tex('stadium_timsah_clean.jpg')
func step(dt: float) -> void:
	t += dt
	var tt := fmod(t, 11.0)
	w.phase = 'play'
	if tt >= 7.0 and tt < 8.6:
		w.phase = 'goal'; w.scorer = 0
	for n in 8:
		var p: SimPlayer = ps[n]
		p.on_ground = true; p.vx = 0.0; p.kick_t = 0.0; p.vy = 0.0; p.stun = 0.0; p.face = 1
		var y := 0.0
		if tt < 2.5:
			p.vx = 330.0; p.x += 330.0 * dt
		elif tt < 3.7:
			var u := (tt - 2.5) / 1.2
			p.on_ground = u >= 1.0; p.vy = -650.0 + 1100.0 * u; y = -sin(u * PI) * 110.0
		elif tt < 5.5:
			var u2 := fmod(tt - 3.7, 0.9)
			if u2 < 0.24: p.kick_t = 0.24 - u2
		elif tt < 7.0:
			var u3 := (tt - 5.5) / 0.75
			var f := fmod(u3, 1.0)
			p.on_ground = false; p.vy = -500.0 + 1000.0 * f; y = -sin(f * PI) * 90.0
			if f > 0.3 and f < 0.6: p.kick_t = 0.1
		elif tt < 8.6:
			pass
		elif tt < 9.6:
			p.stun = 1.0
		else:
			p.vx = -330.0; p.face = -1; p.x -= 330.0 * dt
		p.y = y
		var tgt := Rig.target(p, w, 0, t + n * 0.13)
		Rig.blend(qs[n], tgt, dt, p.kick_t > 0.0)
	queue_redraw()
func _draw():
	draw_texture_rect(bg, Rect2(0, 0, 1280, 720), false)
	draw_rect(Rect2(0, 0, 1280, 720), Color(0, 0, 0, 0.25))
	for n in 8:
		var p: SimPlayer = ps[n]
		var x := 160.0 + (n % 4) * 320.0
		var gy := 330.0 + (n / 4) * 340.0
		draw_set_transform(Vector2(x, gy + 2), 0, Vector2(1, 0.25))
		draw_circle(Vector2.ZERO, 55 * (1.0 + p.y / 300.0), Color(0, 0, 0, 0.35))
		draw_set_transform(Vector2.ZERO)
		var hop := 0.0
		if w.phase == 'goal': hop = absf(sin(t * 9.0 + n)) * 22.0
		Rig.draw(self, Rig.HEROES[n], qs[n], Vector2(x, gy + p.y - hop), 260.0, p.face < 0)
"""
	sc.reload()
	node = Node2D.new()
	node.set_script(sc)
	node.w = SimWorld.new(0, 3)
	root.add_child(node)
	node.scale = Vector2(1.5, 1.5)
func _process(d):
	t += d
	node.step(d)
	if t > 11.0:
		quit()
	return false
