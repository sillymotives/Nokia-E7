#!/usr/bin/env python3
"""Offline IAUpdate 2.1.0 *source-rule illustrations* using invented candidates.

No network calls, handset access, ROM changes, update creation, or package
installation. Never accepts actual phone records. No claim of complete IAUpdate
engine emulation or Belle 2.2.0 acceptance. All examples are synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json

Version = tuple[int, int, int]
PlatformVersion = tuple[int, int]
PACKAGES = frozenset({"SA", "SP", "PU", "SERVICE_PACK", "WIDGET"})
IMPORTANCES = frozenset({"normal", "recommended", "critical", "mandatory", "hidden"})
DEPENDENCY_STATES = frozenset({"passed", "failed", "unknown"})


@dataclass(frozen=True)
class UpgradeBase:
    """Whether a same-UID installed component satisfies an upgrade range."""
    same_uid: bool
    installed: Version | None
    floor: Version
    roof: Version


@dataclass(frozen=True)
class EmbeddedComponent:
    """Installed component that might be downgraded by embedded content."""
    installed: Version | None
    embedded_version_roof: Version


@dataclass(frozen=True)
class Candidate:
    """Invented test scenario; not a full Symbian/NCD node."""
    label: str
    version: Version = (2, 0, 0)
    installed: Version | None = None
    package_type: str = "SA"
    importance: str = "normal"
    duplicate: bool = False
    platform: str | None = "S60"
    device_platform_version: PlatformVersion = (5, 3)
    platform_floor: PlatformVersion = (0, 0)
    platform_roof: PlatformVersion = (99, 99)
    upgrade_bases: tuple[UpgradeBase, ...] = ()
    embedded_components: tuple[EmbeddedComponent, ...] = ()
    dependency_state: str = "passed"
    forced_hidden: bool = False
    reboot_after_install: bool = False

    def __post_init__(self) -> None:
        if self.package_type not in PACKAGES:
            raise ValueError("unknown packet class")
        if self.importance not in IMPORTANCES:
            raise ValueError("unknown importance")
        if self.dependency_state not in DEPENDENCY_STATES:
            raise ValueError("unknown dependency state")
        for version in (self.version, self.installed):
            if version is not None and (len(version) != 3 or any(x < 0 for x in version)):
                raise ValueError("bad version")


def platform_accepted(candidate: Candidate) -> bool:
    """Historical AcceptablePlatformL: optional S60, inclusive major/minor range."""
    name_ok = candidate.platform is None or candidate.platform.lower() == "s60"
    return (name_ok and candidate.platform_floor <= candidate.device_platform_version
            <= candidate.platform_roof)


def upgrade_packet_accepted(candidate: Candidate) -> bool:
    """Historical PackageTypeAcceptedL, limited to fully declared examples."""
    if candidate.package_type in {"SA", "SERVICE_PACK", "WIDGET"}:
        return True
    return any(base.same_uid and base.installed is not None
               and base.floor <= base.installed <= base.roof
               for base in candidate.upgrade_bases)


def embedded_degrades(candidate: Candidate) -> bool:
    """Installed embedded component newer than embedded roof: reject."""
    return any(component.installed is not None
               and component.installed > component.embedded_version_roof
               for component in candidate.embedded_components)


def install_check(candidate: Candidate) -> tuple[bool, bool]:
    """(passes, force_hide_equal_version) for the historical AddNode gate.

    Service packs defer installed-state handling to HandleServicePacksL.
    """
    if candidate.package_type == "SERVICE_PACK":
        return True, False
    if candidate.installed is not None:
        if candidate.installed > candidate.version:
            return False, False
        if candidate.installed == candidate.version:
            return True, True
    return True, False


def inspect_candidate(candidate: Candidate) -> dict:
    """Explains only source-backed gates; does not resolve real dependencies/UI."""
    install_ok, equal_installed_hidden = install_check(candidate)
    failed = []
    if candidate.duplicate:
        failed.append("already_collected")
    if not platform_accepted(candidate):
        failed.append("platform_mismatch")
    if not install_ok:
        failed.append("newer_version_already_installed")
    if embedded_degrades(candidate):
        failed.append("embedded_component_would_downgrade")
    if not upgrade_packet_accepted(candidate):
        failed.append("upgrade_base_missing_or_out_of_range")

    candidate_gate_passed = not failed
    hidden = (candidate.forced_hidden or equal_installed_hidden
              or candidate.importance == "hidden")

    if not candidate_gate_passed:
        stage = "rejected_by_candidate_gates"
    elif candidate.dependency_state == "unknown":
        stage = "dependency_resolution_not_modelled"
    elif candidate.dependency_state == "failed":
        stage = "excluded_for_failed_dependency_chain"
    elif candidate.package_type == "SERVICE_PACK":
        stage = "special_service_pack_processing_not_modelled"
    elif hidden:
        stage = "removed_from_visible_head_list"
    else:
        stage = "eligible_for_head_list_comparison_only"

    # MarkFilterNodeL: without caller UID/search filters, normal = unticked;
    # others ticked. This is a preselection heuristic only, never installation.
    if stage == "eligible_for_head_list_comparison_only":
        default_preselection = candidate.importance != "normal"
    else:
        default_preselection = None

    return {
        "example": candidate.label,  # hard-coded fictional labels ONLY
        "candidate_gate_passed": candidate_gate_passed,
        "candidate_gate_failures": failed,
        "hypothetical_head_stage": stage,
        "importance": candidate.importance,  # fixed allowlist
        "package_type": candidate.package_type,  # fixed allowlist
        "default_preselected_if_unfiltered": default_preselection,
        "declares_reboot_after_install": candidate.reboot_after_install,
        "full_dependency_resolution_performed": False,
        "real_device_acceptance_tested": False,
        "actual_installability_verified": False,
        "real_update_payload_present": False,
    }


def replace_recommended(current_version: Version, current_packet: str,
                        current_leaf_distance: int, new_version: Version,
                        new_packet: str, new_leaf_distance: int) -> bool:
    """Source-equivalent *inner preference* from ReplaceRecommendedL.

    Caller must separately establish NodeExists equivalence, valid packages,
    that both dependency graphs passed, and non-service-pack comparison.
    """
    if current_packet not in {"SA", "SP", "PU"} or new_packet not in {"SA", "SP", "PU"}:
        raise ValueError("only ordinary SA/SP/PU packet comparison supported")
    if current_leaf_distance < 0 or new_leaf_distance < 0:
        raise ValueError("distance must be nonnegative")
    if new_version > current_version:
        return True
    if new_version != current_version or new_leaf_distance > current_leaf_distance:
        return False
    return (new_packet == current_packet
            or (new_packet != "SA" and current_packet == "SA")
            or (new_packet == "PU" and current_packet == "SP"))


def examples() -> tuple[Candidate, ...]:
    """All scenarios fabricated, with no IDs, IMEI or firmware identifiers."""
    same = UpgradeBase(True, (1, 2, 0), (1, 0, 0), (1, 9, 9))
    wrong = UpgradeBase(False, (1, 2, 0), (1, 0, 0), (1, 9, 9))
    return (
        Candidate("fresh_normal_sa"),
        Candidate("fresh_critical_sa", importance="critical"),
        Candidate("same_version_installed", installed=(2, 0, 0)),
        Candidate("newer_version_installed", installed=(2, 1, 0)),
        Candidate("pu_missing_base", package_type="PU"),
        Candidate("pu_matching_base", package_type="PU", upgrade_bases=(same,)),
        Candidate("sp_wrong_uid_base", package_type="SP", upgrade_bases=(wrong,)),
        Candidate("wrong_platform", platform="AnotherOS"),
        Candidate("outside_platform_range", platform_floor=(6, 0)),
        Candidate("embedded_downgrade", embedded_components=(EmbeddedComponent((2, 3, 0), (2, 0, 0)),)),
        Candidate("cyclic_dependencies", dependency_state="failed"),
        Candidate("dependency_unknown", dependency_state="unknown"),
        Candidate("server_hidden", importance="hidden"),
        Candidate("already_collected", duplicate=True),
        Candidate("service_pack_special_case", package_type="SERVICE_PACK", installed=(2, 0, 0)),
        Candidate("widget_candidate", package_type="WIDGET"),
        Candidate("reboot_metadata_only", reboot_after_install=True),
    )


def demo_report() -> dict:
    rows = [inspect_candidate(candidate) for candidate in examples()]
    return {
        "study": "Nokia IAUpdate 2.1.0 source-derived synthetic eligibility examples",
        "examples": rows,
        "example_count": len(rows),
        "only_fictional_candidates": True,
        "device_network_or_firmware_access": False,
        "not_a_complete_ui_or_dependency_solver": True,
        "not_a_belle_2_2_0_acceptance_test": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true", required=True,
                    help="run only built-in synthetic examples; no input files or networks")
    ap.parse_args()
    print(json.dumps(demo_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
