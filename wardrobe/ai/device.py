"""
设备检测 + 资源感知
- Mac Apple Silicon: MPS + mlx_lm
- NVIDIA: CUDA
- Linux x86 CPU only: CPU + transformers
- 内存不足时自动禁用某些模块
"""

import os
import platform
import shutil
import sys


def get_torch_device() -> str:
    """为 PyTorch 模型选择设备。"""
    try:
        import torch
    except ImportError:
        return "cpu"

    if sys.platform == "darwin" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def is_apple_silicon() -> bool:
    return sys.platform == "darwin" and platform.machine() in ("arm64", "arm64e")


def has_mlx() -> bool:
    if not is_apple_silicon():
        return False
    try:
        import mlx.core  # noqa: F401
        import mlx_lm  # noqa: F401
        return True
    except ImportError:
        return False


def get_models_dir() -> str:
    return os.environ.get("WARDROBE_MODELS_DIR", os.path.expanduser("~/wardrobe_models"))


def get_fashion_clip_dir() -> str:
    return os.environ.get(
        "FASHION_CLIP_DIR", os.path.join(get_models_dir(), "marqo-fashionCLIP")
    )


def get_llm_dir() -> str:
    """LLM 模型目录。
    - Mac: 默认指向 Qwen3-4B-Thinking MLX 版
    - Linux/Windows: 默认指向 Qwen2.5-0.5B safetensors
    """
    env = os.environ.get("LLM_MODEL_DIR")
    if env:
        return env
    base = get_models_dir()
    if is_apple_silicon():
        return os.path.join(base, "Qwen3-4B-Thinking-MLX-4bit")
    return os.path.join(base, "Qwen2.5-0.5B")


def get_available_memory_mb() -> int | None:
    """获取系统可用内存 (MB)。失败返回 None。"""
    try:
        if sys.platform == "darwin":
            out = subprocess_output(["vm_stat"])
            # Parse "Pages free:      12345."
            for line in out.splitlines():
                if "Pages free" in line:
                    pages = int(line.split()[-1].rstrip("."))
                    return pages * 4 // 1024  # 4KB pages
        elif sys.platform.startswith("linux"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) // 1024
        elif sys.platform == "win32":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullAvailPhys // (1024 * 1024)
    except Exception:
        return None
    return None


def subprocess_output(cmd: list[str]) -> str:
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout


def can_fit_visual(min_mb: int = 700) -> bool:
    """检查可用内存是否够装 FashionCLIP。"""
    avail = get_available_memory_mb()
    if avail is None:
        return True  # 不知道就允许
    return avail >= min_mb


def can_fit_llm(min_mb: int = 1100) -> bool:
    """检查可用内存是否够装 LLM。"""
    avail = get_available_memory_mb()
    if avail is None:
        return True
    return avail >= min_mb


def disk_free_mb(path: str = "/") -> int | None:
    try:
        u = shutil.disk_usage(path)
        return u.free // (1024 * 1024)
    except Exception:
        return None
