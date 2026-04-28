from __future__ import annotations

from .base import BaseConverter


class Gen1ToGen2Converter(BaseConverter):
    source_generation = 1
    target_generation = 2
    mode = "time_capsule_gen1_gen2"
