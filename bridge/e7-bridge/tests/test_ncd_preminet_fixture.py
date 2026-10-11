"""Static, synthetic Preminet 2.0 fixtures. Never transmit to a real E7.

Historical-source shape checks, not a Belle 2.2.0 compatibility test.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent / "fixtures"
NAMESPACE = "http://nokia.com/preminet/protocol/v/2/0"


def q(name):
    return "{" + NAMESPACE + "}" + name


class NcdPreminetOfflineFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browse = ET.parse(BASE / "ncd-preminet-browse-OFFLINE-ONLY.xml").getroot()
        cls.empty = ET.parse(BASE / "ncd-preminet-empty-response-OFFLINE-ONLY.xml").getroot()
        cls.folder = ET.parse(BASE / "ncd-preminet-folder-response-OFFLINE-ONLY.xml").getroot()

    def test_browse_root_and_version(self):
        self.assertEqual(self.browse.tag, q("preminetRequest"))
        self.assertEqual(self.browse.get("version"), "2.0")
        self.assertEqual(self.browse.get("namespace"), "urn:e7-lab:synthetic-catalogue")
        self.assertFalse(self.browse.get("session"))

    def test_browse_entity_is_synthetic(self):
        browse = self.browse.find(q("browse"))
        self.assertIsNotNone(browse)
        entity = browse.find(q("entity"))
        self.assertEqual(entity.get("id"), "offline-root")
        self.assertEqual(entity.get("includeMetaData"), "true")

    def test_historical_normal_content_source_filter(self):
        filt = self.browse.find(q("browse") + "/" + q("responseFilter"))
        self.assertEqual(filt.attrib, {
            "pageSize": "1",
            "pageStart": "0",
            "structureDepth": "1",
            "metadataDepth": "0",
            "metadataPerLevel": "1",
        })

    def test_empty_reply_is_only_an_envelope(self):
        self.assertEqual(self.empty.tag, q("preminetResponse"))
        self.assertEqual(self.empty.get("version"), "2.0")
        self.assertEqual(len(self.empty), 0)

    def test_folder_ref_classification_only(self):
        self.assertEqual(self.folder.tag, q("preminetResponse"))
        entity = self.folder.find(q("entity"))
        self.assertIsNotNone(entity)
        self.assertEqual(entity.get("type"), "FolderRef")
        self.assertEqual(entity.get("id"), "offline-folder")
        self.assertIsNone(entity.get("uri"))

    def test_no_actions_cookies_or_downloads(self):
        forbidden = {"actionRequest", "updateDetails", "cookies",
                     "purchase", "downloadableContent", "dataBlock"}
        for root in (self.browse, self.empty, self.folder):
            names = {el.tag.rsplit("}", 1)[-1] for el in root.iter()}
            self.assertFalse(names.intersection(forbidden))

    def test_all_fixtures_have_no_private_data(self):
        for fixture in BASE.glob("ncd-preminet-*-OFFLINE-ONLY.xml"):
            text = fixture.read_text(encoding="utf-8").lower()
            for private in ("imei", "imsi", "msisdn", "arrowcdb",
                            "10.42.0.85", "serialnumber"):
                self.assertNotIn(private, text)


if __name__ == "__main__":
    unittest.main()
