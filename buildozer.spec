[app]
title = Axion Launcher
package.name = axionlauncher
package.domain = org.cashhwocky
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
version = 1.0
requirements = python3,kivy==2.2.1,pillow,pyjnius,android
orientation = portrait
fullscreen = 1
android.api = 34
android.minapi = 26
android.ndk = 25b
android.private_storage = True
p4a.branch = master
[buildozer]
log_level = 2
warn_on_root = 1
