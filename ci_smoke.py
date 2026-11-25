"""CI duman testi: tum sahneleri gercek pygame ile ekransiz calistirir."""
import os
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("KAFA_OLCEK", "1.5")

import pygame  # noqa: E402
import main  # noqa: E402
import net  # noqa: E402


def run(app, scene, frames, keys=False):
    app.go(scene)
    for f in range(frames):
        if keys and f % 7 == 0:
            for k in (pygame.K_SPACE, pygame.K_s, pygame.K_RETURN, pygame.K_DOWN):
                app.scene.handle(pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0, scancode=0))
        app.scene.update(1 / 60)
        app.scene.draw(app.screen)
        pygame.display.flip()


app = main.App()
print("sound ok:", app.sound.ok)
run(app, main.MenuScene(app), 30)
run(app, main.HelpScene(app), 5)
run(app, main.SelectScene(app, "bot"), 10)
run(app, main.SelectScene(app, "local2"), 10)
random.seed(1)
m = main.MatchScene(app, "bot", [0, 5], 60)
import time
t0 = time.perf_counter()
run(app, m, 60 * 20, keys=True)
print("ortalama kare suresi: %.1f ms" % ((time.perf_counter() - t0) / (60 * 20) * 1000))
w = m.world
# basili tutulan sut (sarj cubugu), cift ziplama, smac yollari
for f in range(40):
    w.apply_input(0, False, True, f % 20 < 3, f == 0, False, f < 30)
    w.step(1 / 60)
    m.snap = w.snapshot()
    m._process(m.snap)
    m.draw(app.screen)
w.players[1].frozen = 2
w.players[0].armed = 3
w.ball.mode = 1
w.pu = ["gold", 600, 300, 5]
w.shield = [3, 3]
run(app, m, 120)
w.time_left = 0.01
w.score = [2, 1]
run(app, m, 120)
assert m.snap["ph"] == "over", m.snap["ph"]
app.stadium = 1
run(app, main.MatchScene(app, "local2", [2, 3], 60), 600, keys=True)
app.stadium = 0
hw = main.HostWaitScene(app)
run(app, hw, 30)
jw = main.JoinScene(app)
run(app, jw, 30)
hw.host.stop()
jw.finder.stop()
run(app, main.MessageScene(app, "TEST", "satir 1\nsatir 2"), 5)
pygame.quit()
print("SMOKE OK")
