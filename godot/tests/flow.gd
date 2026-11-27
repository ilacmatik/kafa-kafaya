extends SceneTree
# Akis testi: yukleme -> menu -> secim (2 adim) -> mac
var el := 0.0
var st := 0
func _initialize():
	change_scene_to_file("res://scenes/boot.tscn")
func cur():
	return current_scene
func shot(n):
	root.get_viewport().get_texture().get_image().save_png("/tmp/flow_%s.png" % n)
func _process(d):
	el += d
	var c = cur()
	var nm: String = c.name if c else ""
	if st == 0 and nm == "Menu" and el > 3.5:
		print("menu ok ", el); c._go("bot"); st = 1
	elif st == 1 and nm == "Select" and el > 4.5:
		c.on_tap("hero4"); c.on_tap("hero4"); st = 2
	elif st == 2 and el > 5.3:
		shot("select2"); c.on_tap("hero2"); c._next(); st = 3
	elif st == 3 and nm == "Match" and el > 9.5:
		print("match ok chars=", c.world.players[0].char, ",", c.world.players[1].char); shot("match"); st = 4
		c._toggle_pause()
	elif st == 4 and el > 10.0:
		shot("pause"); quit()
	if el > 30: print("TIMEOUT st=", st, " scene=", nm); quit()
	return false
