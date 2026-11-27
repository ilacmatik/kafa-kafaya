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
