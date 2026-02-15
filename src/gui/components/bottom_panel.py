"""Bottom panel host components for map diagnostics."""

from __future__ import annotations

from typing import Dict, Optional

import darkdetect
import numpy as np
import pyqtgraph as pg
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import Theme

from src.gui.config import cfg


def _plot_theme_palette(is_dark: bool) -> dict[str, str]:
    """Return plot color palette for current theme.

    Parameters
    ----------
    is_dark : bool
        Whether current UI theme is dark.

    Returns
    -------
    dict[str, str]
        Color tokens for plot background and axis foreground.
    """
    if is_dark:
        return {
            "background": "#272727",
            "axis": "#D0D0D0",
            "curve": "#35C759",
            "peak": "#FF9F1A",
            "threshold": "#FF453A",
        }
    return {
        "background": "#FFFFFF",
        "axis": "#404040",
        "curve": "#2B8A3E",
        "peak": "#FF7F0E",
        "threshold": "#E03131",
    }


class BottomPanelHost(QWidget):
    """Host widget for switchable bottom panels.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget for Qt ownership.

    Notes
    -----
    The host keeps a registry of named panel widgets and exposes
    show/hide/switch APIs used by ``MapComponent``.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._panels: Dict[str, QWidget] = {}
        self._current_name: Optional[str] = None
        self._stack = QStackedWidget(self)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._stack)
        self._stack.show()

    def register_panel(self, name: str, panel: QWidget) -> bool:
        """Register one panel into host.

        Parameters
        ----------
        name : str
            Unique panel identifier.
        panel : QWidget
            Panel widget instance.

        Returns
        -------
        bool
            ``True`` when registered, ``False`` on invalid input or duplicate name.
        """
        if not name or panel is None or name in self._panels:
            return False
        self._panels[name] = panel
        self._stack.addWidget(panel)
        return True

    def unregister_panel(self, name: str) -> bool:
        """Unregister one panel by name.

        Parameters
        ----------
        name : str
            Existing panel identifier.

        Returns
        -------
        bool
            ``True`` when removed, ``False`` when panel does not exist.
        """
        panel = self._panels.pop(name, None)
        if panel is None:
            return False
        self._stack.removeWidget(panel)
        panel.setParent(None)
        if self._current_name == name:
            self._current_name = None
            self.hide()
        return True

    def show_panel(self, name: str) -> bool:
        """Show target panel and switch active content.

        Parameters
        ----------
        name : str
            Registered panel identifier.

        Returns
        -------
        bool
            ``True`` when switched successfully, ``False`` when missing.
        """
        panel = self._panels.get(name)
        if panel is None:
            return False
        self._stack.setCurrentWidget(panel)
        self._stack.show()
        self._current_name = name
        self.show()
        return True

    def hide_panel(self) -> None:
        """Hide panel content while keeping host container available."""
        self._stack.hide()

    def current_panel_name(self) -> Optional[str]:
        """Return current panel name.

        Returns
        -------
        str or None
            Active panel name. ``None`` when no panel has been shown.
        """
        return self._current_name


class BottomPanelFigure(QWidget):
    """Generic single-plot figure panel for bottom diagnostics.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget for Qt ownership.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.plot_widget = pg.PlotWidget(self)
        self.curve_item = self.plot_widget.plot(
            [], [], pen=pg.mkPen("#2B8A3E", width=2)
        )
        self.peaks_item = self.plot_widget.plot(
            [],
            [],
            pen=None,
            symbol="o",
            symbolSize=7,
            symbolBrush=pg.mkBrush(255, 127, 14, 180),
            symbolPen=pg.mkPen("#FF7F0E", width=1),
        )
        self.threshold_item: pg.InfiniteLine | None = None
        self._init_ui()
        self._apply_theme()
        cfg.themeChanged.connect(self._apply_theme)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setClipToView(True)
        layout.addWidget(self.plot_widget)

    def _is_dark_theme(self) -> bool:
        """Return whether current app theme is dark."""
        theme = cfg.themeMode.value
        if theme == Theme.AUTO:
            return bool(darkdetect.isDark())
        return theme == Theme.DARK

    def _apply_theme(self) -> None:
        """Apply plot colors to match app light/dark themes."""
        palette = _plot_theme_palette(self._is_dark_theme())
        self.plot_widget.setBackground(QColor(palette["background"]))
        axis_pen = pg.mkPen(color=palette["axis"], width=1)
        for axis_name in ("left", "bottom"):
            axis_item = self.plot_widget.getPlotItem().getAxis(axis_name)
            axis_item.setPen(axis_pen)
            axis_item.setTextPen(axis_pen)
        self.curve_item.setPen(pg.mkPen(color=palette["curve"], width=2))
        self.peaks_item.setSymbolPen(pg.mkPen(color=palette["peak"], width=1))
        self.peaks_item.setSymbolBrush(pg.mkBrush(palette["peak"]))
        if self.threshold_item is not None:
            self.threshold_item.setPen(pg.mkPen(color=palette["threshold"], width=1))

    def set_density_curve(self, x_bins: np.ndarray, counts: np.ndarray) -> None:
        """Set density curve data.

        Parameters
        ----------
        x_bins : numpy.ndarray
            X coordinates with shape ``(M,)`` and dtype ``float64``.
        counts : numpy.ndarray
            Density counts with shape ``(M,)`` and integer dtype.
        """
        self.curve_item.setData(x=x_bins, y=counts)

    def set_peaks(self, peak_x: np.ndarray, peak_h: np.ndarray) -> None:
        """Set peak marker points.

        Parameters
        ----------
        peak_x : numpy.ndarray
            Peak x coordinates with shape ``(K,)`` and dtype ``float64``.
        peak_h : numpy.ndarray
            Peak heights with shape ``(K,)`` and dtype ``float64``.
        """
        self.peaks_item.setData(x=peak_x, y=peak_h)

    def set_threshold_line(self, value: float | None) -> None:
        """Show or clear one horizontal threshold line."""
        if self.threshold_item is not None:
            self.plot_widget.removeItem(self.threshold_item)
            self.threshold_item = None
        if value is None:
            return
        line = pg.InfiniteLine(
            pos=float(value),
            angle=0,
            pen=pg.mkPen(
                color=_plot_theme_palette(self._is_dark_theme())["threshold"],
                width=1,
            ),
        )
        self.plot_widget.addItem(line)
        self.threshold_item = line

    def clear(self) -> None:
        """Clear all line, marker and threshold visuals."""
        self.curve_item.setData([], [])
        self.peaks_item.setData([], [])
        self.set_threshold_line(None)

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """Set plot visible x-range.

        Parameters
        ----------
        x_min : float
            Lower x bound.
        x_max : float
            Upper x bound.
        """
        self.plot_widget.getViewBox().setXRange(
            float(x_min),
            float(x_max),
            padding=0.0,
        )
