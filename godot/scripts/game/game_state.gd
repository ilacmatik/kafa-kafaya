## Global durum: secimler, ayarlar, sahne gecisleri. Ayarlar user://settings.json'da saklanir.
extends Node

const SAVE_PATH := "user://settings.json"
const LEVELS := ["KOLAY", "NORMAL", "ZOR"]
const DURATIONS := [60.0, 90.0, 120.0]
const STADIUM_NAMES := ["GECE ARENASI", "TİMSAH ARENA"]
const WEATHERS := [["clear", "AÇIK HAVA"], ["rain", "YAĞMUR"], ["snow", "KAR"], ["wind", "RÜZGAR"], ["random", "RASTGELE"]]

var chars := [0, 3]
var mode := "bot"
var level := 1
var duration := 90.0
var weather := "clear"      # secilen (random olabilir)
var weather_now := "clear"  # macta kullanilan
var stadium := 0
var cache: Array = []       # yukleme ekraninda onceden yuklenen kaynaklar bellekte kalsin

# --- profil (ilerleme, altin) - ileride kozmetik magazasi bunu kullanacak
const PROFILE_PATH := "user://profile.json"
var profile := {"xp": 0, "coins": 0, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals": 0, "cups": 0}
var last_reward := {}       # son macin odulu (mac sonu ekrani gosterir)

# --- kupa yolu
const CUP_STAGES := [   # ad, bot seviyesi, hava, stadyum
	["ÇEYREK FİNAL 1", 0, "clear", 1],
	["ÇEYREK FİNAL 2", 1, "rain", 0],
	["YARI FİNAL", 1, "wind", 1],
	["FİNAL ÖNCESİ", 2, "snow", 0],
	["BÜYÜK FİNAL", 2, "clear", 1],
]
var cup := {}               # {"char", "opps", "stage", "lost"}
var cup_result = null       # null | true | false (son kupa macinin sonucu)

var _fade: ColorRect
var _layer: CanvasLayer
var _busy := false


func _ready() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 100
	add_child(_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0.01, 0.02, 0.06, 0.0)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_layer.add_child(_fade)
	load_settings()
	load_profile()


## Karartarak sahne degistir.
func go(path: String) -> void:
	if _busy:
		return
	_busy = true
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 1.0, 0.18)
	await tw.finished
	get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await get_tree().process_frame
	var tw2 := create_tween()
	tw2.tween_property(_fade, "color:a", 0.0, 0.25)
	await tw2.finished
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_busy = false


func start_match() -> void:
	weather_now = weather
	if weather == "random":
		var opts := ["clear", "clear", "rain", "snow", "wind"]
		weather_now = opts[randi() % opts.size()]
	save_settings()
	go("res://scenes/match.tscn")


func load_settings() -> void:
	if not FileAccess.file_exists(SAVE_PATH):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if not d is Dictionary:
		return
	level = clampi(int(d.get("level", level)), 0, 2)
	duration = float(d.get("duration", duration))
	if not duration in DURATIONS:
		duration = 90.0
	stadium = clampi(int(d.get("stadium", stadium)), 0, STADIUM_NAMES.size() - 1)
	weather = str(d.get("weather", weather))
	var ok := false
	for w in WEATHERS:
		ok = ok or w[0] == weather
	if not ok:
		weather = "clear"
	var c = d.get("chars", chars)
	if c is Array and c.size() == 2:
		chars = [clampi(int(c[0]), 0, 5), clampi(int(c[1]), 0, 5)]


func save_settings() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"level": level, "duration": duration, "stadium": stadium,
			"weather": weather, "chars": chars}))


func weather_name(w: String) -> String:
	for x in WEATHERS:
		if x[0] == w:
			return x[1]
	return w


# ---------------------------------------------------------------- profil
func load_profile() -> void:
	if not FileAccess.file_exists(PROFILE_PATH):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(PROFILE_PATH))
	if d is Dictionary:
		for k in profile:
			if d.has(k):
				profile[k] = int(d[k])
		if d.has("cup") and d["cup"] is Dictionary:
			cup = d["cup"]


func save_profile() -> void:
	var f := FileAccess.open(PROFILE_PATH, FileAccess.WRITE)
	if f:
		var d := profile.duplicate()
		d["cup"] = cup
		f.store_string(JSON.stringify(d))


## Seviye n'den n+1'e gecis icin gereken XP (yavasca artar)
static func xp_need(lvl: int) -> int:
	return 100 + (lvl - 1) * 40


func level_info() -> Array:   # [seviye, bu seviyedeki xp, gereken]
	var lvl := 1
	var xp: int = profile["xp"]
	while xp >= xp_need(lvl):
		xp -= xp_need(lvl)
		lvl += 1
	return [lvl, xp, xp_need(lvl)]


## Mac sonucunu isle, odulu dondur. res: 1 galibiyet, 0 beraberlik, -1 maglubiyet
func add_result(res: int, goals: int, bonus_coins: int = 0) -> Dictionary:
	var before: int = level_info()[0]
	var xp: int = [15, 25, 50][res + 1] + goals * 10
	var coins: int = [10, 15, 30][res + 1] + goals * 5 + bonus_coins
	profile["xp"] += xp
	profile["coins"] += coins
	profile["matches"] += 1
	profile["goals"] += goals
	profile[["losses", "draws", "wins"][res + 1]] += 1
	var after: int = level_info()[0]
	last_reward = {"xp": xp, "coins": coins, "level_up": after > before, "level": after}
	save_profile()
	return last_reward


# ---------------------------------------------------------------- kupa
func new_cup(char: int) -> void:
	var pool := []
	for i in 6:
		if i != char:
			pool.append(i)
	pool.shuffle()
	# 5 tur: 5 farkli rakip
	cup = {"char": char, "opps": pool.slice(0, 5), "stage": 0, "lost": false}
	cup_result = null
	save_profile()


func start_cup_match() -> void:
	var st: Array = CUP_STAGES[int(cup["stage"])]
	mode = "cup"
	chars = [int(cup["char"]), int(cup["opps"][int(cup["stage"])])]
	weather_now = st[2]
	go("res://scenes/match.tscn")


## Macta kullanilacak degerler (kupada turun ayarlari, aksi halde kullanicinin secimi)
func m_level() -> int:
	return int(CUP_STAGES[int(cup["stage"])][1]) if mode == "cup" else level


func m_stadium() -> int:
	return int(CUP_STAGES[int(cup["stage"])][3]) if mode == "cup" else stadium


func m_duration() -> float:
	return 90.0 if mode == "cup" else duration
