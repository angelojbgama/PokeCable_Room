# PokeCable offline dependencies

This directory is the complete offline dependency bundle used by
`pokecable.sh`. The launcher does not run `apt`, `pip`, `ensurepip`, or any
network installer at runtime.

Current target:

- Device: R36S / ArkOS-compatible Linux
- Architecture: `aarch64`
- System Python: `3.13`
- Bundled Python packages:
  - `pygame 2.6.1`
- Bundled native library path:
  - `lib/aarch64-linux-gnu`

`pygame` includes native Python extensions, and the native libraries it needs
are bundled in `lib/aarch64-linux-gnu`. The launcher prepends this directory to
`LD_LIBRARY_PATH` and prepends `python/` to `PYTHONPATH` only when the device
matches the target above.

The bundle intentionally does not include core system libraries such as
`libc`, the dynamic loader, `libm`, `libgcc_s`, or `libstdc++`. Those should
come from ArkOS to avoid replacing the running system runtime.

If the bundle is missing or incompatible, PokeCable exits with a dependency
error. Fix the package contents instead of installing dependencies on the R36S.

Expected runtime contract:

- `python3` must exist on the R36S system.
- Every non-stdlib Python dependency must live in `dependence/python`.
- Every bundled native dependency required by those Python modules must live in
  `dependence/lib/aarch64-linux-gnu`.
- The app must still start with no internet access.
