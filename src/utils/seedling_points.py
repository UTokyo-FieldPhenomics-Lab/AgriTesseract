"""Point editing helpers for seedling detection results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class PointAction(str, Enum):
    """Supported point edit actions."""

    ADD = "add"
    MOVE = "move"
    DELETE = "delete"


@dataclass
class SeedlingPoint:
    """Seedling center point entity.

    Parameters
    ----------
    fid : int
        Unique point id.
    x : float
        Geo x coordinate.
    y : float
        Geo y coordinate.
    source : str
        Source tag, e.g. ``sam3`` or ``manual``.
    conf : float
        Confidence value in range ``[0, 1]``.
    """

    fid: int
    x: float
    y: float
    source: str
    conf: float


@dataclass
class _UndoItem:
    """Undo command payload for point edits."""

    action: PointAction
    before: SeedlingPoint | None
    after: SeedlingPoint | None


class SeedlingPointStore:
    """In-memory editable point store with undo support.

    Examples
    --------
    >>> store = SeedlingPointStore()
    >>> store.add_point(1.0, 2.0, source="sam3", conf=0.8)
    0
    >>> store.move_point(fid=0, x=2.0, y=3.0)
    True
    """

    def __init__(self) -> None:
        self.points: dict[int, SeedlingPoint] = {}
        self._next_fid: int = 0
        self._undo_stack: list[_UndoItem] = []

    def add_point(self, x: float, y: float, source: str, conf: float) -> int:
        """Add point and push undo command.

        Parameters
        ----------
        x, y : float
            Geo coordinate pair.
        source : str
            Source label.
        conf : float
            Confidence score.

        Returns
        -------
        int
            Created point id.
        """
        point = SeedlingPoint(fid=self._next_fid, x=x, y=y, source=source, conf=conf)
        self.points[point.fid] = point
        self._undo_stack.append(
            _UndoItem(action=PointAction.ADD, before=None, after=point)
        )
        self._next_fid += 1
        return point.fid

    def move_point(self, fid: int, x: float, y: float) -> bool:
        """Move point coordinate and record undo state."""
        point = self.points.get(fid)
        if point is None:
            return False
        before = SeedlingPoint(**point.__dict__)
        point.x = x
        point.y = y
        after = SeedlingPoint(**point.__dict__)
        self._undo_stack.append(
            _UndoItem(action=PointAction.MOVE, before=before, after=after)
        )
        return True

    def delete_point(self, fid: int) -> bool:
        """Delete point by fid and record undo command."""
        point = self.points.pop(fid, None)
        if point is None:
            return False
        self._undo_stack.append(
            _UndoItem(action=PointAction.DELETE, before=point, after=None)
        )
        return True

    def undo_last_action(self) -> PointAction | None:
        """Undo the last edit action.

        Returns
        -------
        PointAction | None
            Reverted action type, or ``None`` when stack empty.
        """
        if not self._undo_stack:
            return None
        item = self._undo_stack.pop()
        if item.action == PointAction.ADD and item.after is not None:
            self.points.pop(item.after.fid, None)
            return item.action
        if item.action == PointAction.DELETE and item.before is not None:
            self.points[item.before.fid] = item.before
            return item.action
        if item.action == PointAction.MOVE and item.before is not None:
            self.points[item.before.fid] = item.before
            return item.action
        return None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert points to DataFrame sorted by fid.

        Returns
        -------
        pandas.DataFrame
            Table with columns ``fid, x, y, source, conf``.
        """
        rows = [point.__dict__ for point in self.points.values()]
        if not rows:
            return pd.DataFrame(columns=["fid", "x", "y", "source", "conf"])
        result_df = pd.DataFrame(rows)
        result_df = result_df.sort_values(by="fid", ascending=True)
        return result_df[["fid", "x", "y", "source", "conf"]].reset_index(drop=True)
