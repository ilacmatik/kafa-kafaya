"""Yerel ag baglantisi: TCP (oyun verisi) + UDP yayin (otomatik oyun bulma)."""
import json
import queue
import socket
import threading
import time

TCP_PORT = 50505
UDP_PORT = 50506
QUERY_PORT = 50507      # "orada mac var mi?" sorgusu (hotspot gibi yayinin gitmedigi aglar icin)
MAGIC = "KAFAKAFAYA1"

# platforma ozel ek bilgiler (Android'de touch.py doldurur)
EXTRA_IPS = lambda: []          # noqa: E731  - bu cihazin tum IPv4 adresleri
GATEWAYS = lambda: []           # noqa: E731  - bagli olunan agin ag gecidi (hotspot sahibi)


def local_ips():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    # 100.100.100.100: Tailscale (internet uzerinden sanal ag) adresi
    for probe in ("10.255.255.255", "192.168.255.255", "172.16.255.255", "100.100.100.100"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((probe, 1))
            ips.add(s.getsockname()[0])
            s.close()
        except OSError:
            pass
    try:
        ips.update(EXTRA_IPS())
    except Exception:
        pass
    ips = [ip for ip in ips if not ip.startswith("127.") and not ip.startswith("169.254.")]
    # once yaygin ev/ofis aglari
    ips.sort(key=lambda ip: (not ip.startswith("192.168."), ip))
    return ips


class Conn:
    """Satir bazli JSON mesajlari tasiyan TCP baglantisi."""

    def __init__(self, sock):
        self.sock = sock
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(None)
        self.inbox = queue.Queue()
        self.alive = True
        self.lock = threading.Lock()
        self.last_recv = time.time()
        self.outq = queue.Queue()
        self._latest = {}          # sik mesajlar ("st", "in"): sadece en yenisi gonderilir
        self._latest_lock = threading.Lock()
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._writer, daemon=True).start()

    def _reader(self):
        buf = b""
        try:
            while self.alive:
                data = self.sock.recv(65536)
                if not data:
                    break
                self.last_recv = time.time()
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line:
                        try:
                            self.inbox.put(json.loads(line.decode("utf-8")))
                        except ValueError:
                            pass
        except OSError:
            pass
        self.alive = False

    def send(self, msg):
        """Bloklamaz: oyun dongusu ag yuzunden takilmasin diye ayri is parcacigi yollar."""
        if not self.alive:
            return
        t = msg.get("t")
        if t in ("st", "in"):
            with self._latest_lock:
                fresh = t not in self._latest
                self._latest[t] = msg
            if fresh:
                self.outq.put(t)
        else:
            self.outq.put(msg)

    def _writer(self):
        try:
            while self.alive:
                try:
                    item = self.outq.get(timeout=0.5)
                except queue.Empty:
                    continue
                if isinstance(item, str):
                    with self._latest_lock:
                        msg = self._latest.pop(item, None)
                    if msg is None:
                        continue
                else:
                    msg = item
                data = (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")
                self.sock.sendall(data)
        except OSError:
            pass
        self.alive = False

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self):
        # bekleyen mesajlar (or. "bye") gitsin diye kisa bekle
        t0 = time.time()
        while self.alive and not self.outq.empty() and time.time() - t0 < 0.3:
            time.sleep(0.01)
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class Host:
    """Mac kuran taraf: baglanti bekler ve agda kendini duyurur."""

    def __init__(self, name="Oyuncu"):
        self.name = name
        self.conn = None
        self.error = None
        self.running = True
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.srv.bind(("", TCP_PORT))
            self.srv.listen(1)
        except OSError as e:
            self.error = "Port %d acilamadi: %s" % (TCP_PORT, e)
            self.running = False
            return
        self.srv.settimeout(0.5)
        threading.Thread(target=self._accept, daemon=True).start()
        threading.Thread(target=self._announce, daemon=True).start()
        threading.Thread(target=self._respond, daemon=True).start()

    def _respond(self):
        """Sorgu gelince dogrudan sorana cevap ver (yayin ulasmayan aglarda da bulunuruz)."""
        try:
            q = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            q.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            q.bind(("", QUERY_PORT))
            q.settimeout(0.5)
        except OSError:
            return
        msg = ("%s|%s|%d" % (MAGIC, self.name, TCP_PORT)).encode("utf-8")
        while self.running and self.conn is None:
            try:
                data, addr = q.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break
            if data.startswith(MAGIC.encode()):
                try:
                    q.sendto(msg, (addr[0], UDP_PORT))
                except OSError:
                    pass
        q.close()

    def _accept(self):
        while self.running and self.conn is None:
            try:
                s, addr = self.srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.conn = Conn(s)
            self.peer = addr[0]
        try:
            self.srv.close()
        except OSError:
            pass

    def _announce(self):
        try:
            u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            return
        msg = ("%s|%s|%d" % (MAGIC, self.name, TCP_PORT)).encode("utf-8")
        while self.running and self.conn is None:
            targets = ["255.255.255.255"]
            for ip in local_ips():
                parts = ip.split(".")
                if len(parts) == 4:
                    targets.append(".".join(parts[:3] + ["255"]))
            for t in targets:
                try:
                    u.sendto(msg, (t, UDP_PORT))
                except OSError:
                    pass
            time.sleep(1.0)
        u.close()

    def stop(self):
        self.running = False
        try:
            self.srv.close()
        except OSError:
            pass
        if self.conn:
            self.conn.close()


class Finder:
    """Agdaki maclari dinler."""

    def __init__(self):
        self.found = {}   # ip -> (isim, port, zaman)
        self.running = True
        self.error = None
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", UDP_PORT))
            self.sock.settimeout(0.5)
        except OSError as e:
            self.error = str(e)
            self.running = False
            return
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._query, daemon=True).start()

    def _query(self):
        try:
            u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            return
        q = (MAGIC + "?").encode()
        while self.running:
            targets = set(["255.255.255.255"])
            try:
                targets.update(GATEWAYS())
            except Exception:
                pass
            for ip in local_ips():
                p = ip.split(".")
                if len(p) == 4:
                    targets.add(".".join(p[:3] + ["255"]))
                    targets.add(".".join(p[:3] + ["1"]))     # cogu hotspot/modem .1 olur
            for t in targets:
                try:
                    u.sendto(q, (t, QUERY_PORT))
                except OSError:
                    pass
            time.sleep(1.0)
        u.close()

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                parts = data.decode("utf-8").split("|")
                if parts[0] == MAGIC:
                    self.found[addr[0]] = (parts[1], int(parts[2]), time.time())
            except (ValueError, IndexError, UnicodeDecodeError):
                pass

    def hosts(self):
        now = time.time()
        return [(ip, v[0], v[1]) for ip, v in sorted(self.found.items()) if now - v[2] < 4]

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass


class Connector:
    """Arka planda baglanmaya calisir (arayuz donmasin diye)."""

    def __init__(self, ip, port=TCP_PORT):
        self.conn = None
        self.error = None
        self.done = False
        threading.Thread(target=self._run, args=(ip, port), daemon=True).start()

    def _run(self, ip, port):
        try:
            s = socket.create_connection((ip, port), timeout=4)
            self.conn = Conn(s)
        except OSError as e:
            self.error = str(e)
        self.done = True
