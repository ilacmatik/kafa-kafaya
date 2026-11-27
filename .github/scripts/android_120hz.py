"""Godot Android derleme sablonuna: acilista ekranin en yuksek yenileme hizini (90/120 Hz) iste.
Android 15+ oyunlari varsayilan 60 Hz'de tutar; bunu acikca istemek gerekir."""
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
cands = [p for p in root.rglob("*") if p.is_file() and p.name.startswith("GodotApp.") and p.suffix in (".java", ".kt")]
if not cands:
    print("UYARI: GodotApp bulunamadi, 120 Hz yamasi atlandi"); sys.exit(0)
JAVA = """
        try {
            android.view.Display d = getWindowManager().getDefaultDisplay();
            android.view.Display.Mode cur = d.getMode();
            android.view.Display.Mode best = cur;
            for (android.view.Display.Mode m : d.getSupportedModes()) {
                if (m.getPhysicalWidth() == cur.getPhysicalWidth() && m.getPhysicalHeight() == cur.getPhysicalHeight()
                        && m.getRefreshRate() > best.getRefreshRate()) best = m;
            }
            android.view.WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.preferredDisplayModeId = best.getModeId();
            lp.preferredRefreshRate = best.getRefreshRate();
            getWindow().setAttributes(lp);
        } catch (Throwable ignored) { }
"""
KT = """
        try {
            val d = windowManager.defaultDisplay
            val cur = d.mode
            var best = cur
            for (m in d.supportedModes) {
                if (m.physicalWidth == cur.physicalWidth && m.physicalHeight == cur.physicalHeight
                    && m.refreshRate > best.refreshRate) best = m
            }
            val lp = window.attributes
            lp.preferredDisplayModeId = best.modeId
            lp.preferredRefreshRate = best.refreshRate
            window.attributes = lp
        } catch (t: Throwable) { }
"""
for p in cands:
    s = p.read_text()
    print("----", p); print(s[:3000])
    if "preferredDisplayModeId" in s:
        continue
    pat = r"(super\.onCreate\(savedInstanceState\);?)"
    if re.search(pat, s):
        s = re.sub(pat, r"\1" + (JAVA if p.suffix == ".java" else KT), s, count=1)
    else:
        # onCreate yoksa ekle
        if p.suffix == ".java":
            s = re.sub(r"(public class GodotApp[^{]*\{)", r"\1\n    @Override\n    public void onCreate(android.os.Bundle savedInstanceState) {\n        super.onCreate(savedInstanceState);" + JAVA + "    }\n", s, count=1)
        else:
            s = re.sub(r"(class GodotApp[^{]*\{)", r"\1\n    override fun onCreate(savedInstanceState: android.os.Bundle?) {\n        super.onCreate(savedInstanceState)" + KT + "    }\n", s, count=1)
    p.write_text(s)
    print("YAMALANDI:", p)
