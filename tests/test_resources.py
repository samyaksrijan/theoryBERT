import pytest

from theorybert.training import resources


@pytest.mark.parametrize("update, message", [
    ({"disk_free_gb": 2.9}, "disk"),
    ({"memory_free_percent": 7}, "memory"),
    ({"swap_used_gb": 3.6}, "swap"),
])
def test_guard_stops_before_resource_limits(tmp_path, monkeypatch, update, message):
    current = {"disk_free_gb": 8, "memory_free_percent": 50, "swap_used_gb": 2}
    monkeypatch.setattr(resources, "snapshot", lambda path: dict(current))
    guard = resources.ResourceGuard(tmp_path)
    current.update(update)
    with pytest.raises(RuntimeError, match=message):
        guard.check("training")
    assert (tmp_path / "resources.jsonl").is_file()


def test_guard_reserves_space_for_atomic_checkpoint_write(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "snapshot", lambda path: {"disk_free_gb": 3.5})
    guard = resources.ResourceGuard(tmp_path)
    with pytest.raises(RuntimeError, match="write reserve"):
        guard.check("checkpoint", reserve_gb=1.2)
