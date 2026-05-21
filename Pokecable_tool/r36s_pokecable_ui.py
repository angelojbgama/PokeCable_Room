#!/usr/bin/env python3
"""Compatibility shim for the legacy R36S UI entrypoint."""

from __future__ import annotations

import sys

from frontend.app import ERROR_LOG, main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        print(f"\nErro fatal. Veja {ERROR_LOG}.", file=sys.stderr)
        raise
