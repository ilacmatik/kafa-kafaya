extends SceneTree
var node: Node2D
var el := 0.0
func _initialize():
	R.init()
	var sc := GDScript.new()
	sc.source_code = """
extends Node2D
var w: SimWorld
func _draw():
	draw_texture_rect(R.tex('sel_bg.jpg'), Rect2(0, 0, 1920, 1080), false)
	var cols := [null, Color8(40, 90, 220), Color8(30, 150, 80), Color8(230, 180, 40), Color8(150, 40, 200)]
	var names := ['VARSAYILAN', 'KRALİYET MAVİSİ', 'ZÜMRÜT', 'ALTIN', 'GECE MORU']
	for n in cols.size():
		var p := SimPlayer.new(0, 0)
		p.on_ground = false; p.vy = 200.0
		w.phase = 'play'
		if cols[n] != null:
			Rig.cosmetics[0] = {'cape': cols[n]}
		else:
			Rig.cosmetics.erase(0)
		var q := Rig.target(p, w, 0, 0.3)
		q['cape'] = -0.45
		Rig.draw(self, 0, q, Vector2(220 + n * 370, 860), 560.0, true)
		R.text(self, names[n], 30, Vector2(220 + n * 370, 920), Color.WHITE, 4)
"""
	sc.reload()
	node = Node2D.new()
	node.set_script(sc)
	node.w = SimWorld.new(0, 3)
	root.add_child(node)
func _process(d):
	el += d
	if el > 0.5:
		root.get_viewport().get_texture().get_image().save_png("/tmp/rig/capes.png")
		quit()
	return false
