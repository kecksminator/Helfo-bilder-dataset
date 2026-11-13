#!/usr/bin/env python3
"""Kjør testbilder gjennom en adapter utvikleren selv kobler til Clinaxia."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
from evaluate import ROOT, load_jsonl, validate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adapter",required=True,help="Python-modul med ocr_image(path) og interpret_text(text)")
    p.add_argument("--revision",required=True,help="Applikasjons-/modellversjon for sporbarhet")
    p.add_argument("--dataset",type=Path,default=ROOT/"data/cases.jsonl")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/clinaxia.jsonl")
    args=p.parse_args(); cases=load_jsonl(args.dataset); adapter=importlib.import_module(args.adapter)
    for method in ("ocr_image","interpret_text"):
        if not callable(getattr(adapter,method,None)): raise SystemExit(f"Adapteren mangler funksjonen {method}")
    rows=[]
    for c in cases:
        image=(args.dataset.parent/c["image"]).resolve()
        ocr=adapter.ocr_image(image)
        if not isinstance(ocr,str): raise TypeError("ocr_image må returnere en streng")
        # Bare bilde/tekst sendes inn. Fasitsvar og policy gis aldri til adapteren.
        rows.append({"case_id":c["case_id"],"ocr_text":ocr,
                     "image_output":adapter.interpret_text(ocr),
                     "reference_output":adapter.interpret_text(c["reference_transcript"])})
        print(f"Fullført: {c['case_id']}",flush=True)
    validate(cases,rows)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
    manifest=args.dataset.parent/"manifest.json"
    (args.out.parent/(args.out.stem+"_meta.json")).write_text(json.dumps({"adapter":args.adapter,"revision":args.revision,
       "cases_sha256":hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
       "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None,
       "note":"Syntetiske data; ingen klinisk gyldighetsvurdering."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
