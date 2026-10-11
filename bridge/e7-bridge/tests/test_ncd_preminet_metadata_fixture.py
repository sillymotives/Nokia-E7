"""Synthetic Nokia Preminet 2.0 metadata structure checks.

This test never connects to the E7 or a network service. It checks only
historical source-derived XML shapes, NOT real Belle client acceptance.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ncd-preminet-metadata-OFFLINE-ONLY.xml"
NS = "http://nokia.com/preminet/protocol/v/2/0"


def q(local):
    return "{" + NS + "}" + local


class OfflinePreminetMetadataFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(FIXTURE).getroot()

    def test_source_derived_preminet_response_root(self):
        self.assertEqual(self.root.tag, q("preminetResponse"))
        self.assertEqual(self.root.get("version"), "2.0")

    def test_nested_embedded_data_entities(self):
        block = self.root.find(q("embeddedData"))
        self.assertIsNotNone(block)
        self.assertIsNotNone(block.find(q("entities")))
        data_entities = list(block.iter(q("dataEntity")))
        self.assertEqual(len(data_entities), 2)

    def test_entity_metadata_types(self):
        records = list(self.root.iter(q("dataEntity")))
        self.assertEqual([r.get("type") for r in records], [
            "FolderData", "ItemData",
        ])

    def test_metadata_name_and_description(self):
        for record in self.root.iter(q("dataEntity")):
            self.assertIsNotNone(record.find(q("name")))
            self.assertIsNotNone(record.find(q("description")))

    def test_downloadable_content_is_only_placeholder_metadata(self):
        item = next(r for r in self.root.iter(q("dataEntity"))
                    if r.get("type") == "ItemData")
        content = item.find(q("downloadableContent"))
        self.assertIsNotNone(content)
        self.assertEqual(content.get("size"), "0")
        self.assertEqual(content.get("mime"), "application/octet-stream")
        self.assertIsNone(content.get("uri"))

    def test_iaupdate_detail_pairs(self):
        item = next(r for r in self.root.iter(q("dataEntity"))
                    if r.get("type") == "ItemData")
        detailpairs = {
            e.get("id"): e.get("value")
            for e in item.findall(q("details") + "/" + q("detail"))
        }
        self.assertEqual(detailpairs, {
            "iaimportance": "normal",
            "iatype": "SA",
        })

    def test_no_active_directives_or_network_uris(self):
        forbidden = {
            "actionRequest", "actionEntity", "cookies", "cookie",
            "purchase", "purchaseOption", "downloadDetails", "descriptor",
            "error", "dataBlocks", "installationReport", "query",
        }
        names = {e.tag.rsplit("}", 1)[-1] for e in self.root.iter()}
        self.assertFalse(names.intersection(forbidden))
        self.assertTrue(all("uri" not in e.attrib for e in self.root.iter()))

    def test_no_private_device_data(self):
        content = FIXTURE.read_text(encoding="utf-8").lower()
        for secret in (
            "imei", "imsi", "msisdn", "arrowcdb", "10.42.0.85",
            "http://10.", "https://", "phone number", "serialnumber",
        ):
            self.assertNotIn(secret, content)


if __name__ == "__main__":
    unittest.main()
