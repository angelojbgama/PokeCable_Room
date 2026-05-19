# PokeCable offline dependencies

This directory is loaded by `pokecable.sh` before system Python packages and
native libraries.

Current target:

- Device: R36S / ArkOS-compatible Linux
- Architecture: `aarch64`
- Python: `3.13`
- Bundled Python packages:
  - `pygame 2.6.1`
  - `websockets 15.0.1`
- Bundled native library path:
  - `lib/aarch64-linux-gnu`

`websockets` is mostly self-contained. `pygame` includes native Python
extensions, and the native libraries it needs are bundled in
`lib/aarch64-linux-gnu`. The launcher prepends this directory to
`LD_LIBRARY_PATH` only when the device matches the target above.

The bundle intentionally does not include core system libraries such as
`libc`, the dynamic loader, `libm`, `libgcc_s`, or `libstdc++`. Those should
come from ArkOS to avoid replacing the running system runtime.

Online installs are disabled by default. To opt in explicitly:

```sh
POKECABLE_ALLOW_ONLINE_INSTALL=1 ./pokecable.sh
```
