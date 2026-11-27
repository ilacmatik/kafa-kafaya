## Ayarlar: ses, titresim, kare hizi; kontroller yardimi ve oyuncu istatistikleri.
extends UIScreen

var help_open := false


func _ready() -> void:
	super._ready()
	focus = "sfx"


func on_tap(name: String) -> void:
	if help_open:
		help_open = false
		return
	match name:
		"sfx", "crowd", "vib":
			Game.opt[name] = not Game.opt[name]
		"fps":
			Game.opt["fps"] = 60 if int(Game.opt["fps"]) == 0 else 0
		"help":
			help_open = true
		"back":
			on_back()
			return
	Game.apply_opts()
	Game.save_settings()
	play("click")


func on_back() -> void:
	if help_open:
		help_open = false
		return
	play("click")
	Game.go("res://scenes/menu.tscn")


func paint() -> void:
	cover(R.tex("pm_bg.jpg"))
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.01, 0.02, 0.07, 0.55))
	R.text(self, "AYARLAR", 56, Vector2(LW / 2.0, 70), GOLD, 6)
	flat_button("back", Rect2(view_l + 20, 20, 130, 46), "GERİ", Color8(60, 70, 110), 22)
	var rows := [
		["sfx", "SES EFEKTLERİ", "AÇIK" if Game.opt["sfx"] else "KAPALI", Game.opt["sfx"]],
		["crowd", "TARAFTAR SESİ", "AÇIK" if Game.opt["crowd"] else "KAPALI", Game.opt["crowd"]],
		["vib", "TİTREŞİM", "AÇIK" if Game.opt["vib"] else "KAPALI", Game.opt["vib"]],
		["fps", "KARE HIZI", "EN YÜKSEK (120 Hz'e kadar)" if int(Game.opt["fps"]) == 0 else "60 FPS (pil tasarrufu)", int(Game.opt["fps"]) == 0],
	]
	var panel := Rect2(140, 130, 620, 420)
	R.panel(self, panel, Color(0.05, 0.08, 0.2, 0.88), 28, Color(1, 1, 1, 0.4), 2)
	for i in rows.size():
		var row: Array = rows[i]
		var y := panel.position.y + 40 + i * 92
		R.text(self, row[1], 26, Vector2(panel.position.x + 36, y + 26), WHITE, 3, HORIZONTAL_ALIGNMENT_LEFT)
		var tr := Rect2(panel.end.x - 36 - 250, y, 250, 52)
		reg(row[0], tr)
		var on: bool = row[3]
		R.panel(self, tr.grow(-3.0 * pressed_k(row[0])), Color8(40, 150, 70) if on else Color8(90, 50, 60), 22, GOLD if focus == row[0] else Color(1, 1, 1, 0.7), 2)
		R.text(self, row[2], 18 if row[0] == "fps" else 22, tr.get_center(), WHITE, 3, HORIZONTAL_ALIGNMENT_CENTER, row[0] != "fps")
	flat_button("help", Rect2(panel.position.x, panel.end.y + 24, panel.size.x, 58), "KONTROLLER VE TUŞ DÜZENİ", Color8(50, 80, 160), 24)
	# istatistikler
	var p := Game.profile
	var li := Game.level_info()
	var sp := Rect2(800, 130, 340, 502)
	R.panel(self, sp, Color(0.05, 0.08, 0.2, 0.88), 28, GOLD, 2)
	R.text(self, "KARİYERİN", 30, Vector2(sp.get_center().x, sp.position.y + 40), GOLD, 4)
	var st := [["SEVİYE", str(li[0])], ["MAÇ", str(p["matches"])], ["GALİBİYET", str(p["wins"])],
		["BERABERLİK", str(p["draws"])], ["MAĞLUBİYET", str(p["losses"])], ["GOL", str(p["goals"])],
		["KUPA", str(p["cups"])], ["ALTIN", str(p["coins"])]]
	for i in st.size():
		var y2 := sp.position.y + 96 + i * 50
		R.text(self, st[i][0], 20, Vector2(sp.position.x + 30, y2), Color8(200, 212, 240), 2, HORIZONTAL_ALIGNMENT_LEFT, false)
		R.text(self, st[i][1], 24, Vector2(sp.end.x - 30, y2), WHITE, 3, HORIZONTAL_ALIGNMENT_RIGHT)
	if help_open:
		_help()


func _help() -> void:
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.01, 0.02, 0.07, 0.85))
	reg("close", Rect2(view_l, 0, view_r - view_l, LH))
	var r := Rect2(LW / 2.0 - 430, 60, 860, 600)
	R.panel(self, r, Color8(16, 24, 56), 30, GOLD, 3)
	R.text(self, "KONTROLLER", 44, Vector2(LW / 2.0, 110), GOLD, 5)
	var rows := [
		["Hareket", "Sol joystick  ·  A / D  ·  ← / →"],
		["Zıpla", "Yeşil tuş  ·  W / ↑"],
		["Şut", "Kırmızı tuş  ·  BOŞLUK / K (basılı tut: güçlü şut)"],
		["Aşırtma", "Turuncu tuş  ·  Q / F"],
		["Süper güç", "Dolunca sarı tuş  ·  R  ·  ↓↓"],
		["Omuz", "Mor tuş  ·  E / CTRL"],
		["Rövaşata", "Havada topun altına girip şut"],
		["Tuş düzeni", "Maçta duraklat → TUŞ DÜZENİ: tuşları taşı, büyüt"],
	]
	var y := 175.0
	for row: Array in rows:
		R.text(self, row[0], 24, Vector2(r.position.x + 50, y), GOLD, 3, HORIZONTAL_ALIGNMENT_LEFT)
		R.text(self, row[1], 20, Vector2(r.position.x + 240, y), WHITE, 3, HORIZONTAL_ALIGNMENT_LEFT, false)
		y += 54.0
	R.text(self, "Kapatmak için dokun", 18, Vector2(LW / 2.0, r.end.y - 26), Color8(180, 195, 225), 2, HORIZONTAL_ALIGNMENT_CENTER, false)
