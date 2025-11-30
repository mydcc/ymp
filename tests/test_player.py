import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import subprocess

# Ensure the package is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ymp.player as player

class TestPlayer(unittest.TestCase):

    @patch('ymp.player.AUDIO_AVAILABLE', False)
    def test_mock_playback(self):
        """Test fallback when audio is missing."""
        play_obj, start_time = player.genmusic("dummy.mp3", 0)
        self.assertIsInstance(play_obj, player.MockPlayObj)
        self.assertTrue(play_obj.is_playing())
        player.pausemusic(play_obj)
        self.assertFalse(play_obj.is_playing())

    @patch('ymp.player.AUDIO_AVAILABLE', True)
    @patch('subprocess.Popen')
    def test_ffplay_start(self, mock_popen):
        """Test that ffplay is called with correct arguments."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Running
        mock_popen.return_value = mock_process

        url = "http://example.com/stream.mp3"
        play_obj, start_time = player.genmusic(url, 0)

        self.assertIsInstance(play_obj, player.FFplayProcess)

        # Verify call args
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        self.assertEqual(cmd[0], 'ffplay')
        self.assertIn('-nodisp', cmd)
        self.assertIn(url, cmd)

    @patch('ymp.player.AUDIO_AVAILABLE', True)
    @patch('subprocess.Popen')
    def test_ffplay_seek(self, mock_popen):
        """Test seek argument."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        player.genmusic("song.mp3", 5000) # 5 seconds

        args, kwargs = mock_popen.call_args
        cmd = args[0]
        self.assertIn('-ss', cmd)
        self.assertIn('5.0', cmd)

if __name__ == '__main__':
    unittest.main()
