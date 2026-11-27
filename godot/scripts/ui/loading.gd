## Acilis / yukleme ekrani: agir dokulari arka planda yukler, ilerleme gosterir, sonra ana menu.
extends UIScreen

const MSGS := ["Saha sulanıyor", "Top şişiriliyor", "Taraftarlar yerleşiyor", "Formalar ütüleniyor", "Hakem ısınıyor"]
const MIN_TIME := 1.6

var queue: Array[String] = []
var total := 0
var done := 0
var shown := 0.0
var finished := false


func _ready() -> void:
	super._ready()
	var names := ["m2_bg.jpg", "sel_bg.jpg", "vs_bg.jpg", "vs_emblem.png", "stadium_night_clean.jpg",
		"stadium_timsah_clean.jpg", "stadium_timsah_rain_clean.jpg", "stadium_timsah_snow_clean.jpg",
		"crowd_atlas.png", "crowd_tint.png", "crowd_mask_night.png", "crowd_mask_timsah.png",
		"goal_art.png", "goal_post.png", "logo.png"]
	for i in 6:
		names.append("sel_hero%d.png" % i)
		for p in R.POSES:
			names.append("p%d_%s.png" % [i, p])
	for n in names:
		var path: String = "res://assets/" + n
		if ResourceLoader.exists(path):
			queue.append(path)
			ResourceLoader.load_threaded_request(path, "", true)
	total = queue.size() + 6


func tick(dt: float) -> void:
	# tamamlanan dokulari topla
	var i := 0
	while i < queue.size():
		var st := ResourceLoader.load_threaded_get_status(queue[i])
		if st == ResourceLoader.THREAD_LOAD_LOADED or st == ResourceLoader.THREAD_LOAD_FAILED or st == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			if st == ResourceLoader.THREAD_LOAD_LOADED:
				Game.cache.append(ResourceLoader.load_threaded_get(queue[i]))
			queue.remove_at(i)
			done += 1
		else:
			i += 1
	# dokular bitince portreleri kare kare uret (takilma olmasin)
	if queue.is_empty() and done < total:
		var c := done - (total - 6)
		R.portrait_pop(c, 192)
		done += 1
	var target := float(done) / float(total)
	shown = minf(move_toward(shown, target, dt * 1.5), t / MIN_TIME)
	if shown >= 1.0 and t >= MIN_TIME and not finished:
		finished = true
		Game.go("res://scenes/menu.tscn")


func paint() -> void:
	cover(R.tex("ld_bg.jpg"))
	draw_rect(Rect2(view_l, 0, view_r - view_l, LH), Color(0.02, 0.03, 0.1, 0.25))
	var lg := R.tex("logo.png")
	if lg:
		var w := 560.0
		var h := lg.get_height() * w / lg.get_width()
		var bob := sin(t * 2.0) * 4.0
		R.glow(self, Vector2(LW / 2.0, 250), 360, Color(1, 0.85, 0.4, 0.25))
		draw_texture_rect(lg, Rect2(LW / 2.0 - w / 2.0, 250 - h / 2.0 + bob, w, h), false)
	# ilerleme cubugu
	var bar := Rect2(LW / 2.0 - 300, 560, 600, 30)
	R.panel(self, bar.grow(6), Color(0.03, 0.05, 0.14, 0.85), 20, Color(1, 1, 1, 0.5), 2)
	var k := clampf(shown, 0.0, 1.0)
	if k > 0.02:
		var fr := Rect2(bar.position, Vector2(bar.size.x * k, bar.size.y))
		R.panel(self, fr, GOLD, 15)
		draw_rect(Rect2(fr.position + Vector2(8, 4), Vector2(maxf(0.0, fr.size.x - 16), 7)), Color(1, 1, 1, 0.35))
		# parlayan uc
		R.glow(self, Vector2(fr.end.x, fr.get_center().y), 34, Color(1, 0.9, 0.5, 0.7))
	var msg: String = MSGS[int(t / 0.7) % MSGS.size()] + ".".repeat(int(t * 3.0) % 4)
	R.text(self, msg, 26, Vector2(LW / 2.0, 625), WHITE, 4)
	R.text(self, "%d%%" % int(k * 100.0), 22, Vector2(bar.end.x + 50, bar.get_center().y), GOLD, 3)
