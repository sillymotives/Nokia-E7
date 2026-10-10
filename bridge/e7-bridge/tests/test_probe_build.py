"""MakeSIS compatibility regression for the disposable deployment fixture."""
from pathlib import Path
import unittest


class ProbeBuilderCompatibility(unittest.TestCase):
    def test_legacy_makesis_receives_relative_paths(self):
        p = Path(__file__).resolve().parents[1] / "build" / "in-container-probe.sh"
        text = p.read_text(encoding="utf-8")
        self.assertIn('cd "$build" && "$toolchain/bin/makesis" deploy-probe.pkg probe-unsigned.sis', text)
        self.assertNotIn('"$toolchain/bin/makesis" "$build/deploy-probe.pkg"', text)


if __name__ == "__main__":
    unittest.main()
