from __future__ import annotations

from app.sprite_service import resolve_sprite_path


def test_sprite_service_resolves_local_pixel_sprite_by_name() -> None:
    path = resolve_sprite_path(1, "pikachu", "front")

    assert path is not None
    assert path.name == "25.png"
    assert path.exists()


def test_sprite_service_rejects_missing_pose_without_remote_fallback() -> None:
    assert resolve_sprite_path(1, "pikachu", "back") is None
