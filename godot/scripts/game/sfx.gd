## Ses efektleri: Python surumundeki sentez seslerinin aynisi (assets/sfx/*.wav).
extends Node

var players: Array[AudioStreamPlayer] = []
var streams := {}
var last := {}
var crowd: AudioStreamPlayer
var muted := false
const GAP := {"bounce": 0.07, "kick": 0.04, "head": 0.06, "land": 0.1, "tick": 0.2, "swing": 0.05}


func _ready() -> void:
	for i in 16:
		var p := AudioStreamPlayer.new()
		add_child(p)
		players.append(p)
	var d := DirAccess.open("res://assets/sfx")
	if d:
		for f in d.get_files():
			var fn := f.trim_suffix(".import").trim_suffix(".remap")
			if fn.ends_with(".wav"):
				var key := fn.get_basename()
				if not streams.has(key):
					streams[key] = load("res://assets/sfx/" + fn)
	if streams.has("crowd"):
		var s: AudioStreamWAV = streams["crowd"].duplicate()
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = s.data.size() / 2
		crowd = AudioStreamPlayer.new()
		crowd.stream = s
		crowd.volume_db = -10.0
		add_child(crowd)


func start_crowd() -> void:
	if crowd and not muted:
		crowd.play()


func play(name: String, vol_db: float = 0.0, pitch: float = 1.0) -> void:
	if muted or not streams.has(name):
		return
	var now := Time.get_ticks_msec() / 1000.0
	if now - float(last.get(name, -9.0)) < float(GAP.get(name, 0.0)):
		return
	last[name] = now
	for p in players:
		if not p.playing:
			p.stream = streams[name]
			p.volume_db = vol_db
			p.pitch_scale = pitch
			p.play()
			return
