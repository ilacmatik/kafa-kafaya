## Iskelet (parca) animasyonu: Gemini parca sayfasindan ayiklanan parcalar eklem eklem oynatilir.
## Pozlar kodla uretilir (kosu adimi yerdeki hiza gore, sut, ziplama, sevinc...). 120 Hz'de puruzsuz,
## aksesuarlar ilgili kemige baglanir.
class_name Rig
extends RefCounted

## Karakter -> rig adi (simdilik deneme: ALEV yerine Alev Sovalyesi)
const CHAR_RIG := {0: "flame_knight"}

## Parca: dokudaki eklem noktasi (piksel). Eklem: ebeveyn parcanin eklem noktasina gore konum.
const DEFS := {
	"flame_knight": {
		"pivot": {
			"torso": Vector2(117, 226), "head": Vector2(118, 296), "skirt": Vector2(107, 10),
			"arm_up_f": Vector2(70, 32), "arm_lo_f": Vector2(78, 22),
			"arm_up_b": Vector2(50, 30), "arm_lo_b": Vector2(22, 50),
			"thigh_f": Vector2(40, 20), "boot_f": Vector2(70, 16),
			"thigh_b": Vector2(54, 20), "boot_b": Vector2(73, 16),
			"cape": Vector2(174, 14), "sword": Vector2(52, 170),
		},
		"joint": {
			"torso": Vector2(0, 6), "skirt": Vector2(-2, -6), "head": Vector2(-19, -198),
			"shoulder_f": Vector2(-94, -172), "shoulder_b": Vector2(60, -172),
			"elbow_f": Vector2(-28, 104), "elbow_b": Vector2(22, 106),
			"hip_f": Vector2(-44, 34), "hip_b": Vector2(42, 34),
			"knee_f": Vector2(-6, 116), "knee_b": Vector2(12, 116),
			"cape": Vector2(-34, -196), "sword": Vector2(-30, -110),
		},
		"leg_len": 318.0,       # kalca -> taban (duz bacak)
		"height": 830.0,        # taban -> sac ucu
		"sword_rot": -0.55,
		"head_scale": 1.12,
	},
}

static var _tex := {}


static func has(char: int) -> bool:
	return CHAR_RIG.has(char)


static func _t(rig: String, part: String) -> Texture2D:
	var key := rig + "/" + part
	if not _tex.has(key):
		_tex[key] = R.tex("rig/%s/%s.png" % [rig, part])
	return _tex[key]


## Ham poz (aci = radyan, saat yonu +; sarkan uzuv icin - = one dogru)
static func rest() -> Dictionary:
	return {"torso": 0.0, "head": 0.0, "au_f": 0.12, "al_f": -0.2, "au_b": -0.1, "al_b": -0.25,
		"lu_f": -0.06, "ll_f": 0.05, "lu_b": 0.08, "ll_b": 0.05, "cape": 0.0, "dy": 0.0, "dx": 0.0, "body": 0.0}


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
		q["lu_f"] = -0.75 * s * amp
		q["lu_b"] = 0.75 * s * amp
		q["ll_f"] = 0.15 + 1.1 * pow(maxf(0.0, sin(f + 1.9)), 2.0) * amp
		q["ll_b"] = 0.15 + 1.1 * pow(maxf(0.0, sin(f + 1.9 + PI)), 2.0) * amp
		q["au_f"] = 0.65 * s * amp
		q["au_b"] = -0.65 * s * amp
		q["al_f"] = -1.0
		q["al_b"] = -1.0
		q["torso"] = 0.13
		q["head"] = -0.08
		q["dy"] = -absf(cos(f)) * 16.0 * amp
		q["cape"] = -0.35 - 0.08 * sin(f * 2.0)
	else:
		var b := sin(ph)
		q["torso"] = -0.015 * b
		q["au_f"] += 0.04 * b
		q["au_b"] -= 0.04 * b
		q["dy"] = 3.0 * b
		q["cape"] = 0.05 * sin(ph * 0.7)
	if not p.on_ground:
		var up := clampf(-p.vy / 600.0, -1.0, 1.0)   # + yukselis
		q["lu_f"] = -0.95
		q["ll_f"] = 1.25
		q["lu_b"] = -0.25 - 0.2 * up
		q["ll_b"] = 1.0
		q["au_f"] = -1.0 - 0.3 * up
		q["al_f"] = -0.15
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
	if p.stun > 0.0:
		q["head"] = sin(t * 22.0) * 0.18
		q["torso"] = sin(t * 11.0) * 0.06
	return q


## Mevcut pozu hedefe yumusakca yaklastir (dt'ye bagli, kare hizindan bagimsiz).
static func blend(cur: Dictionary, tgt: Dictionary, dt: float, fast: bool) -> void:
	var k := 1.0 - exp(-dt * (38.0 if fast else 16.0))
	for key in tgt:
		cur[key] = lerpf(cur.get(key, tgt[key]), tgt[key], k)


## Cizim: feet = ayak tabaninin dunya konumu, h = dunya biriminde boy, flip = sola bakiyor.
static func draw(ci: CanvasItem, char: int, q: Dictionary, feet: Vector2, h: float, flip: bool,
		mod: Color = Color.WHITE, sq: Vector2 = Vector2.ONE, rot: float = 0.0) -> void:
	var rig: String = CHAR_RIG[char]
	var d: Dictionary = DEFS[rig]
	var pv: Dictionary = d["pivot"]
	var jn: Dictionary = d["joint"]
	var k: float = h / float(d["height"])
	var base := Transform2D(rot, feet) * Transform2D(0.0, Vector2(k * sq.x * (-1.0 if flip else 1.0), k * sq.y), 0.0, Vector2.ZERO)
	# kalca (kok) noktasi
	var hip := base * Transform2D(q.get("body", 0.0), Vector2(q.get("dx", 0.0), -float(d["leg_len"]) + q.get("dy", 0.0)))
	var torso := hip * Transform2D(q["torso"], jn["torso"])
	var skirt := hip * Transform2D(q["torso"] * 0.4, jn["skirt"])
	var hs: float = d.get("head_scale", 1.0)
	var head := torso * Transform2D(q["head"], Vector2(hs, hs), 0.0, jn["head"])
	var sh_f := torso * Transform2D(q["au_f"], jn["shoulder_f"])
	var el_f := sh_f * Transform2D(q["al_f"], jn["elbow_f"])
	var sh_b := torso * Transform2D(q["au_b"], jn["shoulder_b"])
	var el_b := sh_b * Transform2D(q["al_b"], jn["elbow_b"])
	var hp_f := skirt * Transform2D(q["lu_f"] - q["torso"] * 0.4, jn["hip_f"])
	var kn_f := hp_f * Transform2D(q["ll_f"], jn["knee_f"])
	var hp_b := skirt * Transform2D(q["lu_b"] - q["torso"] * 0.4, jn["hip_b"])
	var kn_b := hp_b * Transform2D(q["ll_b"], jn["knee_b"])
	var cape := torso * Transform2D(q["cape"], jn["cape"])
	var sword := torso * Transform2D(float(d["sword_rot"]), jn["sword"])
	var back := Color(mod.r * 0.78, mod.g * 0.74, mod.b * 0.74, mod.a)
	var order := [
		["cape", cape, back], ["sword", sword, mod],
		["arm_up_b", sh_b, back], ["arm_lo_b", el_b, back],
		["thigh_b", hp_b, back], ["boot_b", kn_b, back],
		["thigh_f", hp_f, mod], ["boot_f", kn_f, mod],
		["torso", torso, mod], ["skirt", skirt, mod],
		["head", head, mod],
		["arm_up_f", sh_f, mod], ["arm_lo_f", el_f, mod],
	]
	for it: Array in order:
		var tx := _t(rig, it[0])
		if tx == null:
			continue
		ci.draw_set_transform_matrix(it[1])
		ci.draw_texture(tx, -pv[it[0]], it[2])
	ci.draw_set_transform_matrix(Transform2D.IDENTITY)
