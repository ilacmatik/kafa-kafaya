extends SceneTree
# 8 kahraman: --script tests/heroes.gd -- cikis.png poz  (poz: idle/run/jump/kick/celeb/hurt)
var node: Node2D
var el := 0.0
func _initialize():
	R.init()
	var sc := GDScript.new()
	sc.source_code = """
extends Node2D
var w: SimWorld
var pose := 'idle'
func _draw():
	draw_rect(Rect2(0, 0, 1920, 1080), Color8(60, 120, 70))
	for row in 2:
		draw_line(Vector2(0, 470 + row * 520), Vector2(1920, 470 + row * 520), Color.WHITE, 2)
	for n in 8:
		var p := SimPlayer.new(0, 0)
		p.on_ground = true; p.face = 1
		w.phase = 'play'
		match pose:
			'run': p.vx = 330.0; p.x = n * 17.0
			'jump': p.on_ground = false; p.vy = -300.0
			'kick': p.kick_t = 0.12
			'celeb': w.phase = 'goal'; w.scorer = 0
			'hurt': p.stun = 1.0
		var q := Rig.target(p, w, 0, 0.5)
		var x := 240.0 + (n % 4) * 470.0
		var y := 470.0 + (n / 4) * 520.0
		var h := 400.0
		Rig.draw(self, Rig.HEROES[n], q, Vector2(x, y), h, false)
		# fizik: kafa dairesi (ALEV olcusunde, h=152 -> 400 olcek)
		var s := h / K.BASE_H
		var hr := 27.0 * K.SIZE * s
		draw_arc(Vector2(x + 3.0 * s, y - h + hr + 4.0 * K.SIZE * s), hr, 0, TAU, 40, Color(1, 1, 0, 0.8), 2.0)
		draw_arc(Vector2(x, y - h * 0.47), 22.0 * K.SIZE * s, 0, TAU, 40, Color(0, 1, 1, 0.6), 2.0)
		draw_string(ThemeDB.fallback_font, Vector2(x - 80, y + 30), Rig.HEROES[n], HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
"""
	sc.reload()
	node = Node2D.new()
	node.set_script(sc)
	node.w = SimWorld.new(0, 3)
	node.pose = OS.get_cmdline_user_args()[1]
	root.add_child(node)
func _process(d):
	el += d
	if el > 0.4:
		root.get_viewport().get_texture().get_image().save_png(OS.get_cmdline_user_args()[0])
		quit()
	return false
