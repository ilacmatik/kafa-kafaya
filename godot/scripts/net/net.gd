## Ag (ayni Wi-Fi / hotspot): ENet ile host-yetkili mac.
## Bulma: host UDP'de sorgulara cevap verir; istemci hem yayin (broadcast) hem de alt agdaki
## tum adreslere tek tek sorgu atar (Android'de yayin alinamayabildigi icin).
extends Node

const PORT := 50600
const DISC_PORT := 50601
const MAGIC := "KAFA2?"
const REPLY := "KAFA2!"
const PROTO := 1

signal joined                       # karsi taraf baglandi
signal left(reason: String)         # baglanti koptu
signal message(d: Dictionary)       # guvenilir mesaj
signal snap(b: PackedByteArray)     # host -> istemci durum
signal remote_input(a: Array)       # istemci -> host girdi

var peer: ENetMultiplayerPeer
var is_host := false
var active := false
var connected := false
var found := {}                     # ip -> {"name", "seen"}
var my_name := "OYUNCU"

var _disc: PacketPeerUDP            # host: sorgu dinler
var _query: PacketPeerUDP           # istemci: sorgu atar / cevap dinler
var _scan_t := 0.0
var _sweep: Array[String] = []


func _ready() -> void:
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connected_to_server.connect(func(): connected = true; joined.emit())
	multiplayer.connection_failed.connect(func(): left.emit("Bağlanılamadı"); stop())
	multiplayer.server_disconnected.connect(func(): left.emit("Rakip ayrıldı"); stop())
	my_name = OS.get_model_name() if OS.get_model_name() != "GenericDevice" else "OYUNCU"


# ---------------------------------------------------------------- kur / katil
func host() -> int:
	stop()
	peer = ENetMultiplayerPeer.new()
	var err := peer.create_server(PORT, 1)
	if err != OK:
		return err
	multiplayer.multiplayer_peer = peer
	is_host = true
	active = true
	_disc = PacketPeerUDP.new()
	_disc.bind(DISC_PORT)
	return OK


func join(ip: String) -> int:
	stop_scan()
	if peer:
		multiplayer.multiplayer_peer = null
		peer.close()
	peer = ENetMultiplayerPeer.new()
	var err := peer.create_client(ip, PORT)
	if err != OK:
		return err
	multiplayer.multiplayer_peer = peer
	is_host = false
	active = true
	return OK


func stop() -> void:
	stop_scan()
	if _disc:
		_disc.close()
		_disc = null
	if peer:
		peer.close()
	multiplayer.multiplayer_peer = null
	peer = null
	active = false
	connected = false
	is_host = false


# ---------------------------------------------------------------- bulma
func start_scan() -> void:
	stop_scan()
	found.clear()
	_query = PacketPeerUDP.new()
	_query.set_broadcast_enabled(true)
	_query.bind(0)
	_scan_t = 0.0
	_build_sweep()


func stop_scan() -> void:
	if _query:
		_query.close()
		_query = null


func local_ips() -> Array[String]:
	var out: Array[String] = []
	for a: String in IP.get_local_addresses():
		if a.count(".") == 3 and not a.begins_with("127.") and not a.begins_with("169.254."):
			out.append(a)
	return out


func _build_sweep() -> void:
	_sweep.clear()
	for a in local_ips():
		var parts := a.split(".")
		var base := "%s.%s.%s." % [parts[0], parts[1], parts[2]]
		for i in range(1, 255):
			var ip := base + str(i)
			if ip != a:
				_sweep.append(ip)


func _process(dt: float) -> void:
	# host: sorgulara cevap
	if _disc:
		while _disc.get_available_packet_count() > 0:
			var pkt := _disc.get_packet().get_string_from_utf8()
			var ip := _disc.get_packet_ip()
			var port := _disc.get_packet_port()
			if pkt.begins_with(MAGIC) and not connected:
				_disc.set_dest_address(ip, port)
				_disc.put_packet(("%s|%d|%s" % [REPLY, PROTO, my_name]).to_utf8_buffer())
	# istemci: tarama
	if _query:
		_scan_t -= dt
		if _scan_t <= 0.0:
			_scan_t = 1.0
			var q := MAGIC.to_utf8_buffer()
			_query.set_dest_address("255.255.255.255", DISC_PORT)
			_query.put_packet(q)
			for a in local_ips():
				var p := a.split(".")
				_query.set_dest_address("%s.%s.%s.255" % [p[0], p[1], p[2]], DISC_PORT)
				_query.put_packet(q)
		# alt agi parca parca tara (her karede 24 adres)
		for i in mini(24, _sweep.size()):
			var ip2: String = _sweep.pop_back()
			_query.set_dest_address(ip2, DISC_PORT)
			_query.put_packet(MAGIC.to_utf8_buffer())
		if _sweep.is_empty() and _scan_t > 0.9:
			_build_sweep()
		while _query.get_available_packet_count() > 0:
			var r := _query.get_packet().get_string_from_utf8()
			var rip := _query.get_packet_ip()
			if r.begins_with(REPLY):
				var f := r.split("|")
				found[rip] = {"name": f[2] if f.size() > 2 else rip, "seen": Time.get_ticks_msec(),
					"ok": f.size() > 1 and int(f[1]) == PROTO}
		var now := Time.get_ticks_msec()
		for k in found.keys():
			if now - int(found[k]["seen"]) > 4000:
				found.erase(k)


# ---------------------------------------------------------------- baglanti olaylari
func _on_peer_connected(_id: int) -> void:
	if is_host:
		connected = true
		joined.emit()


func _on_peer_disconnected(_id: int) -> void:
	if is_host and connected:
		connected = false
		left.emit("Rakip ayrıldı")


# ---------------------------------------------------------------- gonderme
func send(d: Dictionary) -> void:
	if connected:
		_msg.rpc(d)


func send_snap(b: PackedByteArray) -> void:
	if connected:
		_snap.rpc(b)


func send_input(a: Array) -> void:
	if connected:
		_inp.rpc(a)


@rpc("any_peer", "call_remote", "reliable")
func _msg(d: Dictionary) -> void:
	message.emit(d)


@rpc("any_peer", "call_remote", "unreliable_ordered")
func _snap(b: PackedByteArray) -> void:
	snap.emit(b)


@rpc("any_peer", "call_remote", "unreliable_ordered")
func _inp(a: Array) -> void:
	remote_input.emit(a)


# ---------------------------------------------------------------- durum paketleme
static var _fields := {}


## Bir sim nesnesinin betik degiskenlerini (sirali) listeye cevir.
static func pack_obj(o: Object, skip: Array = []) -> Array:
	var out := []
	for n: String in _field_names(o, skip):
		out.append(o.get(n))
	return out


static func unpack_obj(o: Object, vals: Array, skip: Array = []) -> void:
	var names := _field_names(o, skip)
	for i in mini(names.size(), vals.size()):
		o.set(names[i], vals[i])


static func _field_names(o: Object, skip: Array) -> Array:
	var sc: Script = o.get_script()
	var key := sc.resource_path + str(skip)
	if _fields.has(key):
		return _fields[key]
	var names := []
	for p: Dictionary in sc.get_script_property_list():
		if p["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE == 0:
			continue
		var n: String = p["name"]
		if n in skip:
			continue
		var v = o.get(n)
		if v is Object:
			continue
		names.append(n)
	_fields[key] = names
	return names


const W_SKIP := ["players", "ball", "events", "rng"]


static func pack_world(w: SimWorld, ev: Array) -> PackedByteArray:
	var d := [pack_obj(w, W_SKIP), pack_obj(w.players[0]), pack_obj(w.players[1]), pack_obj(w.ball), ev]
	var raw := var_to_bytes(d)
	var c := raw.compress(FileAccess.COMPRESSION_DEFLATE)
	var out := PackedByteArray()
	out.resize(4)
	out.encode_u32(0, raw.size())
	out.append_array(c)
	return out


## Durumu dunyaya yaz, olaylari dondur.
static func unpack_world(w: SimWorld, b: PackedByteArray) -> Array:
	if b.size() < 5:
		return []
	var n := b.decode_u32(0)
	if n <= 0 or n > 1 << 20:
		return []
	var d = bytes_to_var(b.slice(4).decompress(n, FileAccess.COMPRESSION_DEFLATE))
	if not d is Array or d.size() < 5:
		return []
	unpack_obj(w, d[0], W_SKIP)
	unpack_obj(w.players[0], d[1])
	unpack_obj(w.players[1], d[2])
	unpack_obj(w.ball, d[3])
	return d[4]
