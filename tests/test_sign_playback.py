"""Verify animation timing and immutable native-buffer playback without GPIO."""
import unittest

from PIL import Image

from poor_louis_farms import (
    animation_frame_count,
    build_animation_frames,
    cache_animation_canvases,
    play_cached_animation,
    refresh_fraction,
)


class FakeCanvas:
    def __init__(self):
        self.uploads = []

    def SetImage(self, image, unsafe):
        if self.uploads:
            raise AssertionError("A cached canvas was rewritten")
        self.uploads.append((image.tobytes(), unsafe))


class FakeMatrix:
    def __init__(self):
        self.canvases = []
        self.swaps = []

    def CreateFrameCanvas(self):
        canvas = FakeCanvas()
        self.canvases.append(canvas)
        return canvas

    def SwapOnVSync(self, canvas, framerate_fraction=1):
        self.swaps.append((canvas, framerate_fraction))


class AnimationTimingTests(unittest.TestCase):
    def test_higher_rate_adds_samples_without_speeding_scene(self):
        slow = build_animation_frames(128, 128, 8)
        fast = build_animation_frames(128, 128, 30)
        self.assertEqual(len(slow), 52)
        self.assertEqual(len(fast), 195)
        self.assertEqual(len(set(fast)), 195)
        # Both renderers must show the same scene at each half-second timestamp.
        for half_second in range(13):
            self.assertEqual(slow[half_second * 4], fast[half_second * 15])

    def test_vsync_cadence_and_invalid_rates(self):
        self.assertEqual(refresh_fraction(120, 30), 4)
        self.assertEqual(refresh_fraction(120, 24), 5)
        self.assertEqual(refresh_fraction(120, 60), 2)
        for fps in (0, -1, float("nan"), float("inf")):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                animation_frame_count(fps)
        for refresh, fps in ((120, 35), (120, 121), (0, 30)):
            with self.subTest(refresh=refresh, fps=fps), self.assertRaises(ValueError):
                refresh_fraction(refresh, fps)


class NativePlaybackTests(unittest.TestCase):
    def test_preload_once_then_only_cycle_complete_native_frames(self):
        matrix = FakeMatrix()
        images = [Image.new("RGB", (2, 2), color) for color in ("red", "green", "blue")]
        canvases = cache_animation_canvases(matrix, iter(images), lambda: True)
        self.assertEqual(matrix.swaps, [(canvases[0], 1)])
        for canvas, image in zip(canvases, images):
            self.assertEqual(canvas.uploads, [(image.tobytes(), False)])
        matrix.swaps.clear()
        play_cached_animation(matrix, canvases, 30, 120, lambda: len(matrix.swaps) < 7)
        self.assertEqual(matrix.swaps, [(canvases[i % 3], 4) for i in range(7)])
        self.assertEqual(len(matrix.canvases), 3)

    def test_shutdown_during_preload_stops_allocating(self):
        matrix = FakeMatrix()
        images = [Image.new("RGB", (2, 2)) for _ in range(3)]
        canvases = cache_animation_canvases(matrix, iter(images), lambda: len(matrix.canvases) < 1)
        self.assertEqual(len(canvases), 1)
        self.assertEqual(len(matrix.canvases), 1)

    def test_empty_cache_cannot_play(self):
        with self.assertRaises(ValueError):
            play_cached_animation(FakeMatrix(), (), 30, 120, lambda: True)


if __name__ == "__main__":
    unittest.main()
