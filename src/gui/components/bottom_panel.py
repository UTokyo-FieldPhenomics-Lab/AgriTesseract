"""Bottom panel host components for map diagnostics."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget


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
        self.hide()

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
        self._current_name = name
        self.show()
        return True

    def hide_panel(self) -> None:
        """Hide host while keeping registered panels alive."""
        self.hide()

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

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setClipToView(True)
        layout.addWidget(self.plot_widget)

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
            pen=pg.mkPen(color="#E03131", width=1),
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
        self.plot_widget.setXRange(float(x_min), float(x_max), padding=0.0)
