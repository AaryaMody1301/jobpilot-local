from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


CATALOGUE_VERSION = "2026-09-10.1"


@dataclass(frozen=True, slots=True)
class RuntimeArtifact:
    id: str
    version: str
    build: str
    backend: Literal["cpu", "vulkan"]
    platform: str
    url: str
    sha256: str
    bytes: int
    archive_name: str
    executable_name: str = "llama-server.exe"
    license: str = "MIT"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    id: str
    display_name: str
    source_repo: str
    source_revision: str
    filename: str
    url: str
    sha256: str
    display_bytes: int
    quantization: str
    license: str
    tested_context_tokens: int
    min_total_ram_bytes: int
    preferred_total_ram_bytes: int
    tier: Literal["bootstrap", "preferred"]
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


RUNTIMES: tuple[RuntimeArtifact, ...] = (
    RuntimeArtifact(
        id="llama-b10809-win-cpu-x64",
        version="0.4.0",
        build="b10809",
        backend="cpu",
        platform="windows-x64",
        url="https://github.com/ggml-org/llama.cpp/releases/download/b10809/llama-b10809-bin-win-cpu-x64.zip",
        sha256="9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5",
        bytes=18_407_457,
        archive_name="llama-b10809-bin-win-cpu-x64.zip",
    ),
    RuntimeArtifact(
        id="llama-b10809-win-vulkan-x64",
        version="0.4.0",
        build="b10809",
        backend="vulkan",
        platform="windows-x64",
        url="https://github.com/ggml-org/llama.cpp/releases/download/b10809/llama-b10809-bin-win-vulkan-x64.zip",
        sha256="97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870",
        bytes=35_221_385,
        archive_name="llama-b10809-bin-win-vulkan-x64.zip",
    ),
)


MODELS: tuple[ModelArtifact, ...] = (
    ModelArtifact(
        id="qwen3.5-0.8b-q4_0",
        display_name="Qwen3.5 0.8B Q4_0",
        source_repo="ggml-org/Qwen3.5-0.8B-GGUF",
        source_revision="main@9447f74; content pinned by SHA-256",
        filename="Qwen3.5-0.8B-Q4_0.gguf",
        url="https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_0.gguf?download=true",
        sha256="57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
        display_bytes=563_000_000,
        quantization="Q4_0",
        license="Apache-2.0",
        tested_context_tokens=4096,
        min_total_ram_bytes=6 * 1024**3,
        preferred_total_ram_bytes=8 * 1024**3,
        tier="bootstrap",
        notes="Small Phase 3 compatibility/evaluation candidate; never auto-approved for tailoring solely because it installs.",
    ),
    ModelArtifact(
        id="qwen3-4b-q4_k_m",
        display_name="Qwen3 4B Q4_K_M",
        source_repo="ggml-org/Qwen3-4B-GGUF",
        source_revision="2f3b082b1356a6123f7ed71e65aea340da25d53c",
        filename="Qwen3-4B-Q4_K_M.gguf",
        url="https://huggingface.co/ggml-org/Qwen3-4B-GGUF/resolve/2f3b082b1356a6123f7ed71e65aea340da25d53c/Qwen3-4B-Q4_K_M.gguf?download=true",
        sha256="ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328",
        display_bytes=2_500_000_000,
        quantization="Q4_K_M",
        license="Apache-2.0",
        tested_context_tokens=4096,
        min_total_ram_bytes=12 * 1024**3,
        preferred_total_ram_bytes=16 * 1024**3,
        tier="preferred",
        notes="Preferred catalogue candidate when local resources allow; still requires device-local Phase 3 evaluation and later Phase 4 review gate.",
    ),
)

_RUNTIME_BY_ID = {item.id: item for item in RUNTIMES}
_MODEL_BY_ID = {item.id: item for item in MODELS}


def get_runtime(runtime_id: str) -> RuntimeArtifact:
    try:
        return _RUNTIME_BY_ID[runtime_id]
    except KeyError as exc:
        raise KeyError(f"unknown runtime catalogue id: {runtime_id}") from exc


def get_model(model_id: str) -> ModelArtifact:
    try:
        return _MODEL_BY_ID[model_id]
    except KeyError as exc:
        raise KeyError(f"unknown model catalogue id: {model_id}") from exc
