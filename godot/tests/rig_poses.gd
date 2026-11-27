extends SceneTree
# Rig pozlarini yan yana cizer: --script tests/rig_poses.gd -- cikis.png
var node: Node2D
var el := 0.0
func _initialize():
	R.init()
	var sc := GDScript.new()
	sc.source_code = """
extends Node2D
var w: SimWorld
func _draw():
	draw_rect(Rect2(0, 0, 1920, 1080), Color8(40, 110, 50))
	draw_line(Vector2(0, 470), Vector2(1920, 470), Color.WHITE, 2)
	draw_line(Vector2(0, 1000), Vector2(1920, 1000), Color.WHITE, 2)
	var cases := [['idle',0],['run',0],['run',24],['run',48],['run',72],['jump',0],['kick',0.19],['kick',0.13],['kick',0.08],['celeb',0],['shoulder',0],['idle_l',0]]
	for n in cases.size():
		var p := SimPlayer.new(0, 0)
		p.on_ground = true; p.vx = 0.0; p.face = 1
		var c: String = cases[n][0]
		var v: float = cases[n][1]
		if c == 'run': p.vx = 330.0; p.x = v
		if c == 'jump': p.on_ground = false; p.vy = -300.0
		if c == 'kick': p.kick_t = v
		if c == 'shoulder': p.shoulder_t = 0.2
		if c == 'idle_l': p.face = -1
		if c == 'celeb': w.phase = 'goal'; w.scorer = 0
		else: w.phase = 'play'
		var q := Rig.target(p, w, 0, 0.5)
		var col := n % 6
		var row := n / 6
		Rig.draw(self, 0, q, Vector2(160 + col * 320, 470 + row * 530), 380.0, p.face < 0)
		draw_string(ThemeDB.fallback_font, Vector2(100 + col * 320, 500 + row * 530), c + ' ' + str(v), HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
"""
	sc.reload()
	node = Node2D.new()
	node.set_script(sc)
	node.w = SimWorld.new(0, 3)
	root.add_child(node)
func _process(d):
	el += d
	if el > 0.5:
		root.get_viewport().get_texture().get_image().save_png(OS.get_cmdline_user_args()[0])
		quit()
	return false
