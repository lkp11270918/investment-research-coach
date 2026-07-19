from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.file_parsers import parse_uploaded_file
from backend.models import ContentBlock, MaterialModality


class MultimodalNormalizationTest(unittest.TestCase):
    def test_text_has_paragraph_coordinates(self) -> None:
        material = parse_uploaded_file(filename="note.txt", data="第一段\n第二段".encode())
        self.assertEqual(material.modality, MaterialModality.TEXT)
        self.assertEqual([block.paragraph for block in material.blocks], [1, 2])

    def test_csv_has_row_coordinates(self) -> None:
        material = parse_uploaded_file(filename="finance.csv", data="指标,2024\n营收,100".encode(), material_id="financial")
        self.assertEqual(material.modality, MaterialModality.TABLE)
        self.assertEqual([block.row for block in material.blocks], [1, 2])

    @patch("backend.file_parsers.parse_image")
    def test_image_inference_remains_unconfirmed(self, mock_parse_image) -> None:
        mock_parse_image.return_value = (
            "图中可见营收100",
            [ContentBlock(modality=MaterialModality.IMAGE, content="增长可能来自提价", extraction_method="vision_inference", requires_confirmation=True)],
            ["图片推断待确认"],
        )
        material = parse_uploaded_file(filename="chart.png", data=b"image")
        self.assertEqual(material.modality, MaterialModality.IMAGE)
        self.assertTrue(material.blocks[0].requires_confirmation)
        self.assertEqual(material.parse_warnings, ["图片推断待确认"])

    @patch("backend.file_parsers.parse_audio")
    def test_audio_speaker_attribution_remains_unconfirmed(self, mock_parse_audio) -> None:
        mock_parse_audio.return_value = (
            "海外业务会增长",
            [ContentBlock(modality=MaterialModality.AUDIO, content="海外业务会增长", speaker="unknown", requires_confirmation=True)],
            ["说话人待确认"],
        )
        material = parse_uploaded_file(filename="call.mp3", data=b"audio", material_id="management")
        self.assertEqual(material.modality, MaterialModality.AUDIO)
        self.assertEqual(material.blocks[0].speaker, "unknown")
        self.assertTrue(material.blocks[0].requires_confirmation)


if __name__ == "__main__":
    unittest.main()
