"""Pydantic schemas: the contract between phases.

Every phase writes one of these as JSON into the run directory, so a run can be
inspected, hand-edited (e.g. the plan) and resumed from any phase.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------- Phase 0: brief ----------


class ProductRef(BaseModel):
    url: str
    note: str = ""
    packshot: str = ""  # optional substring of the preferred gallery image filename


class Brief(BaseModel):
    brand: str
    instagram: str
    website: str
    why_this_brand: str = ""
    products: list[ProductRef]
    audience: str
    goals: list[str]
    preferred_formats: list[Literal["carousel", "image", "reel", "story"]] = ["carousel", "image", "reel"]
    inspiration: str = ""
    season: str = ""
    constraints: list[str] = []
    language: str = "hr"
    references_dir: str = "inputs/instagram"


# ---------- Phase 1: ingest (scraped facts, no LLM) ----------


class FAQ(BaseModel):
    question: str
    answer: str


class ProductFacts(BaseModel):
    """Facts taken verbatim from the shop's structured data (schema.org JSON-LD)."""

    id: str  # short slug used in plans, e.g. "kreatin1-monohidrat-gymbeam"
    url: str
    name: str
    description: str
    category: str = ""
    price_low_eur: float | None = None
    price_high_eur: float | None = None
    faq: list[FAQ] = []
    image_urls: list[str] = []
    local_images: list[str] = []  # downloaded packshots (relative to run dir)
    cutout: str | None = None  # packshot with background removed (PNG, alpha)


class Sources(BaseModel):
    products: list[ProductFacts]
    logo: str | None = None
    instagram_screenshots: list[str]
    unavailable: list[str] = []  # sources we tried and could not read


# ---------- Phase 2: brand analysis ----------


class Evidence(BaseModel):
    claim: str
    source: str = Field(description="URL or screenshot filename the claim is based on")


class BrandAnalysis(BaseModel):
    summary: str
    tone_of_voice: list[str]
    audience: str
    recurring_themes: list[str]
    visual_style: list[str]
    palette_hex: list[str] = Field(description="3-6 dominant brand colours as #RRGGBB")
    typography: str
    product_presentation: str
    people_presentation: str
    caption_patterns: list[str] = Field(description="How captions are written: length, emojis, CTA, hashtags")
    hashtags: list[str]
    engagement_observations: list[str]
    verified_facts: list[Evidence] = Field(description="Only facts directly visible in the sources")
    assumptions: list[str] = Field(description="Inferences that are NOT directly verified")
    unavailable_sources: list[str]
    opportunities: list[str]


# ---------- Phase 3: content plan ----------


class Frame(BaseModel):
    """One visual unit: a carousel slide, the single image, or one reel shot."""

    headline: str = Field(description="Short on-image headline in the post language; '' for none")
    subtext: str = Field(description="Optional smaller line under the headline; '' for none")
    highlight_word: str = Field(description="One word from the headline rendered in brand orange; '' for none")
    scene_prompt: str = Field(
        description="English prompt for the image model describing the background scene ONLY. "
        "No text, no logos, no people. Must leave the zone described in text_zone calm and empty."
    )
    product_id: str = Field(description="Product id to place in the frame, or '' for no product")
    product_mode: Literal["composite", "ai_edit", "none"] = Field(
        description="composite = real packshot pasted by code (label guaranteed exact); "
        "ai_edit = image model integrates the packshot (for stylised scenes); none = no product"
    )
    text_zone: Literal["top", "bottom", "center"] = "top"
    layout: Literal["photo", "dark_card"] = Field(
        description="photo = full-bleed generated scene; dark_card = brand dark background with "
        "text-first layout (good for educational slides)"
    )


class PostPlan(BaseModel):
    number: int
    format: Literal["carousel", "image", "reel"]
    goal: str
    concept: str
    rationale: str
    frames: list[Frame]
    caption_brief: str
    facts_used: list[str] = Field(description="Verified facts (verbatim from sources) the post relies on")


class ContentPlan(BaseModel):
    posts: list[PostPlan]


# ---------- Phase 4/5: production + QA ----------


class Caption(BaseModel):
    caption: str
    hashtags: list[str]
    alt_text: str


class QAResult(BaseModel):
    score: int = Field(description="Overall 1-10")
    product_accurate: bool = Field(description="Packaging/label/logo intact and undistorted, or no product expected")
    on_brand: bool
    text_legible: bool
    has_unwanted_text_or_people: bool
    issues: list[str]
    fix_for_image_model: str = Field(description="Concrete change to the scene prompt to fix the issues; '' if none")


class CaptionQA(BaseModel):
    ok: bool
    unsupported_claims: list[str] = Field(description="Claims not backed by the provided verified facts")
    suggested_fix: str
