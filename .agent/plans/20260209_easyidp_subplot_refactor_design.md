# EasyPlantFieldID Subplot Refactor Design (EasyIDP Native)

## Context

This design replaces the current subplot core path with direct EasyIDP usage.
The current runtime has a custom `src/core/subplot_generator.py` and a GUI path that assumes
`GeoDataFrame` for vector preview and saving.

Validated goals:

- Remove `src/core` from the subplot runtime path.
- Let GUI call `easyidp.geotools.generate_subplots()` directly.
- Keep EasyIDP output (`idp.ROI`) as the primary geometry model.
- Save generated shapefiles via `ROI.save()`.
- Update UI to support EasyIDP `keep` parameter.
- Replace map vector loading path with `idp.ROI` + shapefile path support.
- One-time cleanup direction: no `GeoDataFrame` compatibility layer in map vector API.

## Decision Summary

### Chosen architecture

1. Use `idp.ROI` as the canonical geometry object in subplot workflow.
2. Use `idp.geotools.generate_subplots(...)` for both preview and final generation.
3. Refactor `MapCanvas.add_vector_layer()` to accept:
   - `idp.ROI`
   - shapefile path (internally loaded as `idp.ROI`)
4. Remove `geopandas` dependency from project runtime after map and tests are migrated.

### Why this direction

- It aligns with EasyIDP-native data flow and avoids dual data models.
- It simplifies persistence (`ROI.save`) and attribute consistency (`row`, `col`, `status`).
- It reduces conversion overhead and removes a heavy dependency (`geopandas`).
- It keeps subplot semantics centralized in EasyIDP instead of duplicated in local code.

## UI/Parameter Design

`Subplot` tab keeps the existing dual semantic modes and adds EasyIDP `keep`:

- Mode = Grid
  - Inputs: `row_num`, `col_num`, `x_interval`, `y_interval`, `keep`
- Mode = Size
  - Inputs: `width`, `height`, `x_interval`, `y_interval`, `keep`

`keep` dropdown values:

- `all`
- `touch`
- `inside`

Mapping rules:

- If mode is Grid, only pass `row_num`/`col_num`.
- If mode is Size, only pass `width`/`height`.
- Always pass `x_interval`, `y_interval`, `keep`.

This follows EasyIDP mutual exclusivity rules and avoids mixed-mode ambiguity.

## Data Flow

### Load boundary

1. User selects boundary shapefile.
2. GUI loads `boundary_roi = idp.ROI(shp_path)`.
3. Validate `len(boundary_roi) == 1`.
4. Show boundary through `MapCanvas.add_vector_layer(boundary_roi, "Boundary", ...)`.

### Auto preview

1. Read UI params.
2. Build EasyIDP call kwargs by mode.
3. Execute `generate_subplots(boundary_roi, ...)`.
4. Receive `subplots_roi`.
5. Show preview via `MapCanvas.add_vector_layer(subplots_roi, "Preview", ...)`.

### Final generation and save

1. Recompute with current params.
2. Save by `subplots_roi.save(target_shp_path, name_field="id")`.
3. Report success/failure in UI.

## MapCanvas Refactor Plan

Current map vector rendering already draws polyline arrays from geometry rings.
Refactor to remove `GeoDataFrame` assumptions:

- Input normalization:
  - If `str/Path` -> `idp.ROI(path)`
  - If `idp.ROI` -> use directly
  - Else -> reject with clear error
- Geometry extraction:
  - Iterate ROI polygons (`numpy` Nx2 or Nx3)
  - Use XY columns, append `NaN` separators
- Bounds:
  - Compute min/max from ROI coordinate arrays
  - Build map bounds object for zoom/rotation center logic
- Storage:
  - Keep ROI as layer data object (`'data': roi`)

This preserves existing paint path (`PlotCurveItem`) and layer management behavior.

## Error Handling

Guard-clause strategy in GUI flow:

- No boundary loaded -> warning and return.
- Invalid ROI count -> warning and return.
- Invalid parameter combination -> warning and return.
- EasyIDP generation exception -> error infobar with root cause.
- Save exception -> error infobar with save path context.

Errors remain user-readable while preserving detailed logs via `loguru`.

## Performance Considerations

Expected outcome: no major regression, likely improvement.

Reasons:

- Remove `gpd.read_file()` and `GeoDataFrame` object overhead.
- Avoid repeated model conversion between GDF and ROI.
- Draw path remains `numpy` arrays -> `PlotCurveItem`, which is already efficient.

Risk point:

- Rebuilding coordinate arrays on every tiny parameter change can add churn.

Mitigation:

- Cache per-layer flattened XY arrays and bounds.
- Regenerate only when source ROI changes.

## Migration Scope

Planned impacted files:

- `src/gui/tabs/subplot_generate.py`
- `src/gui/components/property_panel.py`
- `src/gui/components/map_canvas.py`
- `src/gui/resource/i18n/en_US.json` (and paired locale files if needed)
- `pyproject.toml`
- `tests/*` (subplot and map vector related)

Planned removals:

- `src/core/subplot_generator.py`
- `src/core/__init__.py` (or keep package empty only if other modules still required)

## Verification Plan

1. Unit tests for parameter mapping (grid/size/keep).
2. Unit tests for ROI output contract (`row`, `col`, `status` presence).
3. MapCanvas tests for ROI and shapefile path loading.
4. Manual GUI checks:
   - load boundary
   - toggle grid/size
   - keep mode behavior
   - preview refresh
   - save shapefile by `ROI.save`

Command baseline:

```bash
uv run pytest
```

## Notes

- Commit is intentionally not created in this step.
- If needed, a follow-up implementation plan can split work into small patches:
  - map canvas API refactor
  - subplot tab EasyIDP integration
  - UI keep parameter wiring
  - dependency/test cleanup
