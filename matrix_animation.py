"""Build and validate native seasonal GIFs without loading the GPIO driver."""
import argparse
from pathlib import Path

from PIL import Image, ImageSequence

from config import MATRIX_REFRESH_LIMIT_HZ


NATIVE_SIZE = (128, 128)
# Each native canvas costs roughly 450 KiB on the current Pi. Bound startup RAM.
MAX_FRAMES = 384


def read_gif(path: Path) -> tuple[list[Image.Image], list[int]]:
    """Decode composited GIF frames, with remaining transparency shown as black."""
    frames = []
    durations = []
    with Image.open(path) as gif:
        if gif.format != "GIF" or gif.size != NATIVE_SIZE:
            raise ValueError("Expected a native 128×128 GIF")
        if gif.info.get("loop") != 0:
            raise ValueError("GIF must declare infinite looping (loop=0)")
        for index, frame in enumerate(ImageSequence.Iterator(gif), start=1):
            if index > MAX_FRAMES:
                raise ValueError(f"GIF exceeds the Pi cache budget of {MAX_FRAMES} frames")
            duration = frame.info.get("duration", 0)
            if duration <= 0 or frame.size != NATIVE_SIZE:
                raise ValueError(f"Frame {index} needs a positive delay and native dimensions")
            rgba = frame.convert("RGBA")
            rgb = Image.new("RGB", NATIVE_SIZE)
            rgb.paste(rgba, mask=rgba.getchannel("A"))
            frames.append(rgb)
            durations.append(duration)
    if not frames:
        raise ValueError("GIF contains no frames")
    return frames, durations


def refresh_holds(durations: list[int], refresh_hz: int) -> tuple[int, ...]:
    """Snap cumulative frame boundaries to refreshes to avoid per-frame drift."""
    holds = []
    elapsed_ms = previous_tick = 0
    for index, duration in enumerate(durations, start=1):
        elapsed_ms += duration
        tick = (elapsed_ms * refresh_hz + 500) // 1000
        if tick <= previous_tick:
            raise ValueError(f"Frame {index} is too short at {refresh_hz} Hz")
        holds.append(tick - previous_tick)
        previous_tick = tick
    return tuple(holds)


def validate_gif(path: Path) -> str:
    frames, durations = read_gif(path)
    holds = refresh_holds(durations, MATRIX_REFRESH_LIMIT_HZ)
    return (
        f"128×128 GIF, {len(frames)} frames, infinite loop, "
        f"{sum(durations) / 1000:.3f}s source / "
        f"{sum(holds) / MATRIX_REFRESH_LIMIT_HZ:.3f}s at configured refresh, "
        f"frame delays {min(durations)}–{max(durations)} ms"
    )


def build_gif(directory: Path, output: Path, duration_ms: int) -> None:
    if not 10 <= duration_ms <= 655350 or duration_ms % 10:
        raise ValueError("GIF delay must be 10–655350 ms in 10 ms steps")
    paths = sorted(directory.glob("*.png"))
    if not 1 <= len(paths) <= MAX_FRAMES:
        raise ValueError(f"Expected 1–{MAX_FRAMES} PNG frames")
    frames = []
    for path in paths:
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != NATIVE_SIZE:
                raise ValueError(f"{path} is not a native 128×128 PNG")
            rgba = image.convert("RGBA")
            rgb = Image.new("RGB", NATIVE_SIZE)
            rgb.paste(rgba, mask=rgba.getchannel("A"))
            frames.append(rgb)
    frames[0].save(
        output, format="GIF", save_all=True, append_images=frames[1:],
        duration=duration_ms, loop=0, disposal=1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("gif", type=Path)
    build = commands.add_parser("build")
    build.add_argument("frames", type=Path, help="directory of lexically ordered PNGs")
    build.add_argument("gif", type=Path)
    build.add_argument("--duration-ms", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build_gif(args.frames, args.gif, args.duration_ms)
        print(validate_gif(args.gif))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
