"""Tests for seedling point editing helpers."""

from src.utils.seedling_detect.points import PointAction, SeedlingPointStore


def test_point_store_add_move_delete_and_undo() -> None:
    """Point store should support add/move/delete with undo."""
    store = SeedlingPointStore()

    fid0 = store.add_point(x=10.0, y=20.0, source="sam3", conf=0.9)
    assert fid0 == 0
    assert len(store.points) == 1

    moved = store.move_point(fid=0, x=11.5, y=22.5)
    assert moved is True
    assert store.points[0].x == 11.5
    assert store.points[0].y == 22.5

    deleted = store.delete_point(fid=0)
    assert deleted is True
    assert len(store.points) == 0

    assert store.undo_last_action() == PointAction.DELETE
    assert len(store.points) == 1
    assert store.points[0].x == 11.5

    assert store.undo_last_action() == PointAction.MOVE
    assert store.points[0].x == 10.0
    assert store.points[0].y == 20.0

    assert store.undo_last_action() == PointAction.ADD
    assert len(store.points) == 0


def test_point_store_export_dataframe_has_fid() -> None:
    """Dataframe export should include fid/id and point attributes."""
    store = SeedlingPointStore()
    store.add_point(x=1.0, y=2.0, source="manual", conf=1.0)
    store.add_point(x=3.0, y=4.0, source="sam3", conf=0.7)

    df = store.to_dataframe()
    assert list(df.columns) == ["fid", "x", "y", "source", "conf"]
    assert df["fid"].tolist() == [0, 1]
