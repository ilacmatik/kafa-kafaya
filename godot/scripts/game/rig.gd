## Iskelet (parca) animasyonu: Gemini parca sayfasindan ayiklanan parcalar eklem eklem oynatilir.
## Pozlar kodla uretilir (kosu adimi yerdeki hiza gore, sut, ziplama, sevinc...). 120 Hz'de puruzsuz,
## aksesuarlar ilgili kemige baglanir.
class_name Rig
extends RefCounted

## Kahraman sirasi (karakter numarasi -> rig klasoru). Parcalar ve eklemler assets/rig/<ad>/rig.json'dan.
const HEROES := ["flame_knight", "frost_knight", "stone_guardian", "blade_master",
	"storm_shaman", "spirit_shaman", "shadow_ninja", "forest_archer"]
## Gecis: eski futbolcu numaralari -> kahraman (karakter secimi 8'e cikana kadar)
const CHAR_RIG := {0: "flame_knight", 1: "blade_master", 2: "stone_guardian", 3: "frost_knight",
	4: "shadow_ninja", 5: "storm_shaman"}
static var _defs := {}


static func def(rig: String) -> Dictionary:
	if not _defs.has(rig):
		var d = JSON.parse_string(FileAccess.get_file_as_string("res://assets/rig/%s/rig.json" % rig))
		var o := {"pivot": {}, "joint": {}, "extras": d["extras"], "leg_len": float(d["leg_len"]),
			"height": float(d["height"]), "back_rot": float(d.get("back_rot", -0.55)), "back_scale": float(d.get("back_scale", 1.0)),
			"thigh_w": float(d.get("thigh_w", 1.0)), "boot_w": float(d.get("boot_w", 1.0)), "size": {}}
		for k in d["pivot"]:
			o["pivot"][k] = Vector2(d["pivot"][k][0], d["pivot"][k][1])
			o["size"][k] = Vector2(d["size"][k][0], d["size"][k][1])
		for k in d["joint"]:
			o["joint"][k] = Vector2(d["joint"][k][0], d["joint"][k][1])
		_defs[rig] = o
	return _defs[rig]


static var _tex := {}
## Kozmetik: parca -> renk (pelerin vb. yeniden boyanir). Ileride magaza/dolap bunu dolduracak.
static var cosmetics := {}   # char -> {"cape": Color}


## Parcayi hedef renge boya: parlaklik korunur, renk degisir (koyu kumas bile canli renge doner).
static func _recolor(src: Texture2D, col: Color) -> Texture2D:
	var img := src.get_image()
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	# parlakligi 0..1'e yay (koyu pelerin icin)
	var lo := 1.0
	var hi := 0.0
	for y in range(0, img.get_height(), 3):
		for x in range(0, img.get_width(), 3):
			var c := img.get_pixel(x, y)
			if c.a > 0.5:
				var l := c.get_luminance()
				lo = minf(lo, l)
				hi = maxf(hi, l)
	var span := maxf(0.05, hi - lo)
	for y in img.get_height():
		for x in img.get_width():
			var c2 := img.get_pixel(x, y)
			if c2.a <= 0.0:
				continue
			var l2 := clampf((c2.get_luminance() - lo) / span, 0.0, 1.0)
			var o: Color
			if l2 < 0.5:
				o = Color(0.06, 0.05, 0.07).lerp(col, l2 * 2.0)
			else:
				o = col.lerp(col.lightened(0.55), (l2 - 0.5) * 2.0)
			# koyu dis cizgiler koyu kalsin
			if c2.get_luminance() < 0.09:
				o = Color(0.07, 0.06, 0.08)
			o.a = c2.a
			img.set_pixel(x, y, o)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


static func has(char: int) -> bool:
	return CHAR_RIG.has(char)


static func _t(rig: String, part: String) -> Texture2D:
	var key := rig + "/" + part
	if not _tex.has(key):
		_tex[key] = R.tex("rig/%s/%s.png" % [rig, part])
	return _tex[key]


## Ham poz (aci = radyan, saat yonu +; sarkan uzuv icin - = one dogru)
static func rest() -> Dictionary:
	# atletik hazir durus: ayaklar acik, dizler hafif bukuk, kollar govdeden ayri
	return {"torso": 0.05, "head": -0.04, "au_f": 0.22, "al_f": -0.5, "au_b": -0.22, "al_b": -0.45,
		"lu_f": -0.26, "ll_f": 0.16, "lu_b": 0.24, "ll_b": 0.14, "cape": 0.0, "dy": 7.0, "dx": 0.0, "body": 0.0, "plant": 0.0}


## Oyuncunun durumundan hedef pozu uret.
static func target(p: SimPlayer, w: SimWorld, i: int, t: float) -> Dictionary:
	var q := rest()
	var ph := t * 2.4 + i * 1.3
	var celebrate: bool = (w.phase == "goal" and w.scorer == i) or (w.phase == "over" and w.winner == i)
	var running := p.on_ground and absf(p.vx) > 40.0 and p.frozen <= 0.0
	if p.frozen > 0.0:
		return q
	if running:
		# adim fazi yerde alinan yoldan: ayak kaymaz
		var stride := 95.0
		var f := p.x / stride * TAU * float(p.face)
		var s := sin(f)
		var amp := clampf(absf(p.vx) / 300.0, 0.5, 1.0)
		# guclu kosu: one egik govde, yuksek diz, 90 derece bukuk kollarla pompalama
		q["lu_f"] = -0.12 - 0.85 * s * amp
		q["lu_b"] = -0.12 + 0.85 * s * amp
		q["ll_f"] = 0.18 + 1.55 * pow(maxf(0.0, sin(f + 1.7)), 1.6) * amp
		q["ll_b"] = 0.18 + 1.55 * pow(maxf(0.0, sin(f + 1.7 + PI)), 1.6) * amp
		q["au_f"] = 0.85 * s * amp
		q["au_b"] = -0.85 * s * amp
		q["al_f"] = -1.45 - 0.25 * maxf(0.0, -s)
		q["al_b"] = -1.45 - 0.25 * maxf(0.0, s)
		q["torso"] = 0.22 + 0.03 * sin(f * 2.0)
		q["head"] = -0.17
		q["dy"] = 9.0 - absf(cos(f)) * 22.0 * amp
		q["cape"] = -0.45 - 0.1 * sin(f * 2.0)
	else:
		var b := sin(ph)
		q["torso"] += 0.02 * b
		q["au_f"] += 0.04 * b
		q["au_b"] -= 0.04 * b
		q["ll_f"] += 0.05 * b
		q["ll_b"] += 0.05 * b
		q["dy"] += 3.0 * b
		q["cape"] = 0.05 * sin(ph * 0.7)
	if not p.on_ground:
		var up := clampf(-p.vy / 600.0, -1.0, 1.0)   # + yukselis
		q["lu_f"] = -0.95
		q["ll_f"] = 1.25
		q["lu_b"] = -0.25 - 0.2 * up
		q["ll_b"] = 1.0
		q["au_f"] = 0.55 + 0.2 * up
		q["al_f"] = -0.7
		q["au_b"] = -2.4 - 0.3 * up
		q["al_b"] = -0.4
		q["torso"] = -0.05
		q["cape"] = 0.5 * clampf(p.vy / 500.0, -0.6, 1.0)
	if celebrate:
		var pump := sin(t * 9.0)
		q["au_f"] = -3.5 + 0.15 * pump
		q["al_f"] = 0.2
		q["au_b"] = -2.75 - 0.15 * pump
		q["al_b"] = -0.3
		q["head"] = -0.12
		q["torso"] = -0.06
	if p.shoulder_t > 0.0:
		q["torso"] = 0.42
		q["au_f"] = 0.25
		q["al_f"] = -1.9
		q["head"] = -0.25
		q["lu_f"] = -0.5
		q["lu_b"] = 0.55
	if p.kick_t > 0.0:
		var k := clampf(1.0 - p.kick_t / 0.24, 0.0, 1.0)
		var sw := 0.0
		var kn := 0.0
		if k < 0.22:
			var a := k / 0.22
			sw = lerpf(0.0, 0.65, a)
			kn = lerpf(0.2, 1.3, a)
		elif k < 0.55:
			var a2 := (k - 0.22) / 0.33
			a2 = 1.0 - pow(1.0 - a2, 3.0)
			sw = lerpf(0.65, -1.65, a2)
			kn = lerpf(1.3, 0.0, a2)
		else:
			var a3 := (k - 0.55) / 0.45
			sw = lerpf(-1.65, -0.3, a3 * a3)
			kn = lerpf(0.0, 0.2, a3)
		q["lu_f"] = sw
		q["ll_f"] = kn
		q["lu_b"] = 0.12
		q["ll_b"] = 0.1
		q["torso"] = -0.18 * (1.0 if k > 0.22 else 0.0) + 0.06
		q["au_f"] = 0.9
		q["al_f"] = -0.6
		q["au_b"] = -1.3
		q["al_b"] = -0.3
	if p.slide_t > 0.0:
		q["lu_f"] = -1.45
		q["ll_f"] = 0.0
		q["lu_b"] = -0.4
		q["ll_b"] = 1.4
		q["torso"] = -0.35
		q["au_b"] = -1.0
		q["dy"] = 120.0
	if p.bike_t > 0.0:
		var kb := clampf(1.0 - p.bike_t / 0.5, 0.0, 1.0)
		q["body"] = -TAU * 0.42 * sin(kb * PI) * float(1)
		q["lu_f"] = lerpf(-0.3, -2.4, kb)
		q["ll_f"] = 0.1
		q["lu_b"] = -1.2
		q["ll_b"] = 1.0
		q["au_f"] = -1.5
		q["au_b"] = 1.0
	q["plant"] = 0.0
	if p.on_ground and p.slide_t <= 0.0 and p.bike_t <= 0.0:
		q["plant"] = 0.75 if running else 1.0
	q["face"] = 1 if celebrate else 0
	if w.phase == "goal" and w.scorer != i and w.scorer >= 0:
		q["face"] = 2
	if p.stun > 0.0:
		q["face"] = 2
		q["head"] = sin(t * 22.0) * 0.18
		q["torso"] = sin(t * 11.0) * 0.06
	return q


## Mevcut pozu hedefe yumusakca yaklastir (dt'ye bagli, kare hizindan bagimsiz).
static func blend(cur: Dictionary, tgt: Dictionary, dt: float, fast: bool) -> void:
	var k := 1.0 - exp(-dt * (38.0 if fast else 16.0))
	for key in tgt:
		if key == "face":
			cur[key] = tgt[key]
		else:
			cur[key] = lerpf(cur.get(key, tgt[key]), tgt[key], k)


## Cizim: feet = ayak tabaninin dunya konumu, h = dunya biriminde boy, flip = sola bakiyor.
static func draw(ci: CanvasItem, char, q: Dictionary, feet: Vector2, h: float, flip: bool,
		mod: Color = Color.WHITE, sq: Vector2 = Vector2.ONE, rot: float = 0.0) -> void:
	var rig: String = char if char is String else CHAR_RIG[char]
	var d := def(rig)
	var pv: Dictionary = d["pivot"]
	var jn: Dictionary = d["joint"]
	var k: float = h / float(d["height"])
	var base := Transform2D(rot, feet) * Transform2D(0.0, Vector2(k * sq.x * (-1.0 if flip else 1.0), k * sq.y), 0.0, Vector2.ZERO)
	var u: float = float(d["height"]) / 830.0   # poz ofsetleri 830 birimlik boya gore yazildi
	var hy: float = -float(d["leg_len"]) + float(q.get("dy", 0.0)) * u
	if float(q.get("plant", 0.0)) > 0.0 and absf(float(q.get("body", 0.0))) < 0.01:
		# yerdeyken alttaki taban tam zemine otursun (bukuk dizde ayak havada kalmaz / zemine gomulmez)
		var lo := -INF
		for sd in ["f", "b"]:
			var hj: Transform2D = Transform2D(float(q["torso"]) * 0.4, jn.get("skirt", Vector2.ZERO)) * Transform2D(q["lu_" + sd] - q["torso"] * 0.4, jn["hip_" + sd])
			var kj: Transform2D = hj * Transform2D(float(q["ll_" + sd]), jn["knee_" + sd])
			var bp: Vector2 = pv.get("boot_" + sd, Vector2.ZERO)
			var bs2: Vector2 = d["size"].get("boot_" + sd, Vector2.ZERO)
			lo = maxf(lo, (kj * Vector2(0.0, bs2.y * 0.97 - bp.y)).y)
		hy = lerpf(hy, -lo, float(q["plant"]))
	var hip := base * Transform2D(q.get("body", 0.0), Vector2(q.get("dx", 0.0) * u, hy))
	var torso := hip * Transform2D(q["torso"], Vector2.ZERO)
	var skirt := hip * Transform2D(q["torso"] * 0.4, jn.get("skirt", Vector2.ZERO))
	var head := torso * Transform2D(q["head"], jn["head"])
	var sh_f := torso * Transform2D(q["au_f"], jn["shoulder_f"])
	var el_f := sh_f * Transform2D(q["al_f"], jn["elbow_f"])
	var sh_b := torso * Transform2D(q["au_b"], jn["shoulder_b"])
	var el_b := sh_b * Transform2D(q["al_b"], jn["elbow_b"])
	var hp_f := skirt * Transform2D(q["lu_f"] - q["torso"] * 0.4, jn["hip_f"])
	var kn_f := hp_f * Transform2D(q["ll_f"], jn["knee_f"])
	var hp_b := skirt * Transform2D(q["lu_b"] - q["torso"] * 0.4, jn["hip_b"])
	var kn_b := hp_b * Transform2D(q["ll_b"], jn["knee_b"])
	var cape := torso * Transform2D(q["cape"], jn["cape"])
	var bs: float = d["back_scale"]
	var back := torso * Transform2D(float(d["back_rot"]), Vector2(bs, bs), 0.0, jn["back"])
	var dark := Color(mod.r * 0.72, mod.g * 0.7, mod.b * 0.74, mod.a)
	var bones := {"head": head, "torso": torso, "ua_f": sh_f, "fa_f": el_f, "back": back}
	var face: int = int(q.get("face", 0))
	var head_part: String = ["head", "head_happy", "head_hurt"][face]
	if not pv.has(head_part):
		head_part = "head"
	var behind := []
	var front := []
	for ex: Dictionary in d["extras"]:
		var par: Transform2D = bones.get(ex["parent"], torso)
		var pp: String = {"head": head_part, "ua_f": "arm_up_f", "fa_f": "arm_lo_f"}.get(ex["parent"], ex["parent"])
		var psz: Vector2 = d["size"].get(pp, Vector2.ZERO)
		var pvp: Vector2 = pv.get(pp, Vector2.ZERO)
		var at := Vector2(float(ex["at"][0]) * psz.x, float(ex["at"][1]) * psz.y) - pvp
		var r: float = float(ex["rot"]) + (float(q["cape"]) * 0.7 if ex["layer"] == "back" else 0.0)
		var it := [ex["part"], par * Transform2D(r, at), mod]
		if ex["layer"] == "back":
			behind.append(it)
		else:
			front.append(it)
	var order := [["cape", cape, dark]]
	order.append(["back", back, mod])
	order.append_array(behind)
	order.append_array([["arm_up_b", sh_b, dark], ["arm_lo_b", el_b, dark],
		["thigh_b", hp_b, dark], ["boot_b", kn_b, dark],
		["thigh_f", hp_f, mod], ["boot_f", kn_f, mod],
		["torso", torso, mod], ["skirt", skirt, mod],
		[head_part, head, mod],
		["arm_up_f", sh_f, mod], ["arm_lo_f", el_f, mod]])
	order.append_array(front)
	var cos: Dictionary = cosmetics.get(char, {})
	for it: Array in order:
		if not pv.has(it[0]):
			continue
		var tx := _t(rig, it[0])
		if cos.has(it[0]) and tx != null:
			var ck := "%s/%s/%s" % [rig, it[0], (cos[it[0]] as Color).to_html()]
			if not _tex.has(ck):
				_tex[ck] = _recolor(tx, cos[it[0]])
			tx = _tex[ck]
		if tx == null:
			continue
		var m: Transform2D = it[1]
		if it[0].begins_with("thigh"):
			m = m * Transform2D(0.0, Vector2(float(d.get("thigh_w", 1.0)), 1.0), 0.0, Vector2.ZERO)
		elif it[0].begins_with("boot"):
			m = m * Transform2D(0.0, Vector2(float(d.get("boot_w", 1.0)), 1.0), 0.0, Vector2.ZERO)
		ci.draw_set_transform_matrix(m)
		ci.draw_texture(tx, -pv[it[0]], it[2])
	ci.draw_set_transform_matrix(Transform2D.IDENTITY)
