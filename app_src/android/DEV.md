# Important

- adb install does NOT sync assets incrementally
So if new assets added it doesn't add new files
- This works to view app data

```shell
adb shell
run-as org.wally.waller
ls -l files
ls -l files/app
```
