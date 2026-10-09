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

# Force Buildozer to use GitHub's pre-installed, pre-licensed Android SDK & NDK
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/25.2.9519653
android.accept_sdk_license = True

android.api = 34
android.minapi = 26
android.private_storage = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
