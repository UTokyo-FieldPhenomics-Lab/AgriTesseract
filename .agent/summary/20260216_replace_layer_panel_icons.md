# Replace Layer Panel Icons with Material Design Icons

## Summary
Replaced Fluent Icons for "Fit Width" and "Fit Height" actions in the Layer Panel with Material Design Icons using `qtawesome`.

## Changes
- Modified `src/gui/components/layer_panel.py`:
  - Imported `qtawesome` as `qta`.
  - Updated `_fit_width_icon` to use `mdi6.arrow-expand-horizontal`.
  - Updated `_fit_height_icon` to use `mdi6.arrow-expand-vertical`.

## Rationale
- The user requested specific Material Design Icons to replace the previous Fluent Icons (`CareDownSolid` and `CareRightSolid`) which were used for fit width/height actions.

## Verification
- Verified `qtawesome` dependency is present in `pyproject.toml`.
- Updated code to use `qta.icon()` for retrieving the requested icons.
