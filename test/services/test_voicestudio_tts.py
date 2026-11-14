import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.services import voice


class TestVoiceStudioTts(unittest.TestCase):
    def test_voice_listing_prefixes_ids_and_skips_duplicates(self):
        body = {"voices": [{"voice_id": "alloy"}, {"id": "ash"}, {"voice_id": "alloy"}]}
        response = SimpleNamespace(status_code=200, json=lambda: body)
        with patch.dict(config.voicestudio, {"voices": []}, clear=False), patch.object(
            voice, "trace_http_call", return_value=response
        ) as call:
            voices = voice.get_voicestudio_voices()
        self.assertEqual(voices, ["voicestudio:alloy", "voicestudio:ash"])
        self.assertTrue(call.call_args.args[2].endswith("/v1/audio/voices"))

    def test_voice_listing_falls_back_when_server_is_down(self):
        with patch.dict(config.voicestudio, {"voices": []}, clear=False), patch.object(
            voice, "trace_http_call", side_effect=ConnectionError("down")
        ):
            self.assertEqual(voice.get_voicestudio_voices(), ["voicestudio:default"])
            self.assertEqual(voice.get_voicestudio_voices(fallback=False), [])

    def test_tts_routes_to_openai_compatible_endpoint(self):
        with patch.object(
            voice, "_openai_compatible_tts", return_value="sub"
        ) as shared:
            result = voice.tts("Halo dunia", "voicestudio:alloy-Female", 1.2, "a.mp3")
        self.assertEqual(result, "sub")
        args = shared.call_args.args
        self.assertEqual(args[0], "voicestudio")
        self.assertTrue(args[1].endswith("/v1"))
        self.assertEqual(args[4], "alloy")  # sufiks tampilan -Female dibuang
        self.assertEqual(args[6], 1.2)

    def test_text_without_speakable_characters_is_rejected(self):
        self.assertIsNone(voice.voicestudio_tts("...", "alloy", "a.mp3"))


if __name__ == "__main__":
    unittest.main()
