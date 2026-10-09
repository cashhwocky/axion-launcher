[app]
title = Axion Launcher
package.name = axionlauncher
package.domain = org.axion

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
version = 0.1

requirements = python3,kivy==2.2.1,pillow,pyjnius,android

orientation = portrait
fullscreen = 0

# Lets the launcher list every installed app (Android 11+ package visibility)
android.permissions = QUERY_ALL_PACKAGES

android.api = 35
android.minapi = 26
android.ndk = 26b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True

# Registers the app as a selectable HOME launcher
android.manifest.intent_filters = intent_filters.xml
android.manifest.launch_mode = singleTask

[buildozer]
log_level = 2
warn_on_root = 1
