"""Dependency contract tests for runtime GIS stack.

This module locks expected runtime dependency behavior.
"""

from pathlib import Path
import tomllib


def test_runtime_dependencies_contract() -> None:
    """Ensure runtime dependencies include GeoPandas and exclude EasyIDP.

    Returns
    -------
    None

    Examples
    --------
    >>> test_runtime_dependencies_contract()
    """
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    assert any(dep.startswith("geopandas") for dep in deps)
    assert not any(dep.startswith("easyidp") for dep in deps)


def test_no_local_easyidp_uv_source() -> None:
    """Ensure uv source mapping no longer pins local EasyIDP.

    Returns
    -------
    None

    Examples
    --------
    >>> test_no_local_easyidp_uv_source()
    """
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    assert "easyidp" not in sources
