"""Source-backed historical IAUpdate illustrative rules, OFFLINE ONLY."""
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "tools" / "iaupdate_eligibility_recon.py"
spec = importlib.util.spec_from_file_location("iaupdate_eligibility_recon", PATH)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

C = module.Candidate
Base = module.UpgradeBase
Embedded = module.EmbeddedComponent
inspect = module.inspect_candidate


class HistoricalAcceptanceRules(unittest.TestCase):
    def test_new_sa_candidate_passes_gates(self):
        self.assertTrue(inspect(C("fictional"))["candidate_gate_passed"])

    def test_device_platform_optional(self):
        self.assertTrue(module.platform_accepted(C("fictional", platform=None)))

    def test_s60_case_insensitive(self):
        self.assertTrue(module.platform_accepted(C("fictional", platform="s60")))

    def test_other_platform_rejected(self):
        self.assertEqual(inspect(C("fictional", platform="Other"))["candidate_gate_failures"], ["platform_mismatch"])

    def test_major_minor_range_is_inclusive(self):
        c = C("fictional", device_platform_version=(5, 3), platform_floor=(5, 3), platform_roof=(5, 3))
        self.assertTrue(module.platform_accepted(c))

    def test_outside_platform_range_rejected(self):
        self.assertFalse(module.platform_accepted(C("fictional", platform_floor=(5, 4))))

    def test_duplicate_rejected(self):
        self.assertEqual(inspect(C("fictional", duplicate=True))["candidate_gate_failures"], ["already_collected"])

    def test_installed_newer_version_rejected(self):
        self.assertIn("newer_version_already_installed", inspect(C("fictional", installed=(4, 0, 0)))["candidate_gate_failures"])

    def test_equal_version_not_rejected_but_hidden(self):
        data = inspect(C("fictional", installed=(2, 0, 0)))
        self.assertTrue(data["candidate_gate_passed"])
        self.assertEqual(data["hypothetical_head_stage"], "removed_from_visible_head_list")

    def test_installed_older_allows_candidate_gate(self):
        self.assertTrue(inspect(C("fictional", installed=(1, 0, 0)))["candidate_gate_passed"])

    def test_sa_no_upgrade_base_needed(self):
        self.assertTrue(module.upgrade_packet_accepted(C("fictional", package_type="SA")))

    def test_sp_without_upgrade_base_rejected(self):
        self.assertFalse(module.upgrade_packet_accepted(C("fictional", package_type="SP")))

    def test_pu_matching_same_uid_base_is_accepted(self):
        base = Base(True, (1, 2, 0), (1, 0, 0), (1, 9, 9))
        self.assertTrue(module.upgrade_packet_accepted(C("fictional", package_type="PU", upgrade_bases=(base,))))

    def test_sp_base_version_outside_range_rejected(self):
        base = Base(True, (2, 0, 0), (1, 0, 0), (1, 9, 9))
        self.assertFalse(module.upgrade_packet_accepted(C("fictional", package_type="SP", upgrade_bases=(base,))))

    def test_sp_base_wrong_uid_rejected(self):
        base = Base(False, (1, 2, 0), (1, 0, 0), (1, 9, 9))
        self.assertFalse(module.upgrade_packet_accepted(C("fictional", package_type="SP", upgrade_bases=(base,))))

    def test_base_range_inclusive(self):
        base = Base(True, (1, 9, 9), (1, 0, 0), (1, 9, 9))
        self.assertTrue(module.upgrade_packet_accepted(C("fictional", package_type="PU", upgrade_bases=(base,))))

    def test_embedded_downgrade_rejected(self):
        c = C("fictional", embedded_components=(Embedded((2, 1, 0), (2, 0, 0)),))
        self.assertIn("embedded_component_would_downgrade", inspect(c)["candidate_gate_failures"])

    def test_embedded_same_version_ok(self):
        c = C("fictional", embedded_components=(Embedded((2, 0, 0), (2, 0, 0)),))
        self.assertFalse(module.embedded_degrades(c))

    def test_dependency_failed_not_visible_head(self):
        data = inspect(C("fictional", dependency_state="failed"))
        self.assertTrue(data["candidate_gate_passed"])
        self.assertEqual(data["hypothetical_head_stage"], "excluded_for_failed_dependency_chain")

    def test_dependency_unknown_is_explicit(self):
        self.assertEqual(inspect(C("fictional", dependency_state="unknown"))["hypothetical_head_stage"], "dependency_resolution_not_modelled")

    def test_hidden_importance_removed_from_head(self):
        self.assertEqual(inspect(C("fictional", importance="hidden"))["hypothetical_head_stage"], "removed_from_visible_head_list")

    def test_normal_is_not_preselected(self):
        self.assertIs(inspect(C("fictional"))["default_preselected_if_unfiltered"], False)

    def test_critical_is_preselected(self):
        self.assertIs(inspect(C("fictional", importance="critical"))["default_preselected_if_unfiltered"], True)

    def test_mandatory_is_preselected(self):
        self.assertIs(inspect(C("fictional", importance="mandatory"))["default_preselected_if_unfiltered"], True)

    def test_service_pack_defers_special_handling(self):
        d = inspect(C("fictional", package_type="SERVICE_PACK", installed=(2, 0, 0)))
        self.assertTrue(d["candidate_gate_passed"])
        self.assertEqual(d["hypothetical_head_stage"], "special_service_pack_processing_not_modelled")

    def test_reboot_metadata_does_not_cause_install(self):
        d = inspect(C("fictional", reboot_after_install=True))
        self.assertTrue(d["declares_reboot_after_install"])
        self.assertFalse(d["actual_installability_verified"])

    def test_preference_newer_version_wins(self):
        self.assertTrue(module.replace_recommended((1,0,0), "PU", 0, (2,0,0), "SA", 5))

    def test_preference_equal_version_pu_over_sp(self):
        self.assertTrue(module.replace_recommended((2,0,0), "SP", 2, (2,0,0), "PU", 2))

    def test_preference_equal_version_sp_over_sa(self):
        self.assertTrue(module.replace_recommended((2,0,0), "SA", 3, (2,0,0), "SP", 2))

    def test_preference_not_if_longer_chain(self):
        self.assertFalse(module.replace_recommended((2,0,0), "SA", 2, (2,0,0), "PU", 3))

    def test_preference_not_downgrade_packet_at_equal_version(self):
        self.assertFalse(module.replace_recommended((2,0,0), "PU", 2, (2,0,0), "SA", 1))

    def test_preference_same_type_shorter_chain(self):
        self.assertTrue(module.replace_recommended((2,0,0), "SA", 3, (2,0,0), "SA", 2))

    def test_preference_old_version_never_wins(self):
        self.assertFalse(module.replace_recommended((3,0,0), "SA", 2, (2,0,0), "PU", 0))

    def test_full_demo_contains_only_fictional_examples(self):
        data = module.demo_report()
        self.assertEqual(data["example_count"], 17)
        self.assertTrue(data["only_fictional_candidates"])
        self.assertFalse(data["device_network_or_firmware_access"])
        self.assertTrue(data["not_a_belle_2_2_0_acceptance_test"])
        self.assertTrue(all("example" in d and not d["actual_installability_verified"] for d in data["examples"]))

    def test_bad_type_rejected(self):
        with self.assertRaises(ValueError):
            C("fictional", package_type="UNKNOWN")

    def test_script_omits_network_and_xml_io(self):
        text = PATH.read_text(encoding="utf-8")
        for disallowed in ("import socket", "import requests", "urllib.request", "subprocess.", "os.system", "ET.parse("):
            self.assertNotIn(disallowed, text)


if __name__ == "__main__":
    unittest.main()
