"""assets/anim altindaki atlaslari VRAM sikistirmali (ETC2/ASTC, mipmap) ice aktarmaya cevir.
Once godot --import, sonra bu betik, sonra tekrar godot --import."""
import glob, re
n = 0
for p in glob.glob("assets/anim/**/atlas.png.import", recursive=True):
    s = open(p).read()
    s2 = re.sub(r"^compress/mode=\d", "compress/mode=2", s, flags=re.M)
    s2 = re.sub(r"^mipmaps/generate=\w+", "mipmaps/generate=true", s2, flags=re.M)
    if s2 != s:
        open(p, "w").write(s2)
        n += 1
print("guncellenen", n)
