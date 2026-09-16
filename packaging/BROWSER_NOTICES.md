# Bundled browser and WebView notices

JobPilot Local Phase 9 distributions bundle the Playwright-managed browser assets required by the application. Microsoft Edge WebView2 remains an operating-system runtime dependency and is not copied into the JobPilot program directory.

Tested distribution baseline:

- Playwright Python: 1.62.0 (Apache-2.0)
- Playwright Chromium revision: 1234
- Chrome for Testing: 151.0.7922.34, Windows x64
- matching Chrome Headless Shell, FFmpeg, and Playwright support binaries installed by Playwright 1.62.0

The Playwright browser bundle is installed hermetically with `PLAYWRIGHT_BROWSERS_PATH=0` before the PyInstaller build so the packaged application does not depend on a user- or machine-global Playwright browser cache. JobPilot does not add Google API keys, browser extensions, telemetry, or remote UI scripts.

The Chrome for Testing / Chromium-derived bundle contains Chromium open-source code and many third-party components governed by their own upstream licenses and notices. JobPilot does not relicense those components. The bundled browser retains its embedded open-source credits (`chrome://credits`), and Chromium source/license material is available from https://chromium.googlesource.com/chromium/src/ .

JobPilot's desktop shell uses the Evergreen Microsoft Edge WebView2 Runtime. Setup detects the documented WebView2 Runtime registration before installing JobPilot. If the Runtime is absent, setup downloads Microsoft's Evergreen Bootstrapper from the official Microsoft programmatic link `https://go.microsoft.com/fwlink/p/?LinkId=2124703`, requires a valid Microsoft Authenticode signature before execution, and invokes the documented silent install command. Microsoft documents the Runtime distribution options at https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution and provides the Runtime download page at https://developer.microsoft.com/microsoft-edge/webview2/ . Microsoft WebView2 terms and notices remain upstream obligations and are not replaced by this file.

This notice supplements `THIRD_PARTY_NOTICES.md`; it does not replace notices embedded in bundled browser/runtime components or licenses shipped by upstream projects.
