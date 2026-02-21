[app]
#title = ANTester
title = Waller

#package.name = androidnotify
package.name = waller

#package.domain = app.vercel
package.domain = org.wally
author = Fabian © Copyright Info
version = 1.0.1

source.dir = app_src

presplash.filename = %(source.dir)s/assets/icons/presplash.png
icon.filename = %(source.dir)s/assets/icons/icon.png

source.include_exts = py,png,jpg,kv,atlas,ttf,json,xml,wav
source.exclude_dirs = bin, venv,lab, worked, __pycache__, .idea, dist, for-download,laner-linux, .filereader, wallpapers


requirements = python3,kivy,https://github.com/kivymd/KivyMD/archive/master.zip,python-osc,https://github.com/kivy/plyer/archive/master.zip,materialyoucolor,asynckivy,asyncgui,pyjnius, docutils,netifaces,filetype,requests_toolbelt,websockets,android-widgets, https://github.com/Fector101/android_notify/archive/main.zip
services = Wallpapercarousel:./android/services/wallpaper.py:foreground
# Shorttask:./android/services/shorttask.py

osx.python_version = 3
osx.kivy_version = 1.9.1

fullscreen = 0
orientation = portrait

android.api = 35
android.permissions = RECEIVE_BOOT_COMPLETED, INTERNET, VIBRATE, USE_EXACT_ALARM, SCHEDULE_EXACT_ALARM, FOREGROUND_SERVICE, FOREGROUND_SERVICE_SPECIAL_USE, POST_NOTIFICATIONS, SET_WALLPAPER, READ_MEDIA_IMAGES, (name=android.permission.READ_EXTERNAL_STORAGE;maxSdkVersion=32), (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=28)
#android.permissions = RECEIVE_BOOT_COMPLETED, INTERNET, VIBRATE, USE_EXACT_ALARM, SCHEDULE_EXACT_ALARM, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC, POST_NOTIFICATIONS, SET_WALLPAPER, READ_MEDIA_IMAGES, (name=android.permission.READ_EXTERNAL_STORAGE;maxSdkVersion=32), (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=28)
android.add_src = %(source.dir)s/android/src
android.add_resources = %(source.dir)s/android/res
android.gradle_dependencies = androidx.core:core-ktx:1.12.0, com.google.android.material:material:1.12.0
#android.gradle_dependencies = com.google.android.material:material:1.6.0, androidx.core:core-ktx:1.15.0, androidx.core:core:1.6.0, androidx.work:work-runtime:2.9.0
android.enable_androidx = True
p4a.hook = %(source.dir)s/android/p4a/hook.py
p4a.branch = develop

android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True


ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false

[buildozer]
log_level = 2
warn_on_root = 1
