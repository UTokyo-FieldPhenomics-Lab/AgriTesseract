"""Boundary helpers for Rename IDs input bundle."""

from __future__ import annotations

import geopandas as gpd
import numpy as np


def _validate_boundary(boundary_gdf: gpd.GeoDataFrame) -> None:
    """Validate boundary GeoDataFrame has usable polygon geometry.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        Boundary polygons.
    """
    if boundary_gdf is None or boundary_gdf.empty:
        raise ValueError("boundary data is empty")
    if boundary_gdf.geometry.is_empty.any():
        raise ValueError("boundary contains empty geometry")
    geom_types = set(boundary_gdf.geometry.geom_type.unique().tolist())
    allowed_types = {"Polygon", "MultiPolygon"}
    if not geom_types.issubset(allowed_types):
        raise ValueError("boundary geometry must be Polygon or MultiPolygon")


def align_boundary_crs(
    points_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Align boundary CRS to points CRS.

    Parameters
    ----------
    points_gdf : geopandas.GeoDataFrame
        Point geometries used as CRS anchor.
    boundary_gdf : geopandas.GeoDataFrame
        Boundary geometries to align.

    Returns
    -------
    tuple[geopandas.GeoDataFrame, geopandas.GeoDataFrame]
        Points copy and boundary converted to points CRS.
    """
    _validate_boundary(boundary_gdf)
    if points_gdf.crs is None:
        raise ValueError("points CRS is missing")
    if boundary_gdf.crs is None:
        raise ValueError("boundary CRS is missing")
    if points_gdf.crs == boundary_gdf.crs:
        return points_gdf.copy(), boundary_gdf.copy()
    return points_gdf.copy(), boundary_gdf.to_crs(points_gdf.crs)


def build_effective_mask(
    points_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
) -> np.ndarray:
    """Build boolean mask for points covered by boundary.

    Parameters
    ----------
    points_gdf : geopandas.GeoDataFrame
        Input points table.
    boundary_gdf : geopandas.GeoDataFrame
        Aligned polygon boundary table.

    Returns
    -------
    numpy.ndarray
        Boolean mask with shape ``(N,)`` aligned to points rows.
    """
    _validate_boundary(boundary_gdf)
    boundary_geom = boundary_gdf.union_all()
    mask_series = points_gdf.geometry.apply(boundary_geom.covers)
    return np.asarray(mask_series.to_numpy(), dtype=np.bool_)


def compute_boundary_axes(boundary_gdf: gpd.GeoDataFrame) -> dict[str, np.ndarray]:
    """Compute unit x/y axes from boundary minimum rotated rectangle.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        Polygon boundary geometries.

    Returns
    -------
    dict[str, numpy.ndarray]
        Axis vectors ``x_axis`` and ``y_axis`` with shape ``(2,)``.
    """
    _validate_boundary(boundary_gdf)
    boundary_geom = boundary_gdf.union_all()
    rectangle = boundary_geom.minimum_rotated_rectangle
    coord_array = np.asarray(rectangle.exterior.coords[:-1], dtype=float)
    if coord_array.shape[0] < 4:
        raise ValueError("boundary minimum rectangle is invalid")
    edge_array = np.roll(coord_array, -1, axis=0) - coord_array
    edge_len_array = np.linalg.norm(edge_array, axis=1)
    x_index = int(np.argmax(edge_len_array))
    y_index = int((x_index + 1) % edge_array.shape[0])
    x_axis = edge_array[x_index] / edge_len_array[x_index]
    y_axis = edge_array[y_index] / np.linalg.norm(edge_array[y_index])
    return {"x_axis": x_axis.astype(np.float64), "y_axis": y_axis.astype(np.float64)}
