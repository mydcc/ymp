import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ymp.downloader import parse_pls

class TestPLSParser(unittest.TestCase):
    def test_parse_local_pls(self):
        # Create a dummy PLS file
        content = """[playlist]
File1=http://example.com/song1.mp3
Title1=Song 1
File2=http://example.com/song2.mp3
Title2=Song 2
"""
        with open("test.pls", "w") as f:
            f.write(content)

        try:
            urls = parse_pls("test.pls")
            self.assertEqual(len(urls), 2)
            self.assertEqual(urls[0], "http://example.com/song1.mp3")
            self.assertEqual(urls[1], "http://example.com/song2.mp3")
        finally:
            if os.path.exists("test.pls"):
                os.remove("test.pls")

    @patch('ymp.downloader.get')
    def test_parse_remote_pls(self, mock_get):
        # Mock requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """[playlist]
File1=http://remote.com/stream
"""
        mock_get.return_value = mock_response

        urls = parse_pls("http://example.com/radio.pls")
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "http://remote.com/stream")

if __name__ == '__main__':
    unittest.main()
