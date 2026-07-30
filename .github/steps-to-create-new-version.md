## create

- update-note-v1.0.7.txt - for in app display for user
- release-note-v1.0.7.txt - for release page on GitHub

## Change `version` variable in
`utils/constants.py`, `buildoder.spec` and `README.md` to new version number.

how to check new features and fixes
1. https://github.com/Fector101/wallpaper-carousel/compare/v1.0.8...main

GitHub compare page (first attempt, failed to render):
https://github.com/Fector101/wallpaper-carousel/compare/v1.0.8...main

2. File-level change summary:
    git diff v1.0.8...main --stat
    git diff v1.0.8...main --compact-summary

3.Targeted source diffs to understand specific features:
    git diff v1.0.8...main -- app_src/utils/constants.py
    git diff v1.0.8...main -- app_src/utils/image_operations.py
    git diff v1.0.8...main -- app_src/utils/permissions.py
    git diff v1.0.8...main -- app_src/utils/config_manager.py
    git diff v1.0.8...main -- app_src/main.py
    git diff v1.0.8...main -- app_src/ui/screens/settings_screen.py
    git diff v1.0.8...main -- app_src/ui/widgets/layouts.py
    git diff v1.0.8...main -- app_src/ui/screens/gallery_screen.py
    git diff v1.0.8...main -- app_src/android/src/BootReceiver.java
