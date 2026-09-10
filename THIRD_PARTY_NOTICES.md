# Third-party notices

This file records dependencies and reference projects reviewed for `jobpilot-local`. Phase 0 contains original implementation code; no source code from the reference job-automation repositories listed below has been copied.

## Runtime and build dependencies

| Component | Phase 0 baseline | License / source note |
| --- | --- | --- |
| Python | 3.13.15 | Python Software Foundation License |
| pywebview | 6.2.1 | BSD-3-Clause |
| Playwright Python | 1.62.0 | Apache-2.0 |
| psutil | 7.2.2 | BSD-3-Clause |
| pypdf | 6.18.0 | BSD-3-Clause |
| pytest | 9.1.1 | MIT |
| PyInstaller | 6.22.2 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| Tectonic | 0.17.0 candidate external binary | MIT for Tectonic; bundled TeX-derived elements carry additional licenses that must remain attributable in distribution |
| llama.cpp | production build not pinned until Phase 3 evaluation | MIT; exact tested build/checksum must be recorded before distribution |

Playwright-managed Chromium carries its own upstream licensing and notice obligations. The packaged distribution must include the relevant browser notices for the exact bundled revision.

Model weights are not part of the repository. Every model catalogue entry must record source, license, checksum, context settings, and evaluation result before the application may use it.

## Reference repositories reviewed

The following projects are research inputs only. README claims are not treated as verified behavior and no code has been copied in Phase 0.

- `ggml-org/llama.cpp`
- `tectonic-typesetting/tectonic`
- `AbhishekMandapmalvi/AutoApply`
- `humancto/mr-jobs`
- `ATAboukhadra/job_finder`
- `speedyapply/JobSpy`

If code is reused later, the exact file/commit, governing license, modifications, and required attribution must be added here before merge.
