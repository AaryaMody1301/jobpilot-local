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
| llama.cpp | v0.4.0 / binary build b10809 | MIT; exact CPU/Vulkan Windows x64 archives are pinned below |
| Qwen3 4B GGUF | `ggml-org/Qwen3-4B-GGUF`, revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`, Q4_K_M | Apache-2.0; model weights are downloaded only after explicit user approval and are never committed to this repository |

Phase 2 pins the Tectonic Windows x64 MSVC archive `tectonic-0.17.0-x86_64-pc-windows-msvc.zip` to SHA-256 `f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f`. The application downloads it only after explicit user approval from the official Tectonic GitHub release and stores the installed executable plus integrity metadata in JobPilot's app-owned tool directory.

Tectonic's support cache can contain separately licensed TeX/LaTeX/font resources. Distribution packaging must enumerate and preserve the notices applicable to the exact cached/bundled content; Phase 2 does not commit or bundle that cache in Git.

Playwright-managed Chromium carries its own upstream licensing and notice obligations. The packaged distribution must include the relevant browser notices for the exact bundled revision.

## Phase 3 local-AI artifacts

JobPilot does not bundle or commit model weights. Its Phase 3 catalogue records exact download provenance and verifies content before use:

- llama.cpp CPU x64 archive: `llama-b10809-bin-win-cpu-x64.zip`, 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- llama.cpp Vulkan x64 archive: `llama-b10809-bin-win-vulkan-x64.zip`, 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`;
- Qwen3 4B Q4_K_M weight: `Qwen3-4B-Q4_K_M.gguf`, 2,497,280,640 bytes, SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`.

The Qwen3 GGUF is used as a text-only local model. JobPilot does not download or load a multimodal projection for it. Passing the controlled Phase 3 evaluation does not grant permission to fabricate resume facts and does not enable automatic tailoring; the separate Phase 4 five-resume human review gate still applies.

Every future runtime/model revision must receive a new catalogue record/install identity with source revision, license, exact checksum/size and evaluation evidence before use. A metadata update check may report newer upstream versions, but it never downloads or automatically trusts them.

## Reference repositories reviewed

The following projects are research inputs only. README claims are not treated as verified behavior and no code has been copied from them unless a later exact reuse entry says otherwise.

- `ggml-org/llama.cpp`
- `tectonic-typesetting/tectonic`
- `AbhishekMandapmalvi/AutoApply`
- `humancto/mr-jobs`
- `ATAboukhadra/job_finder`
- `speedyapply/JobSpy`

If code is reused later, the exact file/commit, governing license, modifications, and required attribution must be added here before merge.
