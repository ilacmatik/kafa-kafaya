[app]
title = Kafa Kafaya
package.name = kafakafaya
package.domain = org.ilacmatik
source.dir = .
source.include_exts = py,png,jpg,json,ttf,txt,ico
source.exclude_dirs = .github,bin,.buildozer,__pycache__,tools,dist,build
source.exclude_patterns = ci_smoke.py,build.bat,README.md,OKU_BENI.txt,requirements.txt,android_icon.png,android_presplash.png
version = 1.0
requirements = python3,pygame,pyjnius
icon.filename = %(source.dir)s/android_icon.png
presplash.filename = %(source.dir)s/android_presplash.png
android.presplash_color = #0C1022
orientation = landscape
fullscreen = 1

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE,WAKE_LOCK
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
