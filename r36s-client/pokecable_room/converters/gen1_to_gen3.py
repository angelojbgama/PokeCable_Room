from __future__ import annotations

from .base import BaseConverter


class Gen1ToGen3Converter(BaseConverter):
    source_generation = 1
    target_generation = 3
    mode = "forward_transfer_to_gen3"
