#!/usr/bin/env python3
"""Evaluer transkripsjon og to separate tolkningsløp uten eksterne tjenester."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
VALID_STATES={"known","not_documented","uncertain","conflict"}
VALID_SUGGESTIONS={"review","confirmed","rejected"}
LIST_FIELDS={"teeth","historical_teeth","diagnosis_codes","treatments","treatment_by_tooth","symptoms","recorded_tariffs","historical_tariffs"}
INTEGER_FIELDS={"duration_minutes","prior_501_year","prior_101_today"}

def load_jsonl(path):
    result=[]
    with Path(path).open(encoding="utf-8") as fh:
        for n,line in enumerate(fh,1):
            if line.strip():
                try: result.append(json.loads(line))
                except json.JSONDecodeError as exc: raise ValueError(f"{path}:{n}: ugyldig JSON: {exc}") from exc
    return result

def norm(x): return " ".join(unicodedata.normalize("NFKC", str(x)).casefold().split())
def comparable(x):
    if isinstance(x,list): return sorted(comparable(a) for a in x)
    if isinstance(x,dict): return {k:comparable(v) for k,v in sorted(x.items())}
    if isinstance(x,str): return norm(x)
    return x
def dist(a,b):
    """Levenshtein, lineært minne. Fungerer for både tegn og ord."""
    if len(a)<len(b): a,b=b,a
    previous=list(range(len(b)+1))
    for i,ai in enumerate(a,1):
        current=[i]
        for j,bj in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(ai!=bj)))
        previous=current
    return previous[-1]
def ratio(a,b): return round(a/b,4) if b else None

def validate(cases,preds):
    by_case={}
    ids={c["case_id"] for c in cases}
    if len(ids)!=len(cases): raise ValueError("Duplisert case-ID i datasett")
    legal=set(cases[0]["fields"]) if cases else set()
    for p in preds:
        cid=p.get("case_id")
        if cid not in ids: raise ValueError(f"Ukjent case-ID i prediksjon: {cid!r}")
        if cid in by_case: raise ValueError(f"Duplisert prediksjon: {cid}")
        if "ocr_text" in p and not isinstance(p["ocr_text"],str): raise ValueError(f"{cid}: ocr_text må være tekst")
        for mode in ("image_output","reference_output"):
            if mode not in p: continue
            out=p[mode]
            if not isinstance(out,dict): raise ValueError(f"{cid}: {mode} må være et objekt")
            fields=out.get("fields",{})
            if not isinstance(fields,dict): raise ValueError(f"{cid}: fields må være et objekt")
            for k,v in fields.items():
                if k not in legal: raise ValueError(f"{cid}: ukjent felt {k}")
                if not isinstance(v,dict) or v.get("state") not in VALID_STATES: raise ValueError(f"{cid}: ugyldig feltstatus {k}")
                if v["state"] != "not_documented" and ("value" not in v or v["value"] is None or v["value"]=="" or v["value"]==[]): raise ValueError(f"{cid}: verdi mangler for {k}")
                if v["state"] == "not_documented" and v.get("value") not in (None,[],""): raise ValueError(f"{cid}: udokumentert felt kan ikke ha en verdi: {k}")
                value=v.get("value")
                if v["state"]!="not_documented":
                    if k in LIST_FIELDS and (not isinstance(value,list) or not all(isinstance(x,str) and x for x in value)): raise ValueError(f"{cid}: {k} må være en tekstliste")
                    if k in INTEGER_FIELDS and (isinstance(value,bool) or not isinstance(value,int) or value<0): raise ValueError(f"{cid}: {k} må være et ikke-negativt heltall")
                    if k not in LIST_FIELDS|INTEGER_FIELDS and not (isinstance(value,str) or (k=="visit_date" and v["state"] in {"uncertain","conflict"} and isinstance(value,list) and all(isinstance(x,str) for x in value))): raise ValueError(f"{cid}: ugyldig type for {k}")
                evidence=v.get("evidence",[])
                if not isinstance(evidence,list) or not all(isinstance(x,str) and x.strip() for x in evidence): raise ValueError(f"{cid}: evidence må være en liste med ikke-tomme tekstbiter")
                confidence=v.get("confidence")
                if confidence is not None and (isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0<=confidence<=1): raise ValueError(f"{cid}: ugyldig confidence i {k}")
            suggestions=out.get("suggestions",[])
            if not isinstance(suggestions,list): raise ValueError(f"{cid}: suggestions må være en liste")
            seen=set()
            for s in suggestions:
                if not isinstance(s,dict) or not isinstance(s.get("code"),str) or s.get("status") not in VALID_SUGGESTIONS: raise ValueError(f"{cid}: ugyldig takstforslag")
                if s["code"] in seen: raise ValueError(f"{cid}: duplisert takstforslag {s['code']}")
                if "quantity" in s and (isinstance(s["quantity"],bool) or not isinstance(s["quantity"],int) or s["quantity"]<1): raise ValueError(f"{cid}: quantity må være et positivt heltall")
                seen.add(s["code"])
            diagnoses=out.get("diagnosis_suggestions",[])
            if not isinstance(diagnoses,list): raise ValueError(f"{cid}: diagnosis_suggestions må være en liste")
            codes=set()
            for d in diagnoses:
                if not isinstance(d,dict) or not isinstance(d.get("code"),str) or not d["code"] or d.get("status") not in VALID_SUGGESTIONS: raise ValueError(f"{cid}: ugyldig diagnoseforslag")
                if d["code"] in codes: raise ValueError(f"{cid}: duplisert diagnoseforslag")
                codes.add(d["code"])
            if not isinstance(out.get("flags",[]),list) or not all(isinstance(x,str) for x in out.get("flags",[])): raise ValueError(f"{cid}: flags må være en tekstliste")
        by_case[cid]=p
    return by_case

def score_output(case,out,input_text=None):
    m=Counter(); errors=[]; provided=out.get("fields",{})
    for name,expected in case["fields"].items():
        actual=provided.get(name,{"state":"not_documented"})
        es, astate=expected["state"], actual["state"]
        same=comparable(actual.get("value"))==comparable(expected.get("value"))
        if astate=="known":
            m["asserted_fields"]+=1
            evidence=actual.get("evidence",[])
            if not evidence: m["missing_evidence"]+=1
            elif input_text is not None and all(norm(e) in norm(input_text) for e in evidence): m["evidence_found_in_input"]+=1
            elif input_text is not None:
                m["invalid_evidence"]+=1
                errors.append({"field":name,"kind":"evidence_not_found_in_input","evidence":evidence})
        if es=="known":
            m["expected_known_fields"]+=1
            if astate=="known" and same: m["correct_known_fields"]+=1
            else:
                m["false_negative_fields"]+=1
                if astate=="known":
                    m["false_positive_fields"]+=1; m["wrong_values"]+=1
                    errors.append({"field":name,"kind":"wrong_value","expected":expected.get("value"),"observed":actual.get("value")})
                else:
                    m["omitted_known_fields"]+=1
                    errors.append({"field":name,"kind":"omitted_or_abstained","expected":expected.get("value"),"observed_state":astate})
        elif es in {"uncertain","conflict"}:
            m["source_uncertain_fields"]+=1
            if astate==es and same: m["proper_uncertainty_fields"]+=1
            elif astate=="known":
                m["false_positive_fields"]+=1; m["false_certainty_fields"]+=1
                errors.append({"field":name,"kind":"false_certainty","expected_state":es,"observed":actual.get("value")})
            else:
                m["unresolved_uncertainty_fields"]+=1
                errors.append({"field":name,"kind":"uncertainty_not_preserved","expected_state":es,"observed_state":astate})
        elif astate=="known":
            m["false_positive_fields"]+=1; m["unsupported_field_assertions"]+=1
            errors.append({"field":name,"kind":"unsupported_assertion","observed":actual.get("value")})
        elif astate in {"uncertain","conflict"} and actual.get("value") not in (None,[],""):
            m["unsupported_uncertain_hypotheses"]+=1
            errors.append({"field":name,"kind":"unsubstantiated_uncertain_value","observed":actual.get("value")})
    suggestions=out.get("suggestions",[])
    present={s["code"] for s in suggestions if s["status"] in {"review","confirmed"}}
    confirmed={s["code"] for s in suggestions if s["status"]=="confirmed"}
    required=set(case["policy"].get("required_review_codes",[]))
    m["required_tariff_candidates"]+=len(required)
    m["identified_tariff_candidates"]+=len(present & required)
    m["missing_tariff_candidates"]+=len(required-present)
    m["unlabeled_tariff_candidates"]+=len(present-required)
    quantities=case["policy"].get("required_review_quantities",{})
    for code,expected_count in quantities.items():
        suggestion=next((s for s in suggestions if s["code"]==code and s["status"] in {"review","confirmed"}),None)
        m["required_tariff_quantities"]+=1
        if suggestion is None or "quantity" not in suggestion:
            m["missing_tariff_quantities"]+=1
            errors.append({"kind":"missing_tariff_quantity","code":code,"expected":expected_count})
        elif suggestion["quantity"]!=expected_count:
            m["wrong_tariff_quantities"]+=1
            errors.append({"kind":"wrong_tariff_quantity","code":code,"expected":expected_count,"observed":suggestion["quantity"]})
        else: m["correct_tariff_quantities"]+=1
    dx=out.get("diagnosis_suggestions",[])
    dx_present={x["code"] for x in dx if x["status"] in {"review","confirmed"}}
    dx_required=set(case["policy"].get("required_diagnosis_candidates",[]))
    m["required_diagnosis_candidates"]+=len(dx_required)
    m["identified_diagnosis_candidates"]+=len(dx_present & dx_required)
    m["unlabeled_diagnosis_candidates"]+=len(dx_present-dx_required)
    confirmed_dx={x["code"] for x in dx if x["status"]=="confirmed"}
    m["clinician_unreviewed_diagnosis_confirmations"]+=len(confirmed_dx)
    for code in sorted(confirmed_dx): errors.append({"kind":"unreviewed_diagnosis_confirmation","code":code})
    if case["policy"].get("eligibility")=="unverified":
        m["unverified_confirmed_tariffs"]+=len(confirmed)
        for code in sorted(confirmed): errors.append({"kind":"unverified_confirmed_tariff","code":code})
    forbidden=confirmed & set(case["policy"].get("forbidden_confirmed_codes",[]))
    m["confirmed_rule_conflicts"]+=len(forbidden)
    for code in sorted(forbidden): errors.append({"kind":"confirmed_tariff_conflicts_with_fixture","code":code})
    pair=set(case["policy"].get("conflicting_pair",[]))
    recorded=set(case["fields"].get("recorded_tariffs",{}).get("value",[]))
    if pair and pair<=confirmed|recorded and bool(pair & confirmed):
        m["confirmed_documented_conflicting_tariffs"]+=1
        errors.append({"kind":"confirmed_documented_conflicting_tariffs","codes":sorted(pair)})
    expected_flags=set(case["policy"].get("required_uncertainty_flags",[]))
    actual_flags=set(out.get("flags",[]))
    m["required_uncertainty_flags"]+=len(expected_flags)
    m["identified_uncertainty_flags"]+=len(expected_flags & actual_flags)
    for flag in sorted(expected_flags-actual_flags): errors.append({"kind":"missing_uncertainty_flag","flag":flag})
    return dict(m),errors

def aggregate(cases,preds,mode):
    totals=Counter(); details=[]; count=0; by_field={}; confidences=[]
    for case in cases:
        p=preds.get(case["case_id"],{}); out=p.get(mode)
        if out is None: continue
        input_text=p.get("ocr_text") if mode=="image_output" else case["reference_transcript"]
        m,err=score_output(case,out,input_text); totals.update(m); count+=1
        for name,expected in case["fields"].items():
            a=out.get("fields",{}).get(name,{"state":"not_documented"})
            fm=by_field.setdefault(name,Counter()); state=expected["state"]
            if a.get("state")=="known" and a.get("confidence") is not None:
                correct=int(state=="known" and comparable(a.get("value"))==comparable(expected.get("value")))
                confidences.append((a["confidence"],correct))
            if state=="known":
                fm["known_expected"]+=1
                if a["state"]=="known" and comparable(a.get("value"))==comparable(expected.get("value")): fm["correct"]+=1
                elif a["state"]=="known": fm["wrong_value"]+=1
                else: fm["omitted_or_abstained"]+=1
            elif state in {"uncertain","conflict"}:
                fm["uncertain_expected"]+=1
                if a["state"]==state and comparable(a.get("value"))==comparable(expected.get("value")): fm["uncertainty_preserved"]+=1
                elif a["state"]=="known": fm["false_certainty"]+=1
            elif a["state"]=="known": fm["unsupported_assertions"]+=1
        details.append({"case_id":case["case_id"],"split":case["split"],"counts":m,"errors":err})
    tp=totals["correct_known_fields"]; fp=totals["false_positive_fields"]; fn=totals["false_negative_fields"]
    buckets=[]
    for lo in range(10):
        selected=[(c,y) for c,y in confidences if lo/10<=c and (c<(lo+1)/10 or (lo==9 and c==1))]
        if selected: buckets.append({"bin":f"{lo/10:.1f}-{(lo+1)/10:.1f}","count":len(selected),
                                     "mean_confidence":round(sum(c for c,_ in selected)/len(selected),4),
                                     "observed_correct":round(sum(y for _,y in selected)/len(selected),4)})
    brier=round(sum((c-y)**2 for c,y in confidences)/len(confidences),4) if confidences else None
    ece=round(sum(b["count"]*abs(b["mean_confidence"]-b["observed_correct"]) for b in buckets)/len(confidences),4) if confidences else None
    return {"cases_evaluated":count,"cases_total":len(cases),"coverage":ratio(count,len(cases)),
            "counts":dict(totals), "field_precision":ratio(tp,tp+fp), "field_recall":ratio(tp,tp+fn),
            "required_candidate_recall":ratio(totals["identified_tariff_candidates"],totals["required_tariff_candidates"]),
            "diagnosis_candidate_recall":ratio(totals["identified_diagnosis_candidates"],totals["required_diagnosis_candidates"]),
            "uncertainty_flag_recall":ratio(totals["identified_uncertainty_flags"],totals["required_uncertainty_flags"]),
            "confidence_calibration":{"n":len(confidences),"brier":brier,"ece_10_bins":ece,"bins":buckets},
            "by_field":{name:{**dict(m),"known_recall":ratio(m["correct"],m["known_expected"])} for name,m in by_field.items()},
            "details":details}

def compare_paired(cases,preds):
    counts=Counter(); details=[]
    for case in cases:
        p=preds.get(case["case_id"],{})
        if "image_output" not in p or "reference_output" not in p: continue
        counts["paired_cases"]+=1
        for name,expected in case["fields"].items():
            if expected["state"]!="known": continue
            def correct(mode):
                a=p[mode].get("fields",{}).get(name,{"state":"not_documented"})
                return a["state"]=="known" and comparable(a.get("value"))==comparable(expected.get("value"))
            image_ok,reference_ok=correct("image_output"),correct("reference_output")
            key={(True,True):"both_correct",(False,True):"only_reference_correct",(True,False):"only_image_correct",(False,False):"both_incorrect"}[(image_ok,reference_ok)]
            counts[key]+=1; counts["known_fields_compared"]+=1
            if key!="both_correct": details.append({"case_id":case["case_id"],"field":name,"comparison":key})
    return {"counts":dict(counts),"details":details,
            "note":"Sammenlikner paret output, ikke bevis for årsak; krever like modellinnstillinger og kan påvirkes av nondeterminisme."}

def evaluate(cases,predictions):
    by=validate(cases,predictions)
    ct=wt=cd=wd=ev=evok=0; ocr=[]
    for case in cases:
        p=by.get(case["case_id"],{})
        if "ocr_text" not in p: continue
        ref=norm(case["reference_transcript"]); hyp=norm(p["ocr_text"])
        a,b=ref.split(),hyp.split(); cdist=dist(ref,hyp); wdist=dist(a,b)
        cd+=cdist;ct+=len(ref);wd+=wdist;wt+=len(a)
        expected_evidence=[e for f in case["fields"].values() for e in f.get("evidence",[])]
        match=sum(norm(e) in hyp for e in expected_evidence); ev+=len(expected_evidence); evok+=match
        ocr.append({"case_id":case["case_id"],"split":case["split"],"cer":ratio(cdist,len(ref)),
                    "wer":ratio(wdist,len(a)),"evidence_hit":match,"evidence_total":len(expected_evidence)})
    report={"schema_version":"2.0","cases_total":len(cases),"prediction_cases":len(by),
            "ocr":{"cases_evaluated":len(ocr),"coverage":ratio(len(ocr),len(cases)),
                   "character_error_rate_micro":ratio(cd,ct),"word_error_rate_micro":ratio(wd,wt),
                   "evidence_exact_recall":ratio(evok,ev),"evidence_found":evok,"evidence_total":ev,
                   "details":ocr},
            "image_input_interpretation":aggregate(cases,by,"image_output"),
            "reference_text_interpretation":aggregate(cases,by,"reference_output"),
            "paired_comparison":compare_paired(cases,by),
            "splits":{},"limitations":["Takstfasiten er et lite, åpent annotert sett; ekstra vurderingskandidater er ikke automatisk feil.",
                "Fasit fastslår aldri faktisk refusjonsrett. Et bekreftet forslag behandles som udokumentert sikkerhet i disse casene.",
                "Evidenssjekk viser om sitert tekst finnes i input; den viser ikke at sitatet støtter påstanden semantisk.",
                "Konfidensmål er bare beskrivende ved så få og selekterte prediksjoner; de kan ikke tolkes som klinisk kalibrering.",
                "Tegn- og ordfeil påvirkes av leserekkefølge og grensesnitttekst; evidenstreff er et eksakt delstrengssøk.",
                "Sammenlikning mellom bildeflyt og fasittekst isolerer en nyttig differanse, men beviser ikke årsak for hver feil."]}
    for split in sorted({c["split"] for c in cases}):
        group=[c for c in cases if c["split"]==split]
        report["splits"][split]={"image_input_interpretation":aggregate(group,by,"image_output"),
                                  "reference_text_interpretation":aggregate(group,by,"reference_output")}
    return report

def markdown(r):
    out=["# Evalueringsrapport", "", f"Case i datasettet: {r['cases_total']}. Case med prediksjoner: {r['prediction_cases']}.", "",
         "## OCR", "", f"Dekning: {r['ocr']['cases_evaluated']}/{r['cases_total']}",
         f"Tegnfeilrate (mikro): {r['ocr']['character_error_rate_micro']}",
         f"Ordfeilrate (mikro): {r['ocr']['word_error_rate_micro']}",
         f"Eksakt gjenfunn av evidens: {r['ocr']['evidence_found']}/{r['ocr']['evidence_total']}"]
    for k,title in [("image_input_interpretation","Tolkning fra OCR"),("reference_text_interpretation","Tolkning fra fasittekst")]:
        x=r[k]; c=x["counts"]
        out += ["",f"## {title}","",f"Dekning: {x['cases_evaluated']}/{x['cases_total']}",
                f"Feltpresisjon: {x['field_precision']}; feltgjenfinningsgrad: {x['field_recall']}",
                f"Feilaktige verdier: {c.get('wrong_values',0)}; oppdiktede feltpåstander: {c.get('unsupported_field_assertions',0)}; utelatte kjente felt: {c.get('omitted_known_fields',0)}",
                f"Kildens usikkerhet gjort sikker: {c.get('false_certainty_fields',0)}; bekreftede takster med uavklart refusjonsgrunnlag: {c.get('unverified_confirmed_tariffs',0)}",
                f"Bekreftede takstforslag som bryter med et spesifikt annotert vilkår: {c.get('confirmed_rule_conflicts',0)}",
                f"Påkrevde kontrollkandidater funnet: {c.get('identified_tariff_candidates',0)}/{c.get('required_tariff_candidates',0)}",
                f"Takstantall riktige: {c.get('correct_tariff_quantities',0)}/{c.get('required_tariff_quantities',0)}; feil: {c.get('wrong_tariff_quantities',0)}; mangler: {c.get('missing_tariff_quantities',0)}",
                f"Diagnosekandidater funnet: {c.get('identified_diagnosis_candidates',0)}/{c.get('required_diagnosis_candidates',0)}; ubekreftet faglig vurdering fremstilt som sikker: {c.get('clinician_unreviewed_diagnosis_confirmations',0)}",
                f"Feltpåstander med sitert tekst i input: {c.get('evidence_found_in_input',0)}/{c.get('asserted_fields',0)}; ikke-gjenfunnet sitat: {c.get('invalid_evidence',0)}",
                f"Konfidensmålinger: n={x['confidence_calibration']['n']}, Brier={x['confidence_calibration']['brier']}",
                f"Forventede usikkerhetsmarkører funnet: {c.get('identified_uncertainty_flags',0)}/{c.get('required_uncertainty_flags',0)}"]
    pair=r["paired_comparison"]["counts"]
    out += ["","## Parvis sammenlikning", "",f"Parede case: {pair.get('paired_cases',0)}; kjente felt sammenliknet: {pair.get('known_fields_compared',0)}.",
            f"Bare korrekt fra fasittekst: {pair.get('only_reference_correct',0)}; feil i begge løp: {pair.get('both_incorrect',0)}; bare korrekt fra OCR-tekst: {pair.get('only_image_correct',0)}.",
            "Forskjeller er observasjoner, ikke alene bevis for at OCR forårsaket feilen."]
    out += ["", "## Begrensninger", ""]+["- "+x for x in r["limitations"]]
    return "\n".join(out)+"\n"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",type=Path,default=ROOT/"data/cases.jsonl")
    parser.add_argument("--predictions",type=Path,required=True)
    parser.add_argument("--out-dir",type=Path,default=ROOT/"reports")
    parser.add_argument("--strict-coverage",action="store_true")
    parser.add_argument("--min-field-recall",type=float,help="Valgfri terskel 0–1 for bildeflyt; ikke en klinisk standard")
    parser.add_argument("--max-unsupported-fields",type=int,help="Valgfri grense for udokumenterte sikre feltpåstander")
    parser.add_argument("--max-false-certainty",type=int,help="Valgfri grense for usikre felt gjort sikre")
    parser.add_argument("--max-unverified-tariffs",type=int,help="Valgfri grense for ubekreftet refusjon gjort sikker")
    args=parser.parse_args()
    if args.min_field_recall is not None and not 0<=args.min_field_recall<=1: parser.error("--min-field-recall må være mellom 0 og 1")
    if any(x is not None and x<0 for x in (args.max_unsupported_fields,args.max_false_certainty,args.max_unverified_tariffs)): parser.error("Maksimalverdier må være ikke-negative")
    meta_path=args.predictions.parent/(args.predictions.stem+"_meta.json")
    provenance={"metadata_present":meta_path.is_file(),"cases_sha256_verified":False,"manifest_sha256_verified":False}
    if meta_path.is_file():
        try: meta=json.loads(meta_path.read_text(encoding="utf-8"))
        except (ValueError,OSError) as exc: parser.error(f"Ugyldig prediksjonsmetadata: {exc}")
        for key,file in (("cases_sha256",args.dataset),("manifest_sha256",args.dataset.parent/"manifest.json")):
            expected=meta.get(key)
            if expected:
                if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
                    parser.error(f"Prediksjonenes {key} stemmer ikke med datasettet. Kjør adapteren på nytt.")
                provenance[key+"_verified"]=True
    try: result=evaluate(load_jsonl(args.dataset),load_jsonl(args.predictions))
    except (ValueError,KeyError,TypeError) as exc: parser.error(str(exc))
    result["provenance"]=provenance
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/"evaluation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.out_dir/"evaluation.md").write_text(markdown(result),encoding="utf-8")
    print(markdown(result))
    gate_used=any(x is not None for x in (args.min_field_recall,args.max_unsupported_fields,args.max_false_certainty,args.max_unverified_tariffs))
    if (args.strict_coverage or gate_used) and any(result[k]["cases_evaluated"] != result["cases_total"] for k in ("ocr","image_input_interpretation","reference_text_interpretation")):
        raise SystemExit("Ufullstendig dekning: minst ett løp mangler output for ett eller flere case.")
    scored=result["image_input_interpretation"]; counts=scored["counts"]; failures=[]
    if args.min_field_recall is not None and (scored["field_recall"] is None or scored["field_recall"]<args.min_field_recall): failures.append("feltgjenfinning under grensen")
    for limit,key in [(args.max_unsupported_fields,"unsupported_field_assertions"),(args.max_false_certainty,"false_certainty_fields"),(args.max_unverified_tariffs,"unverified_confirmed_tariffs")]:
        if limit is not None and counts.get(key,0)>limit: failures.append(key+" over grensen")
    if failures: raise SystemExit("Testkrav feilet: "+", ".join(failures))
if __name__=="__main__": main()
