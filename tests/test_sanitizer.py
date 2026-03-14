import unittest
import sys
import os

# Add root project dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.utils.network_sanitizer import clean_output

class TestNetworkSanitizer(unittest.TestCase):

    def test_clean_ansi_codes(self):
        raw = b"Line 1\x1b[31mRed Text\x1b[0m\nLine 2"
        cleaned = clean_output(raw)
        self.assertEqual(cleaned, "Line 1Red Text\nLine 2")

    def test_clean_aruba_pagination(self):
        # Simulate Aruba pagination leftovers
        raw = b"interface vlan 1\n\r\x1b[24;1H\x1b[?25h-- MORE --, next page: Space, next line: Enter, quit: Control-C\n"
        cleaned = clean_output(raw)
        self.assertNotIn("MORE", cleaned)
        self.assertNotIn("\x1b[24;1H", cleaned)
        self.assertTrue(cleaned.startswith("interface vlan 1"))

    def test_clean_cisco_more(self):
        raw = b"router bgp 100\n --More-- \b\b\b\b\b\b\b\b\b        \b\b\b\b\b\b\b\b\bneighbor 1.1.1.1"
        cleaned = clean_output(raw)
        # Should not have --More-- and backspaces should be processed
        self.assertNotIn("More", cleaned)
        self.assertTrue(cleaned.endswith("neighbor 1.1.1.1"))

    def test_clean_backspaces(self):
        raw = b"passwo\x08\x08\x08word123"
        cleaned = clean_output(raw)
        self.assertEqual(cleaned, "pasword123")

    def test_trim_empty_lines(self):
        raw = b"line 1\n\n\n\nline 2"
        cleaned = clean_output(raw)
        self.assertEqual(cleaned, "line 1\n\nline 2")

if __name__ == '__main__':
    unittest.main()
