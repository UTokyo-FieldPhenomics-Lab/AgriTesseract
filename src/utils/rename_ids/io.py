"""Input IO helpers for Rename IDs tab."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd


def load_points_data(source: str | dict) -> gpd.GeoDataFrame:
    """Load input points from filepath or object bundle.

    Parameters
    ----------
    source : str | dict
        Input source path or object bundle that contains ``points_gdf``.

    Returns
    -------
    geopandas.GeoDataFrame
        Loaded points dataframe.

    Examples
    --------
    >>> gdf = load_points_data("/tmp/points.shp")
    >>> isinstance(gdf, gpd.GeoDataFrame)
    True
    """
    if isinstance(source, str):
        return gpd.read_file(Path(source))
    if isinstance(source, dict) and isinstance(
        source.get("points_gdf"), gpd.GeoDataFrame
    ):
        return source["points_gdf"].copy()
    raise TypeError("source must be shapefile path or bundle with points_gdf")


def normalize_input_points(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    """Normalize points GeoDataFrame for RenameInputBundle contract.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Raw points dataframe where geometry must be Point.

    Returns
    -------
    tuple[geopandas.GeoDataFrame, dict]
        Normalized dataframe and metadata dict with id/crs details.

    Examples
    --------
    >>> out_gdf, meta = normalize_input_points(gdf)
    >>> "fid" in out_gdf.columns
    True
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("gdf must be a GeoDataFrame")
    if gdf.empty:
        raise ValueError("points data is empty")
    geom_type_series = gdf.geometry.geom_type
    if not bool((geom_type_series == "Point").all()):
        raise ValueError("points geometry must contain Point only")

    normalized_gdf = gdf.copy()
    id_field = "fid"
    if id_field not in normalized_gdf.columns or normalized_gdf[id_field].isna().any():
        normalized_gdf[id_field] = list(range(len(normalized_gdf)))
    normalized_gdf[id_field] = normalized_gdf[id_field].astype(int)

    core_columns = [id_field]
    extra_columns = [
        col for col in normalized_gdf.columns if col not in (id_field, "geometry")
    ]
    normalized_gdf = normalized_gdf[core_columns + extra_columns + ["geometry"]]

    crs_wkt = None
    if normalized_gdf.crs is not None:
        crs_wkt = normalized_gdf.crs.to_wkt()
    points_meta = {"id_field": id_field, "crs_wkt": crs_wkt}
    return normalized_gdf, points_meta
