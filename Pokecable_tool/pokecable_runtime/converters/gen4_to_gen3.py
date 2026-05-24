from __future__ import annotations

from .base import BaseConverter


class Gen4ToGen3Converter(BaseConverter):
    source_generation = 4
    target_generation = 3
    mode = "legacy_downconvert_experimental"
