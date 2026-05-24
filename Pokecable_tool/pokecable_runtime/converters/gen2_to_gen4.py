from __future__ import annotations

from .base import BaseConverter


class Gen2ToGen4Converter(BaseConverter):
    source_generation = 2
    target_generation = 4
    mode = "forward_transfer_to_gen4"
