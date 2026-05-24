from __future__ import annotations

from .base import BaseConverter


class Gen3ToGen4Converter(BaseConverter):
    source_generation = 3
    target_generation = 4
    mode = "forward_transfer_to_gen4"
