# Task: analysis

## Instructions
You are a senior social media strategist analysing a brand's Instagram presence before planning new posts.

You receive:
- the client brief,
- product facts scraped from the official webshop (schema.org data and FAQ — treat these as verified),
- screenshots of the brand's Instagram profile and individual posts (filenames are given before each image).

Produce a brand analysis. Rules:
- Base every claim on what you actually see or read. In `verified_facts`, each claim must name its source: a URL from the product facts or a screenshot filename.
- Anything you infer (audience age, strategy, why a post performed) goes into `assumptions`, not `verified_facts`.
- Engagement: compare likes only with care — note post age when visible; a post a few hours old is not comparable to a week-old one.
- Palette: give hex values of the dominant brand colours you observe.
- Typography: describe the headline lettering you see (weight, width, case, colour use).
- `opportunities`: concrete gaps or angles the brand under-uses that fit its identity.
- Write all prose in the brief's language (en).



## Brief
{
  "brand": "GymBeam Croatia",
  "instagram": "https://www.instagram.com/gymbeamhr/",
  "website": "https://gymbeam.hr/",
  "why_this_brand": "Suggested brand in the assignment. Large own-label range (no third-party trademarks on packaging), an active and varied Instagram with a clear visual identity (orange + dark backgrounds) and a habit of trend content.\n",
  "products": [
    {
      "url": "https://gymbeam.hr/kreatin1-monohidrat-gymbeam.html",
      "note": "creatine monohydrate, a recurring \"hero\" of their posts",
      "packshot": "creatine-monohydrate-unflavoured-mockup-view1_5"
    },
    {
      "url": "https://gymbeam.hr/protein-just-whey-gymbeam.html",
      "note": "GymBeam's main whey in the Croatian shop (True Whey is not sold there)",
      "packshot": "just_whey_chocolate_milkshake_1_kg_gymbeam_1"
    }
  ],
  "audience": "Croatia, 18-35, gym-goers and recreational athletes who are starting with supplements or want a trusted, affordable option. They follow fitness influencers and like humour and trends.\n",
  "goals": [
    "Post 1: education -> saves and shares (carousel)",
    "Post 2: product showcase -> purchase intent (single image)",
    "Post 3: trend/fun -> reactions and comments (reel)"
  ],
  "preferred_formats": [
    "carousel",
    "image",
    "reel"
  ],
  "inspiration": "Their own retro neon / Miami illustration post (inputs/instagram/01_gta_trend.png, 2,147 likes, far above the profile average). We want a follow-up to that trend, with the real product in frame and no people. Educational carousels like \"Zodiac signs as GymBeam products\".\n",
  "season": "December 2026 - holiday season (the MERRY FITMAS advent calendar is live on the profile).",
  "constraints": [
    "No people in the images.",
    "Do not invent prices, discounts, codes, product properties or quotes from real people.",
    "Logo, packaging and label must stay accurate.",
    "No video game titles, logos or fonts (the style may be inspired by the genre, not copied)."
  ],
  "language": "en",
  "references_dir": "inputs/instagram"
}

## Verified product facts (webshop)
### 100% Kreatin - GymBeam
id: kreatin1-monohidrat-gymbeam
url: https://gymbeam.hr/kreatin1-monohidrat-gymbeam.html
category: Suplementi > Kreatin > Kreatin Monohidrat > 100% Kreatin - GymBeam
description: 100% Kreatin monohidrat učinkovit je dodatak za povećanje fizičke izvedbe. Omogućit će vam da trenirate intenzivno, napravite više ponavljanja ili dulje sprintate.
price range (EUR, depends on pack size): 9.5 – 28.9
- Q: Kako djeluje kreatin?
  A: GymBeam 100% Creatine Monohydrate je formuliran za povećanje izvedbe tijekom kratkotrajnih, uzastopnih intervala intenzivnog vježbanja. Ovaj jednosastojni prah pruža 5 g kreatin monohidrata po dnevnoj dozi. Namijenjen je sportašima i aktivnim pojedincima čiji je primarni cilj poboljšanje izvedbe tijekom treninga snage ili sličnih aktivnosti visokog intenziteta. Proizvod također podržava sekundarne ciljeve poput dobivanja mišićne mase i oporavka.
- Q: Koliko kreatina trebam uzimati?
  A: Preporučena dnevna doza za GymBeam 100% Creatine Monohydrate je 5 grama. To odgovara jednoj mjerici praha, koju treba pomiješati s 250 ml vode. Savjetuje se uzimanje jedne doze dnevno. Nemojte prekoračiti maksimalnu dnevnu dozu od 5 g.
- Q: Kada je najbolje vrijeme za uzimanje kreatina?
  A: GymBeam 100% Creatine Monohydrate može se uzimati u bilo koje doba dana, jer je vrijeme uzimanja fleksibilno. Preporučena dnevna doza je 5 grama, koja se može konzumirati kada Vam odgovara. Mnogi ga miješaju s vodom ili dodaju u shake, ali dosljednost u svakodnevnom uzimanju važnija je od određenog vremena.
- Q: Uzrokuje li kreatin gubitak kose?
  A: GymBeam 100% Creatine Monohydrate je jednokomponentni dodatak koji pruža 5 g kreatin monohidrata u svakoj dozi. Individualne reakcije na dodatke prehrani mogu varirati. Iako je kreatin široko proučavan zbog svojih učinaka na izvedbu, ako imate specifične brige o mogućim nuspojavama poput gubitka kose, najbolje je da o njima razgovarate sa svojim liječnikom ili kvalificiranim zdravstvenim djelatnikom.
- Q: Koje su prednosti kreatina za žene?
  A: GymBeam 100% Creatine Monohydrate je uniseks proizvod osmišljen za povećanje izvedbe tijekom kratkotrajnih intervala vježbanja visokog intenziteta. Pruža 5 g čistog kreatin monohidrata po dozi. Za žene koje se bave treningom snage ili drugim intenzivnim aktivnostima, služi istom primarnom cilju podrške izvedbi. Proizvod je također namijenjen pomoći u sekundarnim ciljevima kao što su dobivanje mišićne mase i oporavak za svakog korisnika.
- Q: Zašto tekstura kreatin monohidrata može varirati između serija?
  A: Praškasti oblik proizvoda 100% Creatine Monohydrate - GymBeam može pokazivati neznatne varijacije u teksturi ili finoći između različitih proizvodnih serija. Ove manje fizičke razlike u veličini čestica normalan su aspekt proizvodnje praha i ne mijenjaju sastav proizvoda. Svaka doza od 5 g dosljedno pruža navedenu količinu čistog kreatin monohidrata, što je potvrđeno laboratorijskim testiranjem.
- Q: Sadrži li pakiranje kreatin monohidrata mjericu?
  A: Pakiranje proizvoda 100% Creatine Monohydrate - GymBeam trebalo bi sadržavati mjericu. Upute za upotrebu proizvoda navode dozu od „1 mjerica (5 g)”, što ukazuje da je osiguran alat za mjerenje ove točne količine kako bi se osigurale točne i dosljedne dnevne doze.
### Just Whey Grass-Fed Protein – GymBeam
id: protein-just-whey-gymbeam
url: https://gymbeam.hr/protein-just-whey-gymbeam.html
category: Proteini > Whey protein sirutke > Proteinski koncentrati > Just Whey Grass-Fed Protein – GymBeam 
description: Just Whey je protein sirutke iz mlijeka krava hranjenih travom, proizveden u Njemačkoj. Najmanje 22 g bjelančevina i 6,5 g BCAA po dozi, enzimi DigeZyme® i mikronutrijenti. Laboratorijski ispitan.
price range (EUR, depends on pack size): 1.95 – 73.95
- Q: Koliko proteina sadrži jedna mjerica proizvoda Just Whey?
  A: Svaka mjerica od 30 g proizvoda Just Whey Grass-Fed Protein – GymBeam pruža 22,5 g proteina. Ova veličina serviranja osmišljena je za učinkovitu nadopunu Vašeg dnevnog unosa proteina. Formula je višekomponentna mješavina koja kombinira koncentrat, izolat i hidrolizat proteina sirutke. Maksimalna preporučena dnevna doza je 90 g, što odgovara trima mjericama.
- Q: Koje su prednosti whey proteina od krava s pašne ispaše?
  A: Just Whey Grass-Fed Protein – GymBeam formuliran je s proteinom sirutke dobivenim od krava s pašne ispaše. Proizvod kombinira tri vrste proteina sirutke – koncentrat, izolat i hidrolizat – i obrađuje se pomoću membranske ultrafiltracije. Svako serviranje pruža 22,5 g proteina i obogaćeno je mješavinom DigeZyme® od šest probavnih enzima. Formula također uključuje cink, magnezij te vitamine B6 i E kako bi se nadopunio njezin nutritivni profil.
- Q: Koliko vode ili mlijeka trebam koristiti za miješanje jedne mjerice proizvoda Just Whey?
  A: Za pripremu proizvoda Just Whey Grass-Fed Protein – GymBeam, pomiješajte jednu mjericu od 30 g s 200 – 300 ml vode. Možete ga pomiješati i s mlijekom za kremastiju teksturu. Dobro protresite kako biste osigurali glatku konzistenciju. Ova količina tekućine preporučuje se za postizanje željenog okusa i teksture proteinskog shakea.
- Q: Dolazi li Just Whey protein s mjericom?
  A: Just Whey Grass-Fed Protein – GymBeam uključuje mjericu kako bi se osiguralo točno mjerenje preporučenog serviranja od 30 g. Korištenje priložene mjerice pomaže Vam da dosljedno pripremate svoj shake s 22,5 g proteina po serviranju, kako je navedeno u nutritivnim informacijama. Uvijek provjerite unutar pakiranja jer se mjerica može slegnuti tijekom transporta.
- Q: Koji su glavni sastojci u proizvodu Just Whey Grass-Fed Protein?
  A: Glavne komponente proizvoda Just Whey Grass-Fed Protein – GymBeam su mješavina koncentrata, izolata i hidrolizata proteina sirutke, svi dobiveni iz mlijeka krava s pašne ispaše. Formula je poboljšana kompleksom probavnih enzima DigeZyme®, bromelainom, esencijalnim mineralima poput cinka i magnezija te vitaminima E i B6. Također se koriste sladila poput sukraloze i steviol glikozida.
- Q: Može li Just Whey pomoći pri mršavljenju?
  A: Jedno serviranje proizvoda Just Whey Grass-Fed Protein – GymBeam sadrži 22,5 g proteina i 2,2 g šećera. Protein je važan makronutrijent za uravnoteženu prehranu. Ovaj proizvod je primarno formuliran za dobivanje mišićne mase i oporavak te nije zamjena za raznoliku prehranu. Svaki plan za kontrolu tjelesne težine trebao bi biti sveobuhvatan, uključujući i prehranu i vježbanje.
- Q: Zašto protein sirutke može uzrokovati osjećaj težine ili nadutosti?
  A: Just Whey Grass-Fed Protein – GymBeam sadrži mješavinu proteina sirutke i nije proizvod bez laktoze, što može biti čimbenik probavne osjetljivosti kod nekih pojedinaca. Za podršku probavi, formula je poboljšana s DigeZyme®, patentiranim kompleksom probavnih enzima koji uključuje laktazu. Iako je ovaj dodatak namijenjen poboljšanju tolerancije, individualne reakcije mogu varirati. Za bilo kakvu trajnu nelagodu, posavjetujte se sa svojim liječnikom ili nutricionistom.

## Unavailable sources
Instagram was not scraped (login wall and terms of use); the analysis uses manually saved screenshots.

## Instagram screenshots

[Image: 01_gta_trend.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\01_gta_trend.png`

[Image: 02_profile_grid_full.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\02_profile_grid_full.png`

[Image: 03_profile_grid_recent.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\03_profile_grid_recent.png`

[Image: 04_merry_fitmas_reel.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\04_merry_fitmas_reel.png`

[Image: 05_black_friday.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\05_black_friday.png`

[Image: 06_food10_carousel.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\06_food10_carousel.png`

[Image: 07_horoscope_carousel.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\07_horoscope_carousel.png`

[Image: 08_zanamari_collab.png] -> view file `C:\Users\kova\sekvenca\inputs\instagram\08_zanamari_collab.png`


## Output
Write JSON matching this schema to `C:\Users\kova\sekvenca\runs\gymbeam-demo\agent\analysis.json`:
```json
{
 "$defs": {
  "Evidence": {
   "properties": {
    "claim": {
     "title": "Claim",
     "type": "string"
    },
    "source": {
     "description": "URL or screenshot filename the claim is based on",
     "title": "Source",
     "type": "string"
    }
   },
   "required": [
    "claim",
    "source"
   ],
   "title": "Evidence",
   "type": "object"
  }
 },
 "properties": {
  "summary": {
   "title": "Summary",
   "type": "string"
  },
  "tone_of_voice": {
   "items": {
    "type": "string"
   },
   "title": "Tone Of Voice",
   "type": "array"
  },
  "audience": {
   "title": "Audience",
   "type": "string"
  },
  "recurring_themes": {
   "items": {
    "type": "string"
   },
   "title": "Recurring Themes",
   "type": "array"
  },
  "visual_style": {
   "items": {
    "type": "string"
   },
   "title": "Visual Style",
   "type": "array"
  },
  "palette_hex": {
   "description": "3-6 dominant brand colours as #RRGGBB",
   "items": {
    "type": "string"
   },
   "title": "Palette Hex",
   "type": "array"
  },
  "typography": {
   "title": "Typography",
   "type": "string"
  },
  "product_presentation": {
   "title": "Product Presentation",
   "type": "string"
  },
  "people_presentation": {
   "title": "People Presentation",
   "type": "string"
  },
  "caption_patterns": {
   "description": "How captions are written: length, emojis, CTA, hashtags",
   "items": {
    "type": "string"
   },
   "title": "Caption Patterns",
   "type": "array"
  },
  "hashtags": {
   "items": {
    "type": "string"
   },
   "title": "Hashtags",
   "type": "array"
  },
  "engagement_observations": {
   "items": {
    "type": "string"
   },
   "title": "Engagement Observations",
   "type": "array"
  },
  "verified_facts": {
   "description": "Only facts directly visible in the sources",
   "items": {
    "$ref": "#/$defs/Evidence"
   },
   "title": "Verified Facts",
   "type": "array"
  },
  "assumptions": {
   "description": "Inferences that are NOT directly verified",
   "items": {
    "type": "string"
   },
   "title": "Assumptions",
   "type": "array"
  },
  "unavailable_sources": {
   "items": {
    "type": "string"
   },
   "title": "Unavailable Sources",
   "type": "array"
  },
  "opportunities": {
   "items": {
    "type": "string"
   },
   "title": "Opportunities",
   "type": "array"
  }
 },
 "required": [
  "summary",
  "tone_of_voice",
  "audience",
  "recurring_themes",
  "visual_style",
  "palette_hex",
  "typography",
  "product_presentation",
  "people_presentation",
  "caption_patterns",
  "hashtags",
  "engagement_observations",
  "verified_facts",
  "assumptions",
  "unavailable_sources",
  "opportunities"
 ],
 "title": "BrandAnalysis",
 "type": "object"
}
```