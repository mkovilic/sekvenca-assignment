import json
from pathlib import Path

import pytest
from PIL import Image

from recept.llm import AgentLLM, AgentPending
from recept.phases.ingest import _gallery, _jsonld, _pick_packshot
from recept.render.compose import Style, compose_frame
from recept.render.cutout import cut_out_product
from recept.schemas import Caption, Frame

PAGE = """
<script type="application/ld+json">{"@graph":[{"@type":"Product","name":"X","image":["a.jpg"],
"offers":{"lowPrice":1,"highPrice":2}},{"@type":"Organization","logo":"https://s/logo.png"}]}</script>
<div data-x='https:\\/\\/shop.hr\\/media\\/catalog\\/product\\/c\\/r\\/x-lifestyle.jpg'></div>
<img src="https://shop.hr/media/catalog/product/cache/abc/c/r/x-mockup-view1.jpg">
"""


def test_jsonld_and_packshot_pick():
    nodes = _jsonld(PAGE)
    assert {n["@type"] for n in nodes} == {"Product", "Organization"}
    gallery = _gallery(PAGE, "https://shop.hr")
    assert _pick_packshot(gallery, "") .endswith("x-mockup-view1.jpg")  # lifestyle shots skipped
    assert _pick_packshot(gallery, "lifestyle").endswith("x-lifestyle.jpg")  # explicit hint wins


def test_agent_llm_writes_request_then_reads_answer(tmp_path: Path):
    llm = AgentLLM(tmp_path)
    with pytest.raises(AgentPending) as e:
        llm.structured(key="cap", system="Write a caption", content="ctx", schema=Caption)
    assert e.value.requests[0].read_text(encoding="utf-8").startswith("# Task: cap")
    (tmp_path / "agent" / "cap.json").write_text(json.dumps({"caption": "hi", "hashtags": ["#a"], "alt_text": "x"}))
    assert llm.structured(key="cap", system="", content="", schema=Caption).caption == "hi"


def test_cutout_keeps_white_label(tmp_path: Path):
    img = Image.new("RGB", (200, 200), "white")
    for x in range(60, 140):
        for y in range(40, 180):
            label = 90 < y < 120 and 70 < x < 130
            img.putpixel((x, y), (255, 255, 255) if label else (250, 90, 30))  # white label inside the pack
    src = tmp_path / "p.png"
    img.save(src)
    out = cut_out_product(src, tmp_path / "c.png")
    cut = Image.open(out)
    assert cut.size[0] < 100  # background cropped away
    assert cut.getpixel((cut.width // 2, cut.height // 2))[3] > 200  # label stays opaque


def test_compose_renders_dark_card():
    cfg = {"brand_style": {"primary": "#FA762B", "dark": "#20201E", "light": "#FEF6E2",
                           "headline_font": "assets/fonts/Anton-Regular.ttf", "body_font": "assets/fonts/Montserrat-VF.ttf"}}
    f = Frame(headline="Creatine, no nonsense", subtext="x", highlight_word="Creatine", scene_prompt="",
              product_id="", product_mode="none", text_zone="top", layout="dark_card")
    img = compose_frame(frame=f, scene=None, cutout=None, logo=None, size=(1080, 1350), style=Style(cfg))
    assert img.size == (1080, 1350)
