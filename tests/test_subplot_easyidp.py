"""Tests for EasyIDP subplot integration helpers."""

from pathlib import Path

import easyidp as idp
import numpy as np
import pyproj
import pytest

from src.utils.subplot_generate.io import build_generate_kwargs, generate_and_save


def _make_boundary_roi() -> idp.ROI:
    """Create a single-polygon ROI boundary in meter CRS."""
    roi = idp.ROI()
    roi["field"] = np.array(
        [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0], [0.0, 0.0]]
    )
    roi.crs = pyproj.CRS.from_epsg(3857)
    return roi


def test_build_generate_kwargs_grid_mode() -> None:
    """Grid mode should map to row/col arguments only."""
    kwargs = build_generate_kwargs(
        mode_index=0,
        rows=4,
        cols=6,
        width=2.0,
        height=3.0,
        x_spacing=0.5,
        y_spacing=0.25,
        keep_mode="inside",
    )

    assert kwargs["row_num"] == 4
    assert kwargs["col_num"] == 6
    assert "width" not in kwargs
    assert "height" not in kwargs
    assert kwargs["keep"] == "inside"


def test_build_generate_kwargs_size_mode() -> None:
    """Size mode should map to width/height arguments only."""
    kwargs = build_generate_kwargs(
        mode_index=1,
        rows=4,
        cols=6,
        width=2.0,
        height=3.0,
        x_spacing=0.5,
        y_spacing=0.25,
        keep_mode="touch",
    )

    assert kwargs["width"] == pytest.approx(2.0)
    assert kwargs["height"] == pytest.approx(3.0)
    assert "row_num" not in kwargs
    assert "col_num" not in kwargs
    assert kwargs["keep"] == "touch"


def test_generate_and_save_with_roi_save(tmp_path: Path) -> None:
    """Generated ROI should be saved via ROI.save()."""
    boundary_roi = _make_boundary_roi()
    out_path = tmp_path / "subplots.shp"

    subplots = generate_and_save(
        boundary_roi=boundary_roi,
        mode_index=0,
        rows=2,
        cols=2,
        width=2.0,
        height=2.0,
        x_spacing=0.0,
        y_spacing=0.0,
        keep_mode="all",
        output_path=out_path,
    )

    assert isinstance(subplots, idp.ROI)
    assert len(subplots) == 4
    assert out_path.exists()


def test_generate_and_save_appends_shp_extension(tmp_path: Path) -> None:
    """Missing extension should be normalized to .shp."""
    boundary_roi = _make_boundary_roi()
    out_path_no_ext = tmp_path / "subplots_no_ext"

    generate_and_save(
        boundary_roi=boundary_roi,
        mode_index=0,
        rows=2,
        cols=2,
        width=2.0,
        height=2.0,
        x_spacing=0.0,
        y_spacing=0.0,
        keep_mode="all",
        output_path=out_path_no_ext,
    )

    assert (tmp_path / "subplots_no_ext.shp").exists()
