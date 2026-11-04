#!/usr/bin/env python3
"""Bygg syntetiske skjermbilder og fasit lokalt. Ingen eksterne kall."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import platform
from pathlib import Path
import PIL
from PIL import Image, ImageDraw, ImageFont
from case_specs import CASES

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("visit_date", "teeth", "diagnosis_codes", "diagnosis_text", "treatments",
          "treatment_by_tooth", "treatment_status", "symptoms", "support_point",
          "duration_minutes", "recorded_tariffs", "historical_tariffs", "historical_teeth",
          "findings", "prior_501_year", "prior_101_today")
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

def sha(b): return hashlib.sha256(b).hexdigest()
def font(path, size):
    if not path.is_file():
        raise SystemExit(f"Mangler font {path}. Installer DejaVu Sans, eller angi lokal font i generatoren.")
    return ImageFont.truetype(str(path), size)

def wrap(draw, text, chosen_font, maxwidth):
    words = text.split()
    result, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if line and draw.textlength(candidate, font=chosen_font) > maxwidth:
            result.append(line); line = word
        else: line = candidate
    if line: result.append(line)
    return result

def render(case, output):
    variant = case["appearance"]
    w, h = (1100, 1100) if variant == "small" else (1440, 1040)
    image = Image.new("RGB", (w, h), "#e8eef1")
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, w, 68), fill="#17344a")
    d.rounded_rectangle((45, 96, w-45, h-48), radius=14, fill="#ffffff", outline="#d2dce3", width=2)
    body = font(FONT, 24 if variant == "small" else 26)
    top = font(BOLD, 23)
    title = font(BOLD, 30)
    d.text((55, 20), "CLINAXIA TEST | SYNTETISKE DATA", font=top, fill="#ffffff")
    x, y = 79, 125
    transcript = ["CLINAXIA TEST | SYNTETISKE DATA"]
    fixed = ["SYNTETISK TESTDATA - INGEN PASIENT", f"TEST-ID: {case['case_id']}",
             f"JOURNALOVERSIKT: {case['title']}"]
    for index, line in enumerate(fixed):
        chosen = title if index == 0 else body
        for part in wrap(d, line, chosen, w-160):
            d.text((x,y), part, font=chosen, fill="#17344a"); transcript.append(part); y += 39
    d.line((x, y+4, w-80, y+4), fill="#d7e1e7", width=2); y += 25
    for row_index, row in enumerate(case["rows"]):
        line = f"{row['label']}: {row['display']}"
        parts=wrap(d,line,body,w-160)
        if variant=="table" and row_index%2==0:
            d.rounded_rectangle((x-9,y-4,w-80,y+len(parts)*35+3),radius=5,fill="#f2f6f8")
        for part in parts:
            d.text((x,y), part, font=body, fill="#243947"); transcript.append(part); y += 35
        y += 13
    if y > h-95: raise ValueError(f"Skjermbilde klippes: {case['case_id']} y={y}")
    if variant == "jpeg":
        memory=io.BytesIO(); image.save(memory, format="JPEG", quality=42, subsampling=2)
        memory.seek(0); image=Image.open(memory).convert("RGB")
    elif variant == "small":
        image=image.resize((round(w*.68),round(h*.68)), Image.Resampling.LANCZOS)
    image.save(output, format="PNG", optimize=False)
    return "\n".join(transcript)+"\n"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT/"data")
    args=parser.parse_args(); dest=args.out.resolve(); (dest/"images").mkdir(parents=True,exist_ok=True)
    items=[]; hashes={}
    for case in CASES:
        cid=case["case_id"]; image_path=dest/"images"/(cid+".png")
        transcript=render(case,image_path)
        fields={name:{"state":"not_documented"} for name in FIELDS}
        for row in case["rows"]:
            if row["key"] not in fields: raise ValueError(row["key"])
            fields[row["key"]]={"state":row["state"],"value":row["value"],"evidence":row["evidence"]}
        items.append({"schema_version":"2.0", "case_id":cid, "split":case["split"], "group":case["group"],
                      "image":f"images/{cid}.png", "appearance":case["appearance"],
                      "reference_transcript":transcript, "fields":fields,
                      "policy":case["policy"],"note":case["note"],
                      "synthetic":True})
        hashes[f"images/{cid}.png"]=sha(image_path.read_bytes())
    cases_path=dest/"cases.jsonl"
    cases_path.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in items),encoding="utf-8")
    hashes["cases.jsonl"]=sha(cases_path.read_bytes())
    tariffs="https://www.helsedirektoratet.no/rundskriv/kapittel-5-stonad-ved-helsetjenester/takster-for-tannbehandling-"
    rules={"retrieved_date":"2026-11-04", "scope":"Utvalgte testregler; ikke komplett regelmotor eller refusjonsbeslutning.",
           "caveat":"Løpende nettside. Kontroller gjeldende og datorelevante regler før bruk; fasit er ikke faglig uavhengig godkjent.",
           "sources":[
               {"source_id":"HELFO-2026-T101","official_url":tariffs,"source_effective_date":"2026-01-01","check":"101: minimum 20 minutter; repetisjon én gang ved over 40 minutter; kan ikke kombineres med 207."},
               {"source_id":"HELFO-2026-T501","official_url":tariffs,"source_effective_date":"2026-01-01","check":"501: minimum 30 minutter; repetisjon for hvert 30. minutt fra 60 minutter; maksimalt 14 per kalenderår."},
               {"source_id":"HELFO-2026-T801-802-804","official_url":tariffs,"source_effective_date":"2026-01-01","check":"801: laboratorieprøve. 802: tannrøntgen. 804: panorama, med vilkår."},
               {"source_id":"ICD10-K02.1","official_url":"https://classbrowser.nhs.uk/ICD-10-5TH-Edition/vol1/block-k00-k14.htm","check":"K02.1 er karies i dentin; norsk kodeverk for relevant år må kontrolleres særskilt."}]}
    rules_path=dest/"helfo_rules_reference.json"
    rules_path.write_text(json.dumps(rules,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    hashes["helfo_rules_reference.json"]=sha(rules_path.read_bytes())
    manifest={"schema_version":"2.0","source":"case_specs.py", "case_count":len(items),
              "splits":{k:sum(c["split"]==k for c in items) for k in ("development","validation","test")},
              "generator":{"python":platform.python_version(),"pillow":PIL.__version__,
                           "font_sha256":sha(FONT.read_bytes()),"font_bold_sha256":sha(BOLD.read_bytes()),
                           "note":"Deterministisk med samme kilde, Python/Pillow og fontfiler; sjekk hasher."},
              "sha256":hashes}
    (dest/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Genererte {len(items)} syntetiske case i {dest}")
if __name__=="__main__": main()
