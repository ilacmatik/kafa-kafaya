## Videodan cikarilmis kare animasyonlari (assets/anim/<kahraman>/<hareket>/atlas.png + anim.json).
## Olcek kahramanin "idle" animasyonundan: gorsel kafa merkezi fizik kafa merkezine oturur.
class_name Anim
extends RefCounted

const HEAD_FRAC := 0.27   # idle karesinde kafa merkezi: tepeden boyun bu orani (kahraman basina hero.json ile degisir)

static var _meta := {}
static var _tex := {}


static func has(rig: String, name: String) -> bool:
	return _m(rig, name) != null


static func _m(rig: String, name: String):
	var key := rig + "/" + name
	if not _meta.has(key):
		var path := "res://assets/anim/%s/%s/anim.json" % [rig, name]
		var m = null
		if FileAccess.file_exists(path):
			m = JSON.parse_string(FileAccess.get_file_as_string(path))
			_tex[key] = load("res://assets/anim/%s/%s/atlas.png" % [rig, name])
		_meta[key] = m
	return _meta[key]


static func fps(rig: String, name: String) -> float:
	var m = _m(rig, name)
	return 24.0 if m == null else float(m["fps"])


## Kosu videosunda iki ayagin da yerden kesik oldugu kare (yoksa -1)
static func air_frame(rig: String) -> int:
	var m = _m(rig, "run")
	return -1 if m == null or not m.has("air_frame") else int(m["air_frame"])


static func length(rig: String, name: String) -> float:
	var m = _m(rig, name)
	return 0.0 if m == null else float(m["frames"].size()) / float(m["fps"])


## Dunya biriminde olcek (kare pikseli -> dunya)
static func world_k(rig: String, name: String, hc: float) -> float:
	var m = _m(rig, name)
	var idle = _m(rig, "idle")
	if m == null or idle == null:
		return 1.0
	return hc / _idle_hc_px(idle) * float(m["scale"]) / float(idle["scale"])


## idle karesinde ayak tabani ile yuz merkezi arasi (piksel): gorsel kafa = fizik kafa
static func _idle_hc_px(idle) -> float:
	if idle.has("face"):
		return float(idle["foot"][1]) - float(idle["face"][1])
	var ih: float = float(idle["foot"][1]) - float(idle["top"])
	return ih * (1.0 - HEAD_FRAC)


## Poz animasyonu (Gemini poz resmi): a ve b pozlari arasinda wb agirlikla gecis.
## head_anchor: havadaki pozlar yuz merkezinden fizik kafasina hizalanir; degilse ayak tabanindan.
static func draw_pose(ci: CanvasItem, rig: String, name: String, a: int, b: int, wb: float, feet: Vector2, hc: float,
		flip: bool, head_anchor: bool, mod: Color = Color.WHITE, sq: Vector2 = Vector2.ONE, rot: float = 0.0) -> void:
	var m = _m(rig, name)
	var idle = _m(rig, "idle")
	if m == null or idle == null:
		return
	var k := world_k(rig, name, hc)
	var tex: Texture2D = _tex[rig + "/" + name]
	var dir := -1.0 if flip else 1.0
	# idle'da yuz ayagin ne kadar onunde: havada da ayni yatay iliski korunsun
	var fdx := 0.0
	if idle.has("face"):
		fdx = (float(idle["face"][0]) - float(idle["foot"][0])) * world_k(rig, "idle", hc)
	for pass_i in 2:
		var idx := a if pass_i == 0 else b
		var al := 1.0 if pass_i == 0 else wb
		if pass_i == 1 and (b == a or wb < 0.02):
			break
		var fr: Array = m["frames"][idx]
		var src := Rect2(fr[0], fr[1], fr[2], fr[3])
		var anchor: Vector2
		var at: Vector2
		if head_anchor:
			anchor = Vector2(m["heads"][idx][0], m["heads"][idx][1])
			at = feet + Vector2(fdx * dir, -hc)
		else:
			anchor = Vector2(m["feet"][idx][0], m["feet"][idx][1])
			at = feet
		ci.draw_set_transform(at, rot, Vector2(k * sq.x * dir, k * sq.y))
		ci.draw_texture_rect_region(tex, Rect2(-anchor, src.size), src, Color(mod.r, mod.g, mod.b, mod.a * al))
	ci.draw_set_transform(Vector2.ZERO)


static func is_poses(rig: String, name: String) -> bool:
	var m = _m(rig, name)
	return m != null and m.get("poses", false)


## Kosu: 1x hizda ayagin zemindeki hizi (dunya birimi/sn). Oynatma hizi = oyuncu hizi / bu -> ayak kaymaz.
static func ground_speed(rig: String, name: String, hc: float) -> float:
	var m = _m(rig, name)
	if m == null or not m.has("ground_v"):
		return 0.0
	return float(m["ground_v"]) * world_k(rig, name, hc)


## t: hareketin baslangicindan gecen sure. hc: zeminden fizik kafa merkezi yuksekligi (dunya birimi).
static func draw(ci: CanvasItem, rig: String, name: String, t: float, feet: Vector2, hc: float, flip: bool,
		mod: Color = Color.WHITE, sq: Vector2 = Vector2.ONE, rot: float = 0.0) -> void:
	var m = _m(rig, name)
	var idle = _m(rig, "idle")
	if m == null or idle == null:
		return
	# olcek: idle'da ayak - kafa merkezi (piksel) = hc (dunya)
	var k := world_k(rig, name, hc)
	var frames: Array = m["frames"]
	var n := frames.size()
	var ft: float = t * float(m["fps"])
	var fi := int(floor(ft))
	var frac: float = ft - floor(ft)
	var fj := fi + 1
	if m["loop"]:
		fi = posmod(fi, n)
		fj = posmod(fj, n)
	else:
		fi = clampi(fi, 0, n - 1)
		fj = clampi(fj, 0, n - 1)
	var tex: Texture2D = _tex[rig + "/" + name]
	var foot := Vector2(m["foot"][0], m["foot"][1])
	ci.draw_set_transform(feet, rot, Vector2(k * sq.x * (-1.0 if flip else 1.0), k * sq.y))
	var fr: Array = frames[fi]
	var src := Rect2(fr[0], fr[1], fr[2], fr[3])
	ci.draw_texture_rect_region(tex, Rect2(-foot, src.size), src, mod)
	# iki kare arasi yumusak gecis: 120 Hz ekranda bile kare atlama hissi olmaz
	if fj != fi and frac > 0.02:
		var fr2: Array = frames[fj]
		var src2 := Rect2(fr2[0], fr2[1], fr2[2], fr2[3])
		ci.draw_texture_rect_region(tex, Rect2(-foot, src2.size), src2, Color(mod.r, mod.g, mod.b, mod.a * frac))
	ci.draw_set_transform(Vector2.ZERO)
