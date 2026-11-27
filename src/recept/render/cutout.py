from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


def _flood_mask(img: Image.Image, tol: int) -> Image.Image:
    # Near-white pixels connected to the border = background.
    w, h = img.size
    px = img.load()
    thr = 255 - tol
    mask = Image.new("L", (w, h), 255)
    m = mask.load()
    q = deque((x, y) for x in range(w) for y in (0, h - 1))
    q.extend((x, y) for y in range(h) for x in (0, w - 1))
    while q:
        x, y = q.popleft()
        if m[x, y] == 0:
            continue
        r, g, b = px[x, y][:3]
        if r < thr or g < thr or b < thr:
            continue
        m[x, y] = 0
        if x > 0:
            q.append((x - 1, y))
        if x < w - 1:
            q.append((x + 1, y))
        if y > 0:
            q.append((x, y - 1))
        if y < h - 1:
            q.append((x, y + 1))
    return mask.filter(ImageFilter.MinFilter(3))


def _rembg_mask(img: Image.Image) -> Image.Image | None:
    try:
        from rembg import new_session, remove
    except ImportError:
        return None
    return remove(img, session=new_session("isnet-general-use"), only_mask=True)


def cut_out_product(src: Path, out: Path, tol: int = 10) -> Path:
    # Union of two masks: rembg drops reflective foil, flood-fill leaks into white labels.
    # Each covers the other's failure, so the label stays pixel-exact.
    img = Image.open(src).convert("RGBA")
    if img.getextrema()[3][0] < 250:
        img.crop(img.getbbox()).save(out)
        return out
    rgb = img.convert("RGB")
    mask = _flood_mask(rgb, tol)
    ai = _rembg_mask(rgb)
    if ai is not None:
        ai = ai.convert("L")
        mask = ImageChops.lighter(mask, ai)
        # flood-fill keeps the soft studio shadow; clip to the object's extent from rembg
        box = ai.point(lambda v: 255 if v > 128 else 0).getbbox()
        if box:
            clip = Image.new("L", mask.size, 0)
            clip.paste(255, (box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2))
            mask = ImageChops.darker(mask, clip)
        # soft grey studio shadow left inside that box: flood neutral light-grey pixels from the border,
        # but never into the object itself (rembg mask, dilated)
        guard = ai.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.MaxFilter(5))
        lo = rgb.convert("L").point(lambda v: 255 if v >= 150 else 0)
        mx = rgb.getchannel("R")
        mn = rgb.getchannel("R")
        for ch in ("G", "B"):
            mx = ImageChops.lighter(mx, rgb.getchannel(ch))
            mn = ImageChops.darker(mn, rgb.getchannel(ch))
        neutral = ImageChops.subtract(mx, mn).point(lambda v: 255 if v <= 10 else 0)
        shadow = ImageChops.darker(lo, neutral)
        shadow.paste(0, mask=guard)
        mask = ImageChops.darker(mask, _flood_mask(shadow.convert("RGB"), 10))
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    img.putalpha(mask)
    img.crop(mask.getbbox()).save(out)
    return out
