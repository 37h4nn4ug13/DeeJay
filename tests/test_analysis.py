import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deejay.analysis import BackgroundAnalyzer  # noqa: E402


class BackgroundAnalyzerTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmpdir.name) / "cache"
        self.db_path = Path(self.tmpdir.name) / "analysis.sqlite"
        self.audio_file = Path(self.tmpdir.name) / "audio.raw"
        self.audio_file.write_bytes(os.urandom(2048))
        self.analyzer = BackgroundAnalyzer(
            cache_dir=self.cache_dir,
            db_path=self.db_path,
            max_workers=2,
        )

    def tearDown(self):
        self.analyzer.shutdown()
        self.tmpdir.cleanup()

    def test_analysis_runs_in_background_and_persists_outputs(self):
        future = self.analyzer.analyze_track("track-1", self.audio_file)
        result = future.result(timeout=5)

        self.assertTrue(result.waveform_path.exists())
        self.assertTrue(result.peaks_path.exists())
        self.assertTrue(result.beatgrid_path.exists())

        with result.waveform_path.open() as fp:
            data = json.load(fp)
            self.assertIn("amplitudes", data)
        record = self.analyzer.db.get_analysis("track-1")
        self.assertIsNotNone(record)
        self.assertEqual(record["waveform_path"], str(result.waveform_path))
        self.assertEqual(record["peaks_path"], str(result.peaks_path))
        self.assertEqual(record["beatgrid_path"], str(result.beatgrid_path))

    def test_cached_result_shortcuts_future(self):
        # First run stores results.
        initial = self.analyzer.analyze_track("track-2", self.audio_file).result(timeout=5)
        timestamp = initial.updated_at

        # Second call should return immediately with cached data.
        start = time.time()
        cached_future = self.analyzer.analyze_track("track-2", self.audio_file)
        self.assertTrue(cached_future.done())
        cached = cached_future.result(timeout=0)
        elapsed = time.time() - start

        self.assertLess(elapsed, 0.05)
        self.assertEqual(cached.updated_at, timestamp)
        self.assertTrue(cached.waveform_path.exists())
