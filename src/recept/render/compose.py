from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from ..config import ROOT
from ..schemas import Frame


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


class Style:
    def __init__(self, cfg: dict):
        s = cfg["brand_style"]
        self.primary = hex_rgb(s["primary"])
        self.dark = hex_rgb(s["dark"])
        self.light = hex_rgb(s["light"])
        self.headline_font = str(ROOT / s["headline_font"])
        self.body_font = str(ROOT / s["body_font"])

    def head(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.headline_font, size)

    def body(self, size: int, weight: str = "SemiBold") -> ImageFont.FreeTypeFont:
        f = ImageFont.truetype(self.body_font, size)
        try:
            f.set_variation_by_name(weight)
        except Exception:  # noqa: BLE001
            pass
        return f


def _wrap(draw: ImageDraw.ImageDraw, words: list[str], font, max_w: int) -> list[list[str]]:
    lines: list[list[str]] = [[]]
    for w in words:
        trial = " ".join(lines[-1] + [w])
        if lines[-1] and draw.textlength(trial, font=font) > max_w:
            lines.append([w])
        else:
            lines[-1].append(w)
    return lines


def _fit_headline(draw, text: str, style: Style, max_w: int, max_h: int, start: int):
    words = text.upper().split()
    size = start
    while size > 40:
        font = style.head(size)
        lines = _wrap(draw, words, font, max_w)
        lh = int(size * 1.08)
        if len(lines) * lh <= max_h and all(draw.textlength(" ".join(l), font=font) <= max_w for l in lines):
            return font, lines, lh
        size -= 4
    font = style.head(size)
    return font, _wrap(draw, words, font, max_w), int(size * 1.08)


def draw_text_block(img: Image.Image, frame: Frame, style: Style, zone: str, alpha: float = 1.0) -> Image.Image:
    """Headline (Anton, upper-case, one word in brand orange) + subtext (Montserrat)."""
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    margin = int(W * 0.08)
    max_w = W - 2 * margin
    hl = frame.headline.strip()
    sub = frame.subtext.strip()
    if not hl and not sub:
        return img

    font, lines, lh = _fit_headline(d, hl, style, max_w, int(H * 0.26), int(W * 0.14)) if hl else (None, [], 0)
    sub_font = style.body(int(W * 0.036))
    sub_lines = _wrap(d, sub.split(), sub_font, max_w) if sub else []
    sub_lh = int(W * 0.036 * 1.35)
    block_h = len(lines) * lh + (int(W * 0.03) if sub_lines else 0) + len(sub_lines) * sub_lh

    if zone == "top":
        y = int(H * 0.07)
    elif zone == "bottom":
        y = H - block_h - int(H * 0.09)
    else:
        y = (H - block_h) // 2

    hi = frame.highlight_word.strip().upper().strip(".,!?:")
    a = int(255 * alpha)
    for line in lines:
        x = margin
        for i, word in enumerate(line):
            token = word + (" " if i < len(line) - 1 else "")
            col = style.primary if hi and word.strip(".,!?:") == hi else style.light
            d.text((x + 3, y + 4), token, font=font, fill=(0, 0, 0, int(a * 0.35)))
            d.text((x, y), token, font=font, fill=(*col, a))
            x += d.textlength(token, font=font)
        y += lh
    if sub_lines:
        y += int(W * 0.03)
        for line in sub_lines:
            d.text((margin, y), " ".join(line), font=sub_font, fill=(*style.light, a))
            y += sub_lh
    return Image.alpha_composite(img, layer)


def legibility_gradient(img: Image.Image, zone: str, strength: int = 190) -> Image.Image:
    W, H = img.size
    grad = Image.new("L", (1, 256))
    for i in range(256):
        grad.putpixel((0, i), int(strength * (1 - i / 255) ** 1.6))
    span = int(H * 0.5)
    g = grad.resize((W, span))
    mask = Image.new("L", (W, H), 0)
    if zone == "top":
        mask.paste(g, (0, 0))
    elif zone == "bottom":
        mask.paste(ImageOps.flip(g), (0, H - span))
    else:
        mask = Image.new("L", (W, H), strength // 2)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(mask)
    return Image.alpha_composite(img, shade)


def place_product(img: Image.Image, cutout: Path, zone: str, height_frac: float = 0.5) -> Image.Image:
    W, H = img.size
    prod = Image.open(cutout).convert("RGBA")
    ph = int(H * height_frac)
    pw = int(prod.width * ph / prod.height)
    if pw > W * 0.7:
        pw = int(W * 0.7)
        ph = int(prod.height * pw / prod.width)
    prod = prod.resize((pw, ph), Image.LANCZOS)
    x = (W - pw) // 2
    y = H - ph - int(H * 0.07) if zone != "bottom" else int(H * 0.12)

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sw, sh = int(pw * 1.05), int(ph * 0.07)
    sd.ellipse((W // 2 - sw // 2, y + ph - sh // 2, W // 2 + sw // 2, y + ph + sh // 2), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    out = Image.alpha_composite(img, shadow)
    out.alpha_composite(prod, (x, y))
    return out


def add_logo(img: Image.Image, logo: Path | None, corner: str = "br") -> Image.Image:
    if not logo or not logo.exists():
        return img
    W, H = img.size
    lg = Image.open(logo).convert("RGBA")
    size = int(W * 0.085)
    lg = lg.resize((size, size), Image.LANCZOS)
    m = int(W * 0.045)
    pos = (W - size - m, H - size - m) if corner == "br" else (W - size - m, m)
    img.alpha_composite(lg, pos)
    return img


def dark_card(size: tuple[int, int], style: Style) -> Image.Image:
    # Mirrors the brand's own educational template: near-black with a faint grid.
    W, H = size
    img = Image.new("RGBA", size, (*style.dark, 255))
    d = ImageDraw.Draw(img)
    step = W // 9
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 18), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 18), width=1)
    return img


def page_marker(img: Image.Image, idx: int, total: int, style: Style) -> Image.Image:
    d = ImageDraw.Draw(img)
    W, H = img.size
    f = style.body(int(W * 0.024), "Bold")
    txt = f"{idx:02d} / {total:02d}"
    d.text((int(W * 0.06), H - int(W * 0.08)), txt, font=f, fill=(*style.light, 200))
    return img


def fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img.convert("RGBA"), size, Image.LANCZOS)


def compose_frame(
    *,
    frame: Frame,
    scene: Path | None,
    cutout: Path | None,
    logo: Path | None,
    size: tuple[int, int],
    style: Style,
    page: tuple[int, int] | None = None,
    with_text: bool = True,
) -> Image.Image:
    if frame.layout == "dark_card" or scene is None:
        img = dark_card(size, style)
    else:
        img = fit_cover(Image.open(scene), size)
        if with_text and (frame.headline or frame.subtext):
            img = legibility_gradient(img, frame.text_zone)
    if cutout and frame.product_mode == "composite":
        frac = 0.42 if frame.layout == "dark_card" else (0.36 if size[1] > size[0] * 1.5 else 0.5)
        img = place_product(img, cutout, frame.text_zone, frac)
    if with_text:
        img = draw_text_block(img, frame, style, frame.text_zone)
    img = add_logo(img, logo, "tr" if frame.text_zone == "bottom" else "br")
    if page:
        img = page_marker(img, *page, style)
    return img
