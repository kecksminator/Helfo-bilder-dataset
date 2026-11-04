import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from evaluate import evaluate, load_jsonl
from run_baseline import parse
from validate_dataset import validate as validate_dataset

CASES=load_jsonl(ROOT/"data/cases.jsonl")
BY_ID={c["case_id"]:c for c in CASES}

def perfect(case):
    fields={k:{x:y for x,y in v.items() if x in ("state","value")}
            for k,v in case["fields"].items()}
    return {"fields":fields,"suggestions":[{"code":c,"status":"review"} for c in case["policy"]["required_review_codes"]],
            "flags":case["policy"]["required_uncertainty_flags"][:]}

class BenchmarkTests(unittest.TestCase):
    def test_dataset_integrity(self): self.assertEqual(validate_dataset(ROOT/"data"),[])

    def test_perfect_ocr_and_fields(self):
        c=BY_ID["SYN-003"]
        r=evaluate([c],[{"case_id":c["case_id"],"ocr_text":c["reference_transcript"],
                         "image_output":perfect(c),"reference_output":perfect(c)}])
        self.assertEqual(r["ocr"]["character_error_rate_micro"],0)
        self.assertEqual(r["image_input_interpretation"]["field_precision"],1)
        self.assertEqual(r["image_input_interpretation"]["field_recall"],1)
        self.assertEqual(r["image_input_interpretation"]["required_candidate_recall"],1)
        self.assertEqual(r["image_input_interpretation"]["counts"].get("unverified_confirmed_tariffs",0),0)

    def test_wrong_tooth_is_both_wrong_and_missed(self):
        c=BY_ID["SYN-002"]; p=perfect(c); p["fields"]["teeth"]["value"]=["46"]
        m=evaluate([c],[{"case_id":c["case_id"],"image_output":p}])["image_input_interpretation"]["counts"]
        self.assertEqual(m["wrong_values"],1); self.assertEqual(m["false_positive_fields"],1); self.assertEqual(m["false_negative_fields"],1)

    def test_hallucination_and_omission_are_distinct(self):
        c=BY_ID["SYN-002"]; p=perfect(c)
        p["fields"]["support_point"]={"state":"known","value":"6a"}; del p["fields"]["teeth"]
        m=evaluate([c],[{"case_id":c["case_id"],"image_output":p}])["image_input_interpretation"]["counts"]
        self.assertEqual(m["unsupported_field_assertions"],1); self.assertEqual(m["omitted_known_fields"],1)

    def test_uncertain_tooth_must_not_become_certain(self):
        c=BY_ID["SYN-007"]; p=perfect(c); p["fields"]["teeth"]={"state":"known","value":["11"]}
        m=evaluate([c],[{"case_id":c["case_id"],"image_output":p}])["image_input_interpretation"]["counts"]
        self.assertEqual(m["false_certainty_fields"],1)

    def test_contradictory_tariffs_and_unverified_confirmation(self):
        c=BY_ID["SYN-005"]; p=perfect(c); p["suggestions"]=[{"code":"101","status":"confirmed"}]
        m=evaluate([c],[{"case_id":c["case_id"],"image_output":p}])["image_input_interpretation"]["counts"]
        self.assertEqual(m["confirmed_documented_conflicting_tariffs"],1); self.assertEqual(m["unverified_confirmed_tariffs"],1)
        self.assertEqual(m["confirmed_rule_conflicts"],1)

    def test_reference_vs_image_are_scored_independently(self):
        c=BY_ID["SYN-002"]; image=perfect(c); image["fields"]["teeth"]["value"]=["46"]
        r=evaluate([c],[{"case_id":c["case_id"],"image_output":image,"reference_output":perfect(c)}])
        self.assertLess(r["image_input_interpretation"]["field_recall"],r["reference_text_interpretation"]["field_recall"])
        self.assertEqual(r["paired_comparison"]["counts"]["only_reference_correct"],1)

    def test_duplicate_and_invalid_prediction_are_rejected(self):
        c=BY_ID["SYN-002"]; p={"case_id":c["case_id"],"image_output":perfect(c)}
        with self.assertRaisesRegex(ValueError,"Duplisert prediksjon"): evaluate([c],[p,p])
        bad=copy.deepcopy(p); bad["image_output"]["fields"]["teeth"]["state"]="certain"
        with self.assertRaisesRegex(ValueError,"ugyldig feltstatus"): evaluate([c],[bad])

    def test_missing_coverage_is_visible(self):
        r=evaluate(CASES,[])
        self.assertEqual(r["prediction_cases"],0); self.assertEqual(r["image_input_interpretation"]["coverage"],0)
        self.assertIsNone(r["image_input_interpretation"]["field_precision"])

    def test_adapter_runs_both_text_paths_and_records_revision(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d); case=BY_ID["SYN-003"]
            (tmp/"data.jsonl").write_text(json.dumps(case,ensure_ascii=False)+"\n",encoding="utf-8")
            (tmp/"fake_adapter.py").write_text("def ocr_image(path): return 'OCR tekst'\ndef interpret_text(text): return {'fields': {}, 'suggestions': [], 'flags': []}\n",encoding="utf-8")
            env={**os.environ,"PYTHONPATH":str(tmp)}
            command=[sys.executable,str(ROOT/"src/run_adapter.py"),"--adapter","fake_adapter","--revision","test-rev",
                     "--dataset",str(tmp/"data.jsonl"),"--out",str(tmp/"output.jsonl")]
            subprocess.run(command,env=env,check=True,capture_output=True,text=True)
            output=load_jsonl(tmp/"output.jsonl")[0]
            self.assertEqual(output["ocr_text"],"OCR tekst")
            self.assertIn("image_output",output); self.assertIn("reference_output",output)
            self.assertEqual(json.loads((tmp/"output_meta.json").read_text())["revision"],"test-rev")

    def test_tariff_boundary_annotations(self):
        expected={19:{},20:{"101":1},21:{"101":1},22:{"101":2},23:{},24:{"501":1},25:{"501":1},26:{"501":2},27:{"501":1},28:{}}
        for n,quantities in expected.items():
            with self.subTest(case=n):
                self.assertEqual(BY_ID[f"SYN-{n:03d}"]["policy"]["required_review_quantities"],quantities)

    def test_wrong_tariff_quantity_is_flagged(self):
        c=BY_ID["SYN-026"]; p=perfect(c); p["suggestions"]=[{"code":"501","status":"review","quantity":1}]
        r=evaluate([c],[{"case_id":c["case_id"],"image_output":p}]); m=r["image_input_interpretation"]["counts"]
        self.assertEqual(m["wrong_tariff_quantities"],1)

    def test_evidence_must_occur_in_actual_input(self):
        c=BY_ID["SYN-002"]; p=perfect(c); p["fields"]["teeth"]["evidence"]=["tann 99 eksisterer"]
        r=evaluate([c],[{"case_id":c["case_id"],"ocr_text":c["reference_transcript"],"image_output":p}])
        self.assertEqual(r["image_input_interpretation"]["counts"]["invalid_evidence"],1)

    def test_confidence_calibration_uses_known_assertions(self):
        c=BY_ID["SYN-002"]; p=perfect(c); p["fields"]["teeth"]={"state":"known","value":["46"],"confidence":0.9}
        r=evaluate([c],[{"case_id":c["case_id"],"image_output":p}])
        cal=r["image_input_interpretation"]["confidence_calibration"]
        self.assertEqual(cal["n"],1); self.assertEqual(cal["brier"],0.81)

    def test_diagnosis_suggestion_scored_separately(self):
        c=BY_ID["SYN-033"]; p=perfect(c); p["diagnosis_suggestions"]=[{"code":"K02.1","status":"review"}]
        r=evaluate([c],[{"case_id":c["case_id"],"reference_output":p}])
        self.assertEqual(r["reference_text_interpretation"]["diagnosis_candidate_recall"],1)
        p["diagnosis_suggestions"][0]["status"]="confirmed"
        r=evaluate([c],[{"case_id":c["case_id"],"reference_output":p}])
        self.assertEqual(r["reference_text_interpretation"]["counts"]["clinician_unreviewed_diagnosis_confirmations"],1)

    def test_reject_boolean_as_numeric_duration(self):
        c=BY_ID["SYN-003"]; p=perfect(c); p["fields"]["duration_minutes"]["value"]=True
        with self.assertRaisesRegex(ValueError,"ikke-negativt heltall"): evaluate([c],[{"case_id":c["case_id"],"image_output":p}])

    def test_v1_xray_code_was_corrected(self):
        c=BY_ID["SYN-009"]
        self.assertEqual(c["fields"]["treatments"]["value"],["tannrøntgen"])
        self.assertEqual(c["fields"]["recorded_tariffs"]["value"],["802"])

    def test_reference_parser_501_boundary(self):
        c=BY_ID["SYN-026"]; out=parse(c["reference_transcript"])
        self.assertIn({"code":"501","status":"review","quantity":2},out["suggestions"])

    def test_gate_rejects_false_certainty(self):
        c=BY_ID["SYN-007"]; p=perfect(c); p["fields"]["teeth"]={"state":"known","value":["11"]}
        item={"case_id":c["case_id"],"ocr_text":c["reference_transcript"],"image_output":p,"reference_output":perfect(c)}
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d); ds=tmp/"case.jsonl"; pred=tmp/"pred.jsonl"
            ds.write_text(json.dumps(c,ensure_ascii=False)+"\n",encoding="utf8")
            pred.write_text(json.dumps(item,ensure_ascii=False)+"\n",encoding="utf8")
            result=subprocess.run([sys.executable,str(ROOT/"src/evaluate.py"),"--dataset",str(ds),"--predictions",str(pred),
                                   "--out-dir",str(tmp/"report"),"--max-false-certainty","0"],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertIn("false_certainty_fields",result.stderr)

    def test_gate_rejects_incomplete_coverage(self):
        c=BY_ID["SYN-002"]; item={"case_id":c["case_id"],"image_output":perfect(c)}
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d); ds=tmp/"case.jsonl"; pred=tmp/"pred.jsonl"
            ds.write_text(json.dumps(c,ensure_ascii=False)+"\n",encoding="utf8")
            pred.write_text(json.dumps(item,ensure_ascii=False)+"\n",encoding="utf8")
            result=subprocess.run([sys.executable,str(ROOT/"src/evaluate.py"),"--dataset",str(ds),"--predictions",str(pred),
                                   "--out-dir",str(tmp/"report"),"--max-false-certainty","0"],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertIn("Ufullstendig dekning",result.stderr)

    def test_stale_predictions_are_rejected_if_hashes_exist(self):
        c=BY_ID["SYN-002"]
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d); ds=tmp/"case.jsonl"; pred=tmp/"pred.jsonl"
            ds.write_text(json.dumps(c,ensure_ascii=False)+"\n",encoding="utf8")
            pred.write_text(json.dumps({"case_id":c["case_id"]})+"\n",encoding="utf8")
            (tmp/"pred_meta.json").write_text(json.dumps({"cases_sha256":"0"*64}),encoding="utf8")
            result=subprocess.run([sys.executable,str(ROOT/"src/evaluate.py"),"--dataset",str(ds),"--predictions",str(pred),
                                   "--out-dir",str(tmp/"report")],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertIn("stemmer ikke med datasettet",result.stderr)

if __name__=="__main__": unittest.main()
