from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from ..schemas import Frame
from .compose import Style, add_logo, draw_text_block


def _zoom(img: Image.Image, t: float, direction: int) -> Image.Image:
    W, H = img.size
    z = 1.0 + 0.08 * (t if direction > 0 else 1 - t)
    cw, ch = int(W / z), int(H / z)
    x = (W - cw) // 2
    y = (H - ch) // 2
    return img.crop((x, y, x + cw, y + ch)).resize((W, H), Image.BILINEAR)


def render_reel(
    shots: list[tuple[Image.Image, Frame]],
    out: Path,
    style: Style,
    logo: Path | None,
    seconds: float,
    fps: int,
    fade: float = 0.35,
) -> Path:
    """shots: (background without text, frame). Ken Burns on the background, text fades in on top,
    crossfade between shots. Frames are piped straight into ffmpeg (bundled via imageio-ffmpeg)."""
    W, H = shots[0][0].size
    n = int(seconds * fps)
    nf = int(fade * fps)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def frame_at(i: int, k: int) -> Image.Image:
        bg, fr = shots[i]
        img = _zoom(bg, k / n, 1 if i % 2 == 0 else -1).convert("RGBA")
        a = min(1.0, k / max(1, nf))
        img = draw_text_block(img, fr, style, fr.text_zone, alpha=a)
        return add_logo(img, logo, "tr" if fr.text_zone == "bottom" else "br")

    assert proc.stdin
    for i in range(len(shots)):
        for k in range(n):
            img = frame_at(i, k)
            if i + 1 < len(shots) and k >= n - nf:
                nxt = frame_at(i + 1, 0)
                img = Image.blend(img, nxt, (k - (n - nf)) / nf)
            proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg nije uspio složiti reel")
    return out
