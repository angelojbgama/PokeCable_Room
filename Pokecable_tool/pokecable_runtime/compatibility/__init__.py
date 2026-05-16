from .matrix import get_trade_mode, is_cross_generation, supported_modes_for_generation
from .report import CompatibilityReport
from .rules import build_compatibility_report

__all__ = [
    "CompatibilityReport",
    "build_compatibility_report",
    "get_trade_mode",
    "is_cross_generation",
    "supported_modes_for_generation",
]
