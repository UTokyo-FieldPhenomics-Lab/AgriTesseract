# Layer Type Contract and Icon Fix Summary

## Background

- Issue: raster and vector layers in `LayerPanel` showed the same icon.
- Trigger path: `MapCanvas.sigLayerAdded` emitted title-case labels (`"Raster"`, `"Vector"`), while `LayerPanel.add_layer()` matched only lowercase (`"raster"`).
- Effect: raster branch did not match when title-case values arrived, so both types effectively followed the same icon path in practice.

## Root Cause

- Layer type was represented as free-form strings across multiple modules.
- The project had no single canonical layer type contract.
- Case normalization and source-of-truth constants were missing, which allowed silent divergence between producer and consumer.

## Implemented Fix (Stable Contract)

### 1) Added canonical layer type module

- New file: `src/gui/components/layer_types.py`
- Added:
  - `LayerType(StrEnum)` with canonical values: `raster`, `vector`
  - `normalize_layer_type()` to normalize incoming raw values and enforce canonical storage/logic

### 2) LayerPanel now consumes normalized type

- Updated: `src/gui/components/layer_panel.py`
- `add_layer()` now normalizes incoming `layer_type` before icon selection.
- Internal registry stores normalized canonical type value.

### 3) Replaced hard-coded emit strings with canonical constants

- Updated emit sites to use `LayerType.*.value`:
  - `src/gui/components/map_canvas.py`
  - `src/gui/tabs/rename_ids.py`
  - `src/gui/tabs/seedling_detect.py`
  - `src/utils/seedling_detect/preview_controller.py`

## Verification Evidence

- Added regression test in `tests/test_map_canvas_layer_order.py`:
  - `test_layer_panel_uses_distinct_icons_for_raster_and_vector`
  - Covers title-case and lowercase input paths.
  - Asserts raster and vector icon renderings are distinct.
- Command results:
  - `uv run pytest tests/test_map_canvas_layer_order.py::test_layer_panel_uses_distinct_icons_for_raster_and_vector` -> passed
  - `uv run pytest tests/test_map_canvas_layer_order.py` -> `4 passed`

## Future Stronger Encapsulation Plan

The current fix establishes a shared contract, but string transport in Qt signals can still allow accidental misuse. A stronger plan is listed below.

### Phase A: Typed signal payload adapter (low risk, incremental)

- Introduce `LayerAddedPayload` dataclass:
  - fields: `name: str`, `layer_type: LayerType`, `visible: bool = True`
- Keep existing signal signature for compatibility, but route all producers through one adapter function:
  - `emit_layer_added(name, layer_type, visible=True)`
  - Adapter normalizes and validates before emitting.
- Add warning logs for unknown raw labels at adapter boundary.

### Phase B: Single registration API (medium risk)

- Add one API on `MapCanvas` for all layer registration metadata writes, replacing direct mutation of `_layers` and `_layer_order` where practical.
- API responsibilities:
  - canonicalize layer type
  - enforce uniqueness/overwrite semantics
  - emit normalized layer-added event
- Benefit: avoids duplicated registration logic spread across tabs/controllers.

### Phase C: Strict mode and migration cleanup (optional hardening)

- Add strict validation mode (default on in tests): reject unknown layer type labels instead of silently defaulting.
- Remove remaining direct `sigLayerAdded.emit(...)` calls in feature modules.
- Add contract tests:
  - producer emits canonical payload
  - consumer receives only canonical enum/value
  - unknown type path behavior is explicit and tested

## Recommended Next Step

- Execute Phase A first as a small PR. It delivers immediate safety without broad refactor cost.
