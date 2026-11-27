## Kafa Kafaya - simulasyon sabitleri (Python sim.py ile birebir).
## Dunya birimi: 1280x720 mantiksal saha. Cizim 1.5 ile 1920x1080'e olceklenir.
class_name K
extends RefCounted

const W := 1280.0
const H := 720.0
const GROUND := 652.0
const GOAL_D := 102.0          # kale cizgisi (on direk ic yuzu) x konumu
const GOAL_H := 285.0          # kale agzi yuksekligi
const ROOF_T := 26.0           # ust direk kalinligi
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

const SIZE := 0.95
const BASE_H := 160.0 * SIZE
const JUMP_K := 0.88

const CHARACTERS := [
	{"name": "ALEV",   "speed": 335.0, "jump": 650.0, "kick": 1.12, "scale": 1.00, "head": 1.00, "power": "fire",   "mass": 1.0},
	{"name": "KAPTAN", "speed": 320.0, "jump": 655.0, "kick": 1.06, "scale": 1.02, "head": 1.05, "power": "magnet", "mass": 1.12},
	{"name": "DUVAR",  "speed": 300.0, "jump": 700.0, "kick": 0.95, "scale": 1.00, "head": 1.12, "power": "glove",  "mass": 1.05},
	{"name": "SARI",   "speed": 322.0, "jump": 715.0, "kick": 1.00, "scale": 1.03, "head": 1.00, "power": "ice",    "mass": 1.0},
	{"name": "SIMSEK", "speed": 385.0, "jump": 645.0, "kick": 0.95, "scale": 0.95, "head": 0.95, "power": "bolt",   "mass": 0.8},
	{"name": "TANK",   "speed": 275.0, "jump": 610.0, "kick": 1.30, "scale": 1.08, "head": 1.10, "power": "quake",  "mass": 1.55},
]
const DISPLAY_NAMES := ["ALEV", "KAPTAN", "DUVAR", "SARI", "ŞİMŞEK", "TANK"]
const STAT_BARS := [[4, 3, 4], [3, 3, 4], [2, 5, 2], [3, 5, 3], [5, 2, 2], [1, 1, 5]]

# guc: ad, renk
const POWERS := {
	"fire":   ["ATEŞ ŞUTU", Color8(255, 140, 40)],
	"ice":    ["BUZ ŞUTU", Color8(110, 220, 255)],
	"magnet": ["MIKNATIS", Color8(200, 130, 255)],
	"glove":  ["DEV ELDİVEN", Color8(255, 214, 60)],
	"bolt":   ["YILDIRIM", Color8(255, 235, 90)],
	"quake":  ["DEPREM", Color8(230, 150, 90)],
}

static func jump_cap_h(h: float) -> float:
	var room := GROUND - h - (GOAL_TOP + 2.0 * BALL_R + 2.0)
	return sqrt(max(0.0, 2.0 * PLAYER_G * room))

## 60 Hz icin ayarlanmis "kare basina" katsayiyi dt'ye cevirir (kare hizindan bagimsiz).
static func f60(k: float, dt: float) -> float:
	return 1.0 - pow(1.0 - k, dt * 60.0)

static func p60(k: float, dt: float) -> float:
	return pow(k, dt * 60.0)
