from __future__ import annotations

from .base import BaseConverter


class Gen2ToGen3Converter(BaseConverter):
    source_generation = 2
    target_generation = 3
    mode = "forward_transfer_to_gen3"
