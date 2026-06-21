#!/usr/bin/env python3
"""Create a local demo JPEG for scripts/demo.sh (gitignored)."""

from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parent / "demo-photo.jpg"


def main() -> None:
    image = Image.new("RGB", (512, 512), color=(30, 144, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((96, 96, 416, 416), fill=(255, 255, 255))
    draw.text((160, 230), "DEMO", fill=(30, 144, 255))
    image.save(OUTPUT, format="JPEG", quality=90)
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
