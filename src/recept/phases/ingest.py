from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..config import ROOT
from ..render.cutout import cut_out_product
from ..schemas import FAQ, Brief, ProductFacts, Sources
from ..state import Run

IMG_RE = re.compile(
    r"https://[a-z.]+/media/catalog/product/(?:cache/[0-9a-f]+/)?([0-9a-z_]/[0-9a-z_]/[^\"'\s,\]]+?\.(?:jpg|png|webp))"
)


def _jsonld(page: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        out.extend(d.get("@graph", [d]) if isinstance(d, dict) else d)
    return out


def _gallery(page: str, base: str) -> list[str]:
    text = html.unescape(page).replace("\\/", "/")
    seen: dict[str, int] = {}
    for p in IMG_RE.findall(text):
        seen[p] = seen.get(p, 0) + 1
    return [f"{base}/media/catalog/product/{p}" for p, _ in sorted(seen.items(), key=lambda kv: -kv[1])]


def _pick_packshot(urls: list[str], hint: str) -> str | None:
    if hint:
        for u in urls:
            if hint in u:
                return u
    skip = ("lifestyle", "sample", "view2", "view3", "bundle")
    for u in urls:
        name = u.rsplit("/", 1)[-1].lower()
        if any(s in name for s in skip):
            continue
        if "mockup" in name or "front" in name or name.endswith("_1.png"):
            return u
    return urls[0] if urls else None


def scrape_product(client: httpx.Client, run: Run, url: str, hint: str) -> tuple[ProductFacts, str | None]:
    page = client.get(url).text
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    nodes = _jsonld(page)
    prod = next((n for n in nodes if n.get("@type") == "Product"), None)
    if not prod:
        raise RuntimeError(f"Nema schema.org Product podataka na {url}")
    faq_node = next((n for n in nodes if n.get("@type") == "FAQPage"), {})
    faq = [
        FAQ(question=q["name"], answer=q["acceptedAnswer"]["text"])
        for q in faq_node.get("mainEntity", [])
    ]
    slug = Path(urlparse(url).path).stem
    offers = prod.get("offers", {})
    facts = ProductFacts(
        id=slug,
        url=url,
        name=prod["name"].strip(),
        description=prod.get("description", ""),
        category=prod.get("category", ""),
        price_low_eur=offers.get("lowPrice"),
        price_high_eur=offers.get("highPrice"),
        faq=faq,
        image_urls=prod.get("image", []),
    )
    gallery = _gallery(page, base)
    shot = _pick_packshot(gallery, hint) or (facts.image_urls[0] if facts.image_urls else None)
    if shot:
        dst = run.path("products", f"{slug}{Path(shot).suffix}")
        dst.write_bytes(client.get(shot).content)
        facts.local_images = [run.rel(dst)]
        cut = run.path("products", f"{slug}_cutout.png")
        cut_out_product(dst, cut)
        facts.cutout = run.rel(cut)
    org = next((n for n in nodes if n.get("@type") == "Organization" and n.get("logo")), None)
    return facts, (org or {}).get("logo")


def run(run: Run, brief: Brief, cfg: dict) -> Sources:
    unavailable: list[str] = []
    products: list[ProductFacts] = []
    logo = None
    logo_url = None
    headers = {"User-Agent": cfg["scrape"]["user_agent"]}
    with httpx.Client(headers=headers, timeout=cfg["scrape"]["timeout_s"], follow_redirects=True) as client:
        for p in brief.products:
            try:
                f, logo_url = scrape_product(client, run, p.url, p.packshot)
                products.append(f)
                run.log(f"proizvod: {f.name} ({len(f.faq)} FAQ, packshot: {bool(f.cutout)})")
            except Exception as e:  # noqa: BLE001
                unavailable.append(f"{p.url}: {e}")
                run.log(f"NEDOSTUPNO {p.url}: {e}")

        local_logo = ROOT / "inputs" / "logo.png"
        if local_logo.exists():
            dst = run.path("logo.png")
            dst.write_bytes(local_logo.read_bytes())
            logo = run.rel(dst)
        elif logo_url:
            dst = run.path("logo.png")
            dst.write_bytes(client.get(logo_url).content)
            logo = run.rel(dst)
        else:
            unavailable.append("logo: nije pronađen na webu, dodaj inputs/logo.png")

    ref_dir = ROOT / brief.references_dir
    shots = sorted(str(p.relative_to(ROOT).as_posix()) for p in ref_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not shots:
        unavailable.append(f"Nema Instagram screenshotova u {brief.references_dir}")
    unavailable.append(
        "Instagram nije čitan automatski (prijava i uvjeti korištenja); analiza koristi ručno spremljene screenshotove."
    )
    sources = Sources(products=products, logo=logo, instagram_screenshots=shots, unavailable=unavailable)
    run.save("ingest", sources)
    return sources
