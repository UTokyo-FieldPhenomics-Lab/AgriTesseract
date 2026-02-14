"""Canonical layer type definitions and normalization utilities."""

from enum import StrEnum


class LayerType(StrEnum):
    """Supported layer categories used by map and layer panel."""

    RASTER = "raster"
    VECTOR = "vector"


_LAYER_TYPE_ALIASES: dict[str, LayerType] = {
    LayerType.RASTER.value: LayerType.RASTER,
    LayerType.VECTOR.value: LayerType.VECTOR,
}


def normalize_layer_type(raw_layer_type: str | LayerType | None) -> LayerType:
    """Normalize arbitrary layer type labels into canonical enum values.

    Parameters
    ----------
    raw_layer_type : str | LayerType | None
        Incoming layer type label from signal emitters or direct calls.

    Returns
    -------
    LayerType
        Canonical ``LayerType``. Unknown values fallback to ``VECTOR``.

    Examples
    --------
    >>> normalize_layer_type("Raster")
    <LayerType.RASTER: 'raster'>
    >>> normalize_layer_type("vector")
    <LayerType.VECTOR: 'vector'>
    """
    if isinstance(raw_layer_type, LayerType):
        return raw_layer_type

    label = str(raw_layer_type or "").strip().lower()
    return _LAYER_TYPE_ALIASES.get(label, LayerType.VECTOR)
