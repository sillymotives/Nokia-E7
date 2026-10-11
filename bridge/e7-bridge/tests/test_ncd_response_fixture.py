"""Offline, static historical Nokia NCD configuration-response shape tests.

The XML fixture is synthetic, contains no handset identifiers, and must
never be served to the phone. Passing these tests does NOT prove that Belle
accepts the response or that an update catalogue would work.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

FILE = Path(__file__).resolve().parent / "fixtures" / "ncd-config-response-OFFLINE-ONLY.xml"
NS = "http://nokia.com/preminet/protocol/configuration/v/1/0"


def qname(local):
    return "{" + NS + "}" + local


class NcdOfflineResponseFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(FILE).getroot()

    def test_root_shape_and_attributes(self):
        self.assertEqual(self.root.tag, qname("configurationResponse"))
        self.assertEqual(self.root.attrib, {"version": "1.0", "expirationDelta": "0"})

    def test_nested_client_configuration(self):
        clients = self.root.findall(qname("clientConfiguration"))
        self.assertEqual(len(clients), 1)
        self.assertIsNotNone(clients[0].find(qname("details")))

    def test_content_source_path_matches_historical_root_loader(self):
        config = self.root.find(qname("clientConfiguration"))
        details = config.find(qname("details"))
        sources = [e for e in details.findall(qname("detail"))
                   if e.get("id") == "contentSources"]
        self.assertEqual(len(sources), 1)
        namespaces = [e for e in sources[0].findall(qname("detail"))
                      if e.get("id") == "namespace"]
        self.assertEqual(len(namespaces), 1)
        uris = [e for e in namespaces[0].findall(qname("detail"))
                if e.get("id") == "uri"]
        self.assertEqual(len(uris), 1)

    def test_content_pairs_follow_nokia_parser_words(self):
        source = next(e for e in self.root.iter(qname("detail"))
                      if e.get("id") == "namespace")
        pairs = {e.get("key"): e.get("value") for e in source.findall(qname("content"))}
        self.assertEqual(pairs["provider"], "offline-fixture")
        self.assertEqual(pairs["id"], "offline-root")
        self.assertEqual(pairs["alwaysVisible"], "false")
        self.assertEqual(pairs["transparent"], "false")

    def test_no_active_protocol_directives(self):
        names = {e.tag.rsplit("}", 1)[-1] for e in self.root.iter()}
        self.assertFalse(names.intersection({
            "actionRequest", "updateDetails", "cookies", "cookie", "message",
            "error", "serverDetails", "preminetResponse", "downloadableContent",
        }))

    def test_reserved_nonreal_uri_and_no_handset_secrets(self):
        source = next(e for e in self.root.iter(qname("detail"))
                      if e.get("id") == "namespace")
        uri = next(e for e in source.findall(qname("detail"))
                   if e.get("id") == "uri")
        self.assertEqual(uri.get("value"), "http://catalogue.invalid/ncd")
        xml = FILE.read_text(encoding="utf-8").lower()
        for term in ("arrowcdb.ncd.nokia.com", "10.42.0.85", "imei", "imsi"):
            self.assertNotIn(term, xml)


if __name__ == "__main__":
    unittest.main()
