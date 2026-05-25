"""Thin Python wrapper around libmgba (via ctypes) + tiny C wrapper for function-pointer calls.

Requires:
  - libmgba0.10t64 (apt install libmgba-dev for headers; runtime comes with the package)
  - mgba_wrapper.so built locally (run `make` in this folder, or see README)
"""
from __future__ import annotations

import ctypes
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_WRAPPER_SO = _THIS_DIR / "mgba_wrapper.so"


class LibMGBA:
    def __init__(self):
        # Try multiple library names (Debian/Ubuntu variants)
        for name in ("libmgba.so.0.10", "libmgba.so", "libmgba.so.0"):
            try:
                self.L = ctypes.CDLL(name, mode=ctypes.RTLD_GLOBAL)
                break
            except OSError:
                continue
        else:
            raise OSError("libmgba.so not found. Install with `sudo apt install libmgba-dev`.")
        if not _WRAPPER_SO.exists():
            raise OSError(
                f"{_WRAPPER_SO} not built. Run:\n"
                f"  cd {_THIS_DIR}\n"
                f"  gcc -shared -fPIC -O2 mgba_wrapper.c -I/usr/include -lmgba -o mgba_wrapper.so"
            )
        self.W = ctypes.CDLL(str(_WRAPPER_SO), mode=ctypes.RTLD_GLOBAL)
        self._bind_signatures()
        self.W.wrapper_silence_log()  # quiet mGBA logs

    def _bind_signatures(self):
        L, W = self.L, self.W
        L.mCoreFind.argtypes = [ctypes.c_char_p]; L.mCoreFind.restype = ctypes.c_void_p
        L.mCoreInitConfig.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; L.mCoreInitConfig.restype = None
        L.mCoreLoadFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; L.mCoreLoadFile.restype = ctypes.c_bool
        L.mCoreAutoloadSave.argtypes = [ctypes.c_void_p]; L.mCoreAutoloadSave.restype = ctypes.c_bool
        L.mCoreGetMemoryBlock.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_size_t)]
        L.mCoreGetMemoryBlock.restype = ctypes.c_void_p
        W.wrapper_init.argtypes = [ctypes.c_void_p]; W.wrapper_init.restype = ctypes.c_bool
        W.wrapper_deinit.argtypes = [ctypes.c_void_p]; W.wrapper_deinit.restype = None
        W.wrapper_reset.argtypes = [ctypes.c_void_p]; W.wrapper_reset.restype = None
        W.wrapper_run_frame.argtypes = [ctypes.c_void_p]; W.wrapper_run_frame.restype = None
        W.wrapper_read8.argtypes = [ctypes.c_void_p, ctypes.c_uint32]; W.wrapper_read8.restype = ctypes.c_uint8
        W.wrapper_silence_log.argtypes = []; W.wrapper_silence_log.restype = None


class MGBASession:
    """High-level session that owns a core pointer and exposes memory access."""

    def __init__(self, libmgba: LibMGBA, rom_path: Path):
        self.lib = libmgba
        self.rom_path = Path(rom_path)
        self.core = self.lib.L.mCoreFind(str(self.rom_path).encode())
        if not self.core:
            raise RuntimeError(f"mCoreFind failed for {self.rom_path}")
        if not self.lib.W.wrapper_init(self.core):
            raise RuntimeError("wrapper_init failed")
        self.lib.L.mCoreInitConfig(self.core, None)
        if not self.lib.L.mCoreLoadFile(self.core, str(self.rom_path).encode()):
            raise RuntimeError("mCoreLoadFile failed")
        self.lib.L.mCoreAutoloadSave(self.core)
        self.lib.W.wrapper_reset(self.core)

    def run_frames(self, n: int) -> None:
        for _ in range(n):
            self.lib.W.wrapper_run_frame(self.core)

    def read_block(self, start_addr: int) -> bytes | None:
        size = ctypes.c_size_t(0)
        ptr = self.lib.L.mCoreGetMemoryBlock(self.core, start_addr, ctypes.byref(size))
        if not ptr or size.value == 0:
            return None
        buf = (ctypes.c_uint8 * size.value).from_address(ptr)
        return bytes(buf)

    def read8(self, addr: int) -> int:
        return self.lib.W.wrapper_read8(self.core, addr)

    def close(self) -> None:
        if self.core:
            self.lib.W.wrapper_deinit(self.core)
            self.core = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
