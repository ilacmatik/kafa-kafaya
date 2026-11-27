extends SceneTree
func _init():
	print("A")
	var w := SimWorld.new(0, 3, 10.0, "clear", false, 7)
	print("B ", w.phase)
	w.step(1.0/120.0)
	print("C ", w.phase_t)
	quit()
