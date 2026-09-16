# Bundled browser notices

JobPilot Local Phase 9 distributions bundle only the Playwright-managed Chromium browser required by the application.

Tested distribution baseline:

- Playwright Python: 1.62.0 (Apache-2.0)
- Playwright Chromium revision: 1234
- Chrome for Testing: 151.0.7922.34, Windows x64

The browser bundle is installed hermetically with `PLAYWRIGHT_BROWSERS_PATH=0` before the PyInstaller build so the packaged application does not depend on a global browser installation. JobPilot does not add Google API keys, browser extensions, telemetry, or remote UI scripts.

Chromium/Chrome for Testing includes Chromium code under the Chromium BSD-style license and many third-party components under their respective licenses. The browser build retains its embedded open-source credits (`chrome://credits`). Chromium licensing information is published by the Chromium project at https://www.chromium.org/Home/chromium-security/ and source/license material is available from https://chromium.googlesource.com/chromium/src/.

This notice supplements `THIRD_PARTY_NOTICES.md`; it does not replace notices embedded in the bundled browser or licenses shipped by upstream components.
