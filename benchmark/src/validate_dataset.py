#!/usr/bin/env python3
"""Kontroller integritet, fasitbevis og syntetiske felt uten nettverk."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from evaluate import ROOT, load_jsonl, norm

def validate(path):
    base=Path(path).resolve(); manifest=json.loads((base/"manifest.json").read_text(encoding="utf-8"))
    problems=[]
    for rel,expected in manifest["sha256"].items():
        file=(base/rel).resolve()
        if not file.is_relative_to(base): problems.append(f"Ugyldig sti: {rel}"); continue
        if not file.is_file(): problems.append(f"Mangler fil: {rel}"); continue
        if hashlib.sha256(file.read_bytes()).hexdigest()!=expected: problems.append(f"Feil SHA-256: {rel}")
    cases=load_jsonl(base/"cases.jsonl")
    ids=set(); groups={}
    rules=json.loads((base/"helfo_rules_reference.json").read_text(encoding="utf-8"))
    sources={s["source_id"] for s in rules.get("sources",[])}
    for c in cases:
        cid=c.get("case_id")
        if cid in ids: problems.append(f"Duplisert case: {cid}")
        ids.add(cid)
        if c.get("synthetic") is not True: problems.append(f"Mangler syntetisk merking: {cid}")
        if c.get("policy",{}).get("eligibility")!="unverified": problems.append(f"Ugyldig refusjonsstatus: {cid}")
        group=c.get("group")
        if group in groups and groups[group]!=c["split"]: problems.append(f"Casegruppe fordelt på flere split: {group}")
        groups[group]=c["split"]
        policy=c["policy"]
        for source in policy.get("source_ids",[]):
            if source not in sources: problems.append(f"Ukjent kilde-ID i {cid}: {source}")
        for code,qty in policy.get("required_review_quantities",{}).items():
            if code not in policy.get("required_review_codes",[]) or not isinstance(qty,int) or isinstance(qty,bool) or qty<1:
                problems.append(f"Ugyldig forventet kandidatantall: {cid}/{code}")
        image=(base/c["image"]).resolve()
        if not image.is_relative_to(base) or not image.is_file(): problems.append(f"Ugyldig bildesti: {cid}")
        transcript=norm(c["reference_transcript"])
        if re.search(r"(?<!\d)\d{11}(?!\d)",transcript): problems.append(f"Mulig 11-sifret personnummer: {cid}")
        for field, data in c["fields"].items():
            if field in {"teeth","historical_teeth"} and data.get("state")!="not_documented":
                for value in data.get("value",[]):
                    if not re.fullmatch(r"(?:[1-4][1-8]|[5-8][1-5])",value): problems.append(f"Ugyldig FDI-tannnummer: {cid}/{value}")
            for e in data.get("evidence",[]):
                if norm(e) not in transcript: problems.append(f"Evidens mangler i transkripsjon: {cid}/{field}: {e}")
    if len(cases)!=manifest["case_count"]: problems.append("Antall case samsvarer ikke med manifest")
    actual={s:sum(c["split"]==s for c in cases) for s in manifest["splits"]}
    if actual!=manifest["splits"]: problems.append("Datasett-split samsvarer ikke med manifest")
    return problems

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--data",type=Path,default=ROOT/"data"); args=p.parse_args()
    issues=validate(args.data)
    if issues: raise SystemExit("Datasettet har feil:\n"+"\n".join(issues))
    print("Datasettets hasher, evidens, split og syntetiske merking er kontrollert.")
if __name__=="__main__": main()
