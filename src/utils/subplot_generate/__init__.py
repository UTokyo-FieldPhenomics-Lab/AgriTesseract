"""Subplot generation submodule for EasyIDP integration.

Re-exports public API from io module.
"""

from src.utils.subplot_generate.io import (
    build_generate_kwargs,
    calculate_optimal_rotation,
    generate_and_save,
    generate_subplots_roi,
    load_boundary_roi,
)

__all__ = [
    "build_generate_kwargs",
    "calculate_optimal_rotation",
    "generate_and_save",
    "generate_subplots_roi",
    "load_boundary_roi",
]
