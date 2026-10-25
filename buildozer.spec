[app]
title = Wraith Runner
package.name = wraithrunner
package.domain = org.rafijordan4
source.dir = .
source.include_exts = py,png,jpg,jpeg,txt,json
version = 0.1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions = VIBRATE
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True
