# Important

- adb install does NOT sync assets incrementally
So if new assets added it doesn't add new files
- This works to view app data

```shell
adb shell
run-as org.wally.waller
ls -l files
cd files/app
```
How to see WAKE INTENT
```shell
adb logcat | grep Intent
```
```shell
adb logcat | grep -E "python|Wallpapercarousel"
```
