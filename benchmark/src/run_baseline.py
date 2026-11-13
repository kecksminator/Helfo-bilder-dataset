#!/usr/bin/env python3
"""Kjør lokal demonstrasjon med Tesseract. Dette er IKKE Clinaxia eller klinisk regelmotor."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from evaluate import ROOT, load_jsonl

LABELS={"dato":"visit_date", "tenner":"teeth", "diagnosekode":"diagnosis_codes",
        "diagnose":"diagnosis_text", "tiltak":"treatments", "status":"treatment_status",
        "symptomer":"symptoms", "stønadspunkt":"support_point", "tidsbruk":"duration_minutes",
        "registrert takst":"recorded_tariffs", "tidligere takst":"historical_tariffs", "tann og tiltak":"treatment_by_tooth",
        "tidligere tenner":"historical_teeth", "funn":"findings", "tidligere 501 i år":"prior_501_year",
        "tidligere 101 i dag":"prior_101_today"}

def val(v): return {"state":"known","value":v}
def parse(text):
    fields={}; flags={"eligibility_unverified"}
    lines=[]
    for line in text.splitlines():
        if not line.strip(): continue
        label=line.split(":",1)[0].strip().casefold() if ":" in line else ""
        if label in LABELS: lines.append(line)
        elif lines and ":" not in line: lines[-1]+=" "+line.strip()
    for line in lines:
        if ":" not in line: continue
        label,raw=line.split(":",1); key=LABELS.get(label.strip().casefold()); raw=raw.strip()
        if not key or not raw: continue
        low=raw.casefold()
        if key=="visit_date":
            dates=re.findall(r"\b\d{4}-\d{2}-\d{2}\b",raw)
            if len(dates)==1: fields[key]=val(dates[0])
            elif len(dates)>1:
                fields[key]={"state":"conflict","value":dates}; flags.add("conflicting_date")
        elif key in ("teeth","historical_teeth"):
            nums=re.findall(r"\b[1-8][1-8]\b",raw)
            if nums:
                if "usikkert" in low or "eller" in low:
                    fields[key]={"state":"uncertain","value":nums}; flags.add("uncertain_tooth")
                else: fields[key]=val(nums)
        elif key=="diagnosis_codes":
            codes=re.findall(r"\b[A-Z]\d{2}\.\d\b",raw.upper())
            if codes: fields[key]=val(codes)
        elif key=="diagnosis_text":
            if low.startswith("mulig "):
                fields[key]={"state":"uncertain","value":raw[6:]}; flags.add("uncertain_diagnosis")
            else: fields[key]=val(raw)
        elif key in ("treatments","symptoms","treatment_by_tooth"):
            fields[key]=val([s.strip() for s in raw.split(";") if s.strip()])
        elif key in ("recorded_tariffs","historical_tariffs"):
            values=re.findall(r"\b\d{1,3}\b",raw)
            if values: fields[key]=val(values)
        elif key in ("duration_minutes","prior_501_year","prior_101_today"):
            m=re.search(r"\b\d+\b",raw)
            if m: fields[key]=val(int(m.group()))
        elif key=="support_point":
            if re.fullmatch(r"\d{1,2}[a-z]?",low): fields[key]=val(low)
        else: fields[key]=val(raw)
        if key in fields: fields[key]["evidence"]=[raw]
    if "support_point" not in fields: flags.add("missing_support_point")
    if "diagnosis_text" not in fields and "diagnosis_codes" not in fields: flags.add("missing_diagnosis")
    if fields.get("treatment_status",{}).get("value","").casefold()=="planlagt": flags.add("treatment_not_performed")
    procedures=[x.casefold() for x in fields.get("treatments",{}).get("value",[])]
    preventive="forebyggende behandling" in procedures and "individuell egenomsorgsopplæring" in procedures
    duration=fields.get("duration_minutes",{}).get("value")
    point=fields.get("support_point",{}).get("value")
    recorded=fields.get("recorded_tariffs",{}).get("value",[])
    suggestions=[]
    if preventive:
        if duration is None: flags.add("missing_duration")
        if isinstance(duration,int) and duration<20: flags.add("duration_below_101_minimum")
        if "207" in recorded: flags.add("tariff_101_207_conflict")
        if isinstance(duration,int) and duration>=20 and point in {"1","4","10","14"} and "207" not in recorded:
            s={"code":"101","status":"review"}
            if "prior_101_today" in fields: s["quantity"]=max(0,(2 if duration>40 else 1)-fields["prior_101_today"]["value"])
            suggestions.append(s)
    periodontal="systematisk periodontal behandling" in procedures and "subgingival depurasjon" in procedures
    prior=fields.get("prior_501_year",{}).get("value")
    if periodontal:
        if isinstance(duration,int) and duration<30: flags.add("duration_below_501_minimum")
        if isinstance(prior,int) and prior>=14: flags.add("annual_501_cap_reached")
        if isinstance(duration,int) and duration>=30 and isinstance(prior,int) and prior<14:
            suggestions.append({"code":"501","status":"review","quantity":min(duration//30,14-prior)})
    if "tannrøntgen" in procedures and fields.get("support_point",{}).get("value"):
        suggestions.append({"code":"802","status":"review"})
    if "panoramarøntgen" in procedures and "oversikt over begge kjever" in fields.get("findings",{}).get("value",""):
        suggestions.append({"code":"804","status":"review"})
    if "prøvetaking til laboratorieundersøkelse" in procedures:
        suggestions.append({"code":"801","status":"review"})
    if "801" in recorded and "prøvetaking til laboratorieundersøkelse" not in procedures:
        flags.add("check_801_sampling_documentation")
    diagnosis_suggestions=[]
    if fields.get("diagnosis_text",{}).get("state")=="known" and fields["diagnosis_text"].get("value","").casefold()=="dentinkaries" and "diagnosis_codes" not in fields:
        diagnosis_suggestions.append({"code":"K02.1","status":"review"})
    return {"fields":fields,"suggestions":suggestions,"diagnosis_suggestions":diagnosis_suggestions,"flags":sorted(flags)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,default=ROOT/"data/cases.jsonl")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/baseline.jsonl")
    p.add_argument("--lang",default="eng",help="Tesseract-språk, f.eks. nor eller eng; norsk anbefales")
    p.add_argument("--psm",default="6")
    args=p.parse_args(); rows=[]
    for case in load_jsonl(args.dataset):
        image=args.dataset.parent/case["image"]
        try:
            result=subprocess.run(["tesseract",str(image),"stdout","-l",args.lang,"--psm",args.psm],
                                  capture_output=True,text=True,check=True)
        except (FileNotFoundError,subprocess.CalledProcessError) as exc:
            raise SystemExit(f"Tesseract feilet for {case['case_id']}: {exc}. Kontroller installasjon og språkpakke.")
        ocr=result.stdout
        rows.append({"case_id":case["case_id"],"ocr_text":ocr,
                     "image_output":parse(ocr),"reference_output":parse(case["reference_transcript"])})
        print(f"OCR: {case['case_id']}",flush=True)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
    version=subprocess.run(["tesseract","--version"],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    lang_listing=subprocess.run(["tesseract","--list-langs"],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    match=re.search(r'"([^"]+)"',lang_listing)
    models={}
    if match:
        for lang in args.lang.split("+"):
            trained=Path(match.group(1))/(lang+".traineddata")
            if trained.is_file(): models[lang]=hashlib.sha256(trained.read_bytes()).hexdigest()
    manifest=args.dataset.parent/"manifest.json"
    (args.out.parent/(args.out.stem+"_meta.json")).write_text(json.dumps({"engine":version,"language":args.lang,"psm":args.psm,
        "language_model_sha256":models,"cases_sha256":hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None,
        "omp_thread_limit":os.environ.get("OMP_THREAD_LIMIT"),
        "description":"Lokal syntetisk demonstrasjon, ikke Clinaxia."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
