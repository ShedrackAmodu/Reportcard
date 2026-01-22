## Android APK packaging (Capacitor + PWABuilder)

This folder contains scaffolding and instructions to produce an Android APK for the ReportCard PWA.

Two recommended approaches:

1) PWABuilder (quick if your PWA is hosted on HTTPS)
  - Visit https://pwabuilder.com and enter your site URL (or use the CLI `pwabuilder`).
  - PWABuilder can generate an Android/TWA package which you can build in Android Studio.

2) Capacitor (wraps the PWA in a native WebView or points to a hosted URL)
  - Use this when you want to bundle web assets or run a local server (recommended during development).

Windows quick-start (Capacitor, assumes Node.js + Android Studio installed):

1. Install Node and npm (if not installed).
2. Open a terminal in this folder and run:

```powershell
npm install --save-dev @capacitor/cli @capacitor/android
npx cap init com.yourorg.reportcard ReportCard --web-dir=www
# If you want to use your running dev server instead of bundled assets:
npx cap config server.url http://10.0.2.2:8000
# Add Android platform
npx cap add android
# If you bundle web assets, put them into android_package/www, then:
npx cap copy
# Open Android Studio to build the APK
npx cap open android
```

Notes:
- For `server.url` use a URL accessible from the Android emulator/device. `10.0.2.2:8000` maps to localhost on the host machine for the Android emulator.
- To create a production APK, open the Android project in Android Studio and build a signed bundle/APK.
- If your site is hosted at an HTTPS URL, using PWABuilder → TWA may be faster.

Helper files in this folder provide a starting `package.json` and `capacitor.config.json`.
