# Third-party notices

This file records dependencies and reference projects reviewed for `jobpilot-local`. Project implementation code is original unless an exact reuse entry is added below.

## Runtime and build dependencies

| Component | Current baseline | License / source note |
| --- | --- | --- |
| Python | 3.13.15 | Python Software Foundation License |
| pywebview | 6.2.1 | BSD-3-Clause |
| Playwright Python | 1.62.0 | Apache-2.0 |
| psutil | 7.2.2 | BSD-3-Clause |
| pypdf | 6.18.0 | BSD-3-Clause |
| pytest | 9.1.1 | MIT |
| PyInstaller | 6.22.2 | GPL-2.0-or-later with the PyInstaller bootloader exception |
| Tectonic | 0.17.0 app-managed Windows x64 binary | MIT for Tectonic; support files derived from TeX Live carry their own upstream licenses and notices that must remain attributable in distribution |
| llama.cpp | production build not pinned until Phase 3 evaluation | MIT; exact tested build/checksum must be recorded before distribution |

Phase 2 pins the Tectonic Windows x64 MSVC archive `tectonic-0.17.0-x86_64-pc-windows-msvc.zip` to SHA-256 `f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f`. The application downloads it only after explicit user approval from the official Tectonic GitHub release and stores the installed executable plus integrity metadata in JobPilot's app-owned tool directory.

Tectonic's support cache can contain separately licensed TeX/LaTeX/font resources. Distribution packaging must enumerate and preserve the notices applicable to the exact cached/bundled content; Phase 2 does not commit or bundle that cache in Git.

Playwright-managed Chromium carries its own upstream licensing and notice obligations. The packaged distribution must include the relevant browser notices for the exact bundled revision.

Model weights are not part of the repository. Every model catalogue entry must record source, license, checksum, context settings, and evaluation result before the application may use it.

## Reference repositories reviewed

The following projects are research inputs only. README claims are not treated as verified behavior and no code has been copied from them unless a later exact reuse entry says otherwise.

- `ggml-org/llama.cpp`
- `tectonic-typesetting/tectonic`
- `AbhishekMandapmalvi/AutoApply`
- `humancto/mr-jobs`
- `ATAboukhadra/job_finder`
- `speedyapply/JobSpy`

If code is reused later, the exact file/commit, governing license, modifications, and required attribution must be added here before merge.
