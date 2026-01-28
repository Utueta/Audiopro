#"""
# Audiopro v0.3.1
# - Handles runtime resource telemetry (CPU/RAM/Disk/GPU) and WAL growth monitoring.
#"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psutil


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    gpu_name: Optional[str]
    gpu_util_percent: Optional[float]
    vram_used_mb: Optional[float]
    vram_total_mb: Optional[float]
    sqlite_wal_bytes: Optional[int]


_DISK_IO_LAST: Optional[psutil._common.sdiskio] = None
_DISK_IO_LAST_TS: Optional[float] = None


def _bytes_to_gb(b: float) -> float:
    return float(b) / (1024.0 ** 3)


def _bytes_to_mb(b: float) -> float:
    return float(b) / (1024.0 ** 2)


def get_sqlite_wal_size_bytes(db_path: str) -> int:
    wal_path = db_path + "-wal"
    try:
        return int(os.path.getsize(wal_path))
    except OSError:
        return 0


def _nvidia_smi_query() -> Dict[str, Any]:
    """NVIDIA GPU telemetry via nvidia-smi (if available)."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.5,
        ).strip()
        if not out:
            return {}
        # Single-GPU first line; multi-GPU choose index 0 for now
        line = out.splitlines()[0]
        name, util, mem_used, mem_total = [x.strip() for x in line.split(",")]
        return {
            "gpu_name": name,
            "gpu_util_percent": float(util),
            "vram_used_mb": float(mem_used),
            "vram_total_mb": float(mem_total),
        }
    except Exception:
        return {}


def get_resource_snapshot(*, db_path: str | None = None) -> ResourceSnapshot:
    """Returns a point-in-time snapshot for UI and logs."""
    global _DISK_IO_LAST, _DISK_IO_LAST_TS

    cpu = float(psutil.cpu_percent(interval=None))
    vm = psutil.virtual_memory()

    import time
    now = time.time()
    io = psutil.disk_io_counters() or None
    read_mb_s = 0.0
    write_mb_s = 0.0
    if io is not None and _DISK_IO_LAST is not None and _DISK_IO_LAST_TS is not None:
        dt = max(1e-6, now - _DISK_IO_LAST_TS)
        read_mb_s = _bytes_to_mb(io.read_bytes - _DISK_IO_LAST.read_bytes) / dt
        write_mb_s = _bytes_to_mb(io.write_bytes - _DISK_IO_LAST.write_bytes) / dt
    if io is not None:
        _DISK_IO_LAST = io
        _DISK_IO_LAST_TS = now

    gpu = _nvidia_smi_query()

    wal = None
    if db_path:
        wal = get_sqlite_wal_size_bytes(db_path)

    return ResourceSnapshot(
        cpu_percent=cpu,
        ram_used_gb=_bytes_to_gb(vm.used),
        ram_total_gb=_bytes_to_gb(vm.total),
        disk_read_mb_s=float(read_mb_s),
        disk_write_mb_s=float(write_mb_s),
        gpu_name=gpu.get("gpu_name"),
        gpu_util_percent=gpu.get("gpu_util_percent"),
        vram_used_mb=gpu.get("vram_used_mb"),
        vram_total_mb=gpu.get("vram_total_mb"),
        sqlite_wal_bytes=wal,
    )


# Planned / Deferred:
# - GPU/VRAM monitoring for AMD and Intel GPUs
# - OpenCL and ROCM support
