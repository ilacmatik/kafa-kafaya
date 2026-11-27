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


static func length(rig: String, name: String) -> float:
	var m = _m(rig, name)
	return 0.0 if m == null else float(m["frames"].size()) / float(m["fps"])


## t: hareketin baslangicindan gecen sure. hc: zeminden fizik kafa merkezi yuksekligi (dunya birimi).
static func draw(ci: CanvasItem, rig: String, name: String, t: float, feet: Vector2, hc: float, flip: bool,
		mod: Color = Color.WHITE, sq: Vector2 = Vector2.ONE, rot: float = 0.0) -> void:
	var m = _m(rig, name)
	var idle = _m(rig, "idle")
	if m == null or idle == null:
		return
	# olcek: idle'da ayak - kafa merkezi (piksel) = hc (dunya)
	var hf := HEAD_FRAC
	var ih: float = float(idle["foot"][1]) - float(idle["top"])
	var px_hc := ih * (1.0 - hf)
	var k := hc / px_hc * float(m["scale"]) / float(idle["scale"])
	var frames: Array = m["frames"]
	var n := frames.size()
	var fi := int(t * float(m["fps"]))
	fi = posmod(fi, n) if m["loop"] else clampi(fi, 0, n - 1)
	var fr: Array = frames[fi]
	var src := Rect2(fr[0], fr[1], fr[2], fr[3])
	var foot := Vector2(m["foot"][0], m["foot"][1])
	ci.draw_set_transform(feet, rot, Vector2(k * sq.x * (-1.0 if flip else 1.0), k * sq.y))
	ci.draw_texture_rect_region(_tex[rig + "/" + name], Rect2(-foot, src.size), src, mod)
	ci.draw_set_transform(Vector2.ZERO)
