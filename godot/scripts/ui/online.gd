## Ayni Wi-Fi / hotspot uzerinden arkadasla oyun: MAC KUR ya da MACA KATIL.
extends UIScreen

var state := "choose"      # choose | host | join | ip
var ip_text := ""
var err := ""


func _ready() -> void:
	super._ready()
	Net.stop()
	Net.joined.connect(_on_joined)
	Net.left.connect(_on_left)
	focus = "host"


func _exit_tree() -> void:
	if Net.joined.is_connected(_on_joined):
		Net.joined.disconnect(_on_joined)
	if Net.left.is_connected(_on_left):
		Net.left.disconnect(_on_left)


func _on_joined() -> void:
	play("kick")
	Game.mode = "host" if Net.is_host else "client"
	Game.go("res://scenes/select.tscn")


func _on_left(reason: String) -> void:
	err = reason
	if state != "choose":
		state = "join" if not Net.is_host else "choose"
		if state == "join":
			Net.start_scan()


func on_tap(name: String) -> void:
	err = ""
	match name:
		"host":
			if Net.host() == OK:
				state = "host"
				play("click")
			else:
				err = "Maç kurulamadı (port meşgul olabilir)."
		"join":
			state = "join"
			Net.start_scan()
			play("click")
		"ipbtn":
			state = "ip"
			play("click")
		"back":
			on_back()
		"connect":
			if ip_text.count(".") == 3:
				_connect(ip_text)
		_:
			if name.begins_with("g:"):
				_connect(name.substr(2))
			elif name.begins_with("k:"):
				var k := name.substr(2)
				if k == "<":
					ip_text = ip_text.substr(0, maxi(0, ip_text.length() - 1))
				elif ip_text.length() < 15:
					ip_text += k
				play("click")


func _connect(ip: String) -> void:
	if Net.join(ip) == OK:
		state = "connecting"
		play("click")
	else:
		err = "Bağlanılamadı."


func on_back() -> void:
	play("click")
	if state == "choose":
		Net.stop()
		Game.go("res://scenes/menu.tscn")
	elif state == "ip":
		state = "join"
	else:
		Net.stop()
		state = "choose"


func on_key(kc: int) -> void:
	if state == "ip":
		if kc >= KEY_0 and kc <= KEY_9:
			on_tap("k:" + str(kc - KEY_0))
		elif kc >= KEY_KP_0 and kc <= KEY_KP_9:
			on_tap("k:" + str(kc - KEY_KP_0))
		elif kc == KEY_PERIOD or kc == KEY_KP_PERIOD:
			on_tap("k:.")
		elif kc == KEY_BACKSPACE:
			on_tap("k:<")
		elif kc == KEY_ENTER or kc == KEY_KP_ENTER:
			on_tap("connect")


func paint() -> void:
	cover(R.tex("pm_bg.jpg"))
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.01, 0.02, 0.07, 0.55))
	R.text(self, "ARKADAŞINLA OYNA", 52, Vector2(LW / 2.0, 70), GOLD, 6)
	R.text(self, "Aynı Wi-Fi'de ya da birinin telefonunun hotspot'una bağlıyken", 20, Vector2(LW / 2.0, 118),
		Color8(210, 222, 245), 3, HORIZONTAL_ALIGNMENT_CENTER, false)
	flat_button("back", Rect2(view_l + 20, 20, 130, 46), "GERİ", Color8(60, 70, 110), 22)
	match state:
		"choose":
			_choose()
		"host":
			_host()
		"join", "connecting":
			_join()
		"ip":
			_ip()
	if err != "":
		R.text(self, err, 22, Vector2(LW / 2.0, 690), Color8(255, 120, 110), 3)


func _choose() -> void:
	for i in 2:
		var key: String = ["host", "join"][i]
		var r := Rect2(LW / 2.0 - 420 + i * 440, 200, 400, 330)
		reg(key, r)
		var on := focus == key
		var pk := pressed_k(key)
		var rr := r.grow(-6.0 * pk + (4.0 if on else 0.0))
		if on:
			R.glow(self, rr.get_center(), 260, Color(1, 0.8, 0.3, 0.25))
		R.panel(self, rr, Color8(18, 28, 64), 30, GOLD if on else Color(1, 1, 1, 0.5), 3)
		var ic := R.tex("m2_ic_%s.png" % key)
		if ic:
			draw_texture_rect(ic, Rect2(rr.get_center().x - 60, rr.position.y + 50, 120, 120), false)
		R.text(self, "MAÇ KUR" if i == 0 else "MAÇA KATIL", 40, Vector2(rr.get_center().x, rr.position.y + 220), WHITE, 5)
		R.text(self, "Arkadaşın sana bağlansın" if i == 0 else "Kurulan maçı bul ve katıl", 19,
			Vector2(rr.get_center().x, rr.position.y + 270), Color8(200, 212, 240), 3, HORIZONTAL_ALIGNMENT_CENTER, false)


func _host() -> void:
	var r := Rect2(LW / 2.0 - 380, 180, 760, 380)
	R.panel(self, r, Color8(18, 28, 64), 30, GOLD, 3)
	var dots := ".".repeat(int(t * 2.0) % 4)
	R.text(self, "ARKADAŞIN BEKLENİYOR" + dots, 36, Vector2(LW / 2.0, 240), GOLD, 4)
	# donen top
	var c := Vector2(LW / 2.0, 340)
	for i in 8:
		var a := t * 4.0 + i * TAU / 8.0
		draw_circle(c + Vector2(cos(a), sin(a)) * 40.0, 7.0 - i * 0.6, Color(1, 1, 1, 0.9 - i * 0.1))
	var ips := Net.local_ips()
	R.text(self, "Arkadaşın MAÇA KATIL'a bassın, maçın otomatik görünecek.", 20, Vector2(LW / 2.0, 430),
		WHITE, 3, HORIZONTAL_ALIGNMENT_CENTER, false)
	R.text(self, "Görünmezse bu adresi girsin:  " + (", ".join(ips) if ips.size() > 0 else "?"), 22,
		Vector2(LW / 2.0, 480), Color8(150, 220, 255), 3)


func _join() -> void:
	var r := Rect2(LW / 2.0 - 420, 160, 840, 400)
	R.panel(self, r, Color8(18, 28, 64), 30, GOLD, 3)
	if state == "connecting":
		R.text(self, "BAĞLANIYOR" + ".".repeat(int(t * 2.0) % 4), 36, Vector2(LW / 2.0, 360), GOLD, 4)
		return
	R.text(self, "BULUNAN MAÇLAR", 30, Vector2(LW / 2.0, 200), GOLD, 4)
	var keys := Net.found.keys()
	if keys.is_empty():
		var dots := ".".repeat(int(t * 2.0) % 4)
		R.text(self, "Aranıyor" + dots, 26, Vector2(LW / 2.0, 330), WHITE, 3)
		R.text(self, "Arkadaşın MAÇ KUR'a basmış olmalı.", 18, Vector2(LW / 2.0, 372), Color8(190, 205, 235), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
	for i in mini(4, keys.size()):
		var ip: String = keys[i]
		var row := Rect2(r.position.x + 40, 240 + i * 66, r.size.x - 80, 56)
		var nm: String = Net.found[ip]["name"]
		flat_button("g:" + ip, row, "%s   ·   %s" % [nm, ip], Color8(40, 120, 70), 22)
	flat_button("ipbtn", Rect2(LW / 2.0 - 150, 500, 300, 46), "IP İLE BAĞLAN", Color8(50, 80, 160), 20)


func _ip() -> void:
	var r := Rect2(LW / 2.0 - 260, 150, 520, 520)
	R.panel(self, r, Color8(18, 28, 64), 30, GOLD, 3)
	var box := Rect2(r.position.x + 40, r.position.y + 30, r.size.x - 80, 60)
	R.panel(self, box, Color8(8, 12, 30), 16, Color(1, 1, 1, 0.6), 2)
	var cur := "|" if int(t * 2.0) % 2 == 0 else ""
	R.text(self, (ip_text if ip_text != "" else "") + cur, 34, box.get_center(), WHITE, 3)
	var keys := ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "<"]
	for i in keys.size():
		var kr := Rect2(r.position.x + 40 + (i % 3) * 150, r.position.y + 110 + (i / 3) * 74, 140, 64)
		var lab: String = keys[i] if keys[i] != "<" else "SİL"
		flat_button("k:" + keys[i], kr, lab, Color8(40, 60, 120), 30)
	flat_button("connect", Rect2(r.position.x + 40, r.end.y - 92, r.size.x - 80, 60), "BAĞLAN", Color8(40, 160, 80), 28)
