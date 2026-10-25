# Wraith Runner Android

Pygame platformer prototype packaged for Android through Buildozer/python-for-android and GitHub Actions.

## Build

Push to `main`, then open **Actions** and run **Build Android APK**. The workflow uploads the APK as an artifact.

Note: the Android packaging pipeline depends on python-for-android having a compatible pygame recipe. If that recipe fails, inspect the Actions build log; a separate SDL2/Pygame Android port may be needed.
