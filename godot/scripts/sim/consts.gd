## Kafa Kafaya - simulasyon sabitleri (Python sim.py ile birebir).
## Dunya birimi: 1280x720 mantiksal saha. Cizim 1.5 ile 1920x1080'e olceklenir.
class_name K
extends RefCounted

const W := 1280.0
const H := 720.0
const GROUND := 652.0
const GOAL_D := 102.0          # kale cizgisi (on direk ic yuzu) x konumu
const GOAL_H := 320.0          # kale agzi yuksekligi (oyuncu ~150: ziplayan kafanin ustunden top gecer)
const ROOF_T := 30.0           # ust direk kalinligi (inceltilmis ahsap kiris)
const POST_X := 23.0           # on direk dis yuzu: kale cizgisinden sahaya dogru
const GOAL_TOP := GROUND - GOAL_H

const BALL_R := 20.0
const BALL_G := 1250.0
const PLAYER_G := 1750.0
const BALL_MAX := 1700.0
const BALL_TS := 0.85          # topun zaman olcegi (1'den kucuk = daha yavas)

const SUPER_SPEED := 1150.0
const SUPER_TIME := 1.0
const METER_PER_SEC := 3.0
const METER_PER_TOUCH := 3.0
const BACK_SPEED := 1.28

const PEN_AIM_T := 5.0
const PEN_SHOT_T := 1.5

const PU_KINDS := ["speed", "jump", "shield", "freeze", "gold"]

const SIZE := 1.05
const BASE_H := 160.0 * SIZE
const JUMP_K := 0.88

# 8 kahraman. jump = sicrama hizi (ayrica kale kirisi siniri var: kafa + top kirisin altina sigar)
# head: carpisma kafasi carpani -> gorsel kafayla ayni olsun diye rig'den olculdu (tools: head fit)
const CHARACTERS := [
	{"name": "ALEV",   "rig": "flame_knight",   "speed": 335.0, "jump": 690.0, "kick": 1.12, "scale": 1.00, "head": 0.975, "power": "fire",   "mass": 1.0},
	{"name": "BUZ",    "rig": "frost_knight",   "speed": 320.0, "jump": 700.0, "kick": 1.09, "scale": 1.02, "head": 0.922, "power": "ice",    "mass": 1.1},
	{"name": "KAYA",   "rig": "stone_guardian", "speed": 295.0, "jump": 680.0, "kick": 1.26, "scale": 1.08, "head": 0.805, "power": "quake",  "mass": 1.5},
	{"name": "KILIÇ",  "rig": "blade_master",   "speed": 345.0, "jump": 690.0, "kick": 1.18, "scale": 1.00, "head": 0.916, "power": "fire",   "mass": 0.95},
	{"name": "EJDER",  "rig": "storm_shaman",   "speed": 315.0, "jump": 705.0, "kick": 1.00, "scale": 1.03, "head": 0.946, "power": "bolt",   "mass": 0.95},
	{"name": "RUH",    "rig": "spirit_shaman",  "speed": 312.0, "jump": 700.0, "kick": 0.96, "scale": 1.00, "head": 0.994, "power": "glove",  "mass": 0.95},
	{"name": "GÖLGE",  "rig": "shadow_ninja",   "speed": 392.0, "jump": 720.0, "kick": 1.06, "scale": 0.98, "head": 0.923, "power": "magnet", "mass": 0.8},
	{"name": "OKÇU",   "rig": "forest_archer",  "speed": 352.0, "jump": 710.0, "kick": 1.03, "scale": 0.97, "head": 1.016, "power": "ice",    "mass": 0.88},
]
const DISPLAY_NAMES := ["ALEV ŞÖVALYESİ", "BUZ ŞÖVALYESİ", "KAYA", "KILIÇ USTASI", "EJDER ŞAMAN", "RUH ŞAMAN", "GÖLGE", "OKÇU"]
# hiz, ziplama, sut (1-5)
const STAT_BARS := [[3, 3, 4], [3, 3, 3], [1, 2, 5], [4, 3, 4], [3, 5, 2], [2, 4, 2], [5, 3, 2], [4, 4, 3]]

# guc: ad, renk
const POWERS := {
	"fire":   ["ATEŞ ŞUTU", Color8(255, 140, 40)],
	"ice":    ["BUZ ŞUTU", Color8(110, 220, 255)],
	"magnet": ["MIKNATIS", Color8(200, 130, 255)],
	"glove":  ["DEV ELDİVEN", Color8(255, 214, 60)],
	"bolt":   ["YILDIRIM", Color8(255, 235, 90)],
	"quake":  ["DEPREM", Color8(230, 150, 90)],
}

## Sicrama hiz siniri: kafanin tepesi kale kirisinin altinda en az top capi + 2 bosluk birakir
## (top her zaman ziplayan oyuncunun ustunden kaleye girebilir). top_y = kafa tepesinin su anki y'si.
static func jump_cap_from(top_y: float) -> float:
	var room := top_y - (GOAL_TOP + 2.0 * BALL_R + 2.0)
	return sqrt(max(0.0, 2.0 * PLAYER_G * room))

static func jump_cap_h(h: float) -> float:
	return jump_cap_from(GROUND - h)

## 60 Hz icin ayarlanmis "kare basina" katsayiyi dt'ye cevirir (kare hizindan bagimsiz).
static func f60(k: float, dt: float) -> float:
	return 1.0 - pow(1.0 - k, dt * 60.0)

static func p60(k: float, dt: float) -> float:
	return pow(k, dt * 60.0)
