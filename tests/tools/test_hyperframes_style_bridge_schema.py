"""The HyperFrames style bridge must read playbook keys that actually exist.

Counterpart to tests/contracts/test_remotion_theme_playbook_keys.py on the
Remotion side: `VideoCompose._build_theme_from_playbook` reads
`typography.headings`, `color_palette.muted` and falls back from `surface` to
`background`, so the HyperFrames bridge has to agree with it. Regression
coverage for issue #306.
"""
from pathlib import Path

import pytest
import yaml

from lib.hyperframes_style_bridge import _motion_easing, style_bridge
from styles.playbook_loader import list_playbooks

STYLES_DIR = Path(__file__).resolve().parents[2] / "styles"
PLAYBOOK_NAMES = sorted(list_playbooks())

# identity.pace enum, per schemas/styles/playbook.schema.json
PACE_ENUM = ["slow", "deliberate", "moderate", "fast", "rapid"]


def _raw(name: str) -> dict:
    return yaml.safe_load((STYLES_DIR / f"{name}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", PLAYBOOK_NAMES)
def test_bridge_reads_real_schema_keys(name: str) -> None:
    """Each real playbook's own tokens must reach the emitted CSS vars."""
    pb = _raw(name)
    css, design = style_bridge(pb, None)

    headings = pb.get("typography", {}).get("headings", {})
    expect_font = headings.get("font") or headings.get("family")
    assert expect_font, f"{name}: playbook declares no typography.headings font"
    assert css["--font-heading"] == expect_font, (
        f"{name}: typography.headings was ignored (got {css['--font-heading']!r})"
    )

    palette = pb.get("visual_language", {}).get("color_palette", {})
    if palette.get("muted"):
        assert css["--color-muted"] == palette["muted"], (
            f"{name}: color_palette.muted was ignored"
        )
    expect_surface = palette.get("surface") or palette.get("background")
    if expect_surface:
        assert css["--color-surface"] == expect_surface, (
            f"{name}: color_palette.background not used as the surface fallback"
        )

    identity_name = pb.get("identity", {}).get("name")
    assert identity_name, f"{name}: playbook declares no identity.name"
    assert identity_name in design, f"{name}: identity.name missing from DESIGN.md"


def test_every_pace_value_maps_to_its_own_profile() -> None:
    """`deliberate` and `rapid` must not collapse into `moderate` (issue #306)."""
    profiles = {pace: _motion_easing({}, pace) for pace in PACE_ENUM}
    assert len(set(profiles.values())) == len(PACE_ENUM), (
        f"identity.pace values share a motion profile: {profiles}"
    )


def test_identity_pace_wins_over_legacy_motion_pace() -> None:
    """`pace` lives under `identity`; `motion.pace` stays supported, but loses."""
    assert _motion_easing({"pace": "slow"}, "fast") == _motion_easing({}, "fast")
    assert _motion_easing({"pace": "fast"}, None) == _motion_easing({}, "fast")
    assert _motion_easing({}, "unrecognized") == _motion_easing({}, "moderate")


def test_bridge_falls_back_when_playbook_missing() -> None:
    css, design = style_bridge(None, None)
    assert css["--font-heading"] and design
