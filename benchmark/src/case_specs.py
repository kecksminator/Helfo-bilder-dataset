"""Originale, syntetiske case. Ingen felt bygger på ekte pasienter.

Fasiten beskriver hva som står i skjermbildet og bevisst avgrensede
testforventninger; den er ikke en beslutning om rett til refusjon.
"""

def f(key, label, display, value, state="known", evidence=None):
    return {"key": key, "label": label, "display": display,
            "value": value, "state": state,
            "evidence": evidence if evidence is not None else [display]}

def case(n, title, split, appearance, rows, required_codes=None, flags=None,
         conflicting_pair=None, forbidden_confirmed=None, note="", quantities=None,
         diagnoses=None, group=None, sources=None):
    return {"case_id": f"SYN-{n:03d}", "title": title, "split": split,
            "appearance": appearance, "rows": rows,
            "policy": {"required_review_codes": required_codes or [],
                       "required_uncertainty_flags": flags or [],
                       "conflicting_pair": conflicting_pair or [],
                       "forbidden_confirmed_codes": forbidden_confirmed or [],
                       "required_review_quantities": quantities or {},
                       "required_diagnosis_candidates": diagnoses or [],
                       "source_ids": sources or (["HELFO-2026-T101"] if (required_codes or forbidden_confirmed or conflicting_pair) else []),
                       "eligibility": "unverified", "closed_world": False},
            "group":group or f"SYN-{n:03d}", "note": note}

def date(v): return f("visit_date", "Dato", v, v)
def tooth(v): return f("teeth", "Tenner", ", ".join(v), v)
def diag(code, text):
    return [f("diagnosis_codes", "Diagnosekode", code, [code]),
            f("diagnosis_text", "Diagnose", text, text)]
def treat(*v): return f("treatments", "Tiltak", "; ".join(v), list(v))
def status(v): return f("treatment_status", "Status", v, v)
def point(v): return f("support_point", "Stønadspunkt", v, v)
def duration(n): return f("duration_minutes", "Tidsbruk", f"{n} minutter", n)
def tariff(*v): return f("recorded_tariffs", "Registrert takst", ", ".join(v), list(v))
def prior501(n): return f("prior_501_year", "Tidligere 501 i år", str(n), n)
def prior101(n): return f("prior_101_today", "Tidligere 101 i dag", str(n), n)
def findings(text): return f("findings", "Funn", text, text)
def prev(n, split, minutes, ap="clear", group=None):
    return case(n,f"Forebygging {minutes} minutter",split,ap,[date("2026-08-04"),tooth(["13","23"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("10"),duration(minutes),prior101(0)],
                required_codes=["101"] if minutes>=20 else [],
                quantities={"101":(2 if minutes>40 else 1)} if minutes>=20 else {},
                flags=["eligibility_unverified"]+(["duration_below_101_minimum"] if minutes<20 else []),
                forbidden_confirmed=["101"] if minutes<20 else [],group=group,sources=["HELFO-2026-T101"])
def perio(n, split, minutes, prior, ap="clear", group=None):
    allowed=max(0,min(minutes//30,14-prior))
    flags=["eligibility_unverified"]
    if minutes<30: flags.append("duration_below_501_minimum")
    if prior>=14: flags.append("annual_501_cap_reached")
    return case(n,f"Periodontal behandling {minutes} minutter",split,ap,[date("2026-08-05"),tooth(["16","26"]),*diag("K05.3","Kronisk periodontitt"),treat("systematisk periodontal behandling","subgingival depurasjon","opplæring til egenomsorg"),status("utført"),point("6a"),duration(minutes),prior501(prior)],
                required_codes=["501"] if allowed else [],quantities={"501":allowed} if allowed else {},
                flags=flags, forbidden_confirmed=["501"] if not allowed else [],group=group,sources=["HELFO-2026-T501"])

CASES = [
 case(1,"Periodontal behandling", "development", "clear", [date("2026-08-02"),tooth(["16","26"]),*diag("K05.3","Kronisk periodontitt"),treat("periodontal depurasjon"),status("utført"),point("6a"),tariff("501")]),
 case(2,"Karies og restaurering", "development", "clear", [date("2026-08-04"),tooth(["36"]),*diag("K02.1","Dentinkaries"),treat("komposittfylling"),status("utført")],flags=["missing_support_point"]),
 case(3,"Forebygging med tidsangivelse", "development", "clear", [date("2026-08-09"),tooth(["13","23"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("10"),duration(25)],required_codes=["101"],flags=["eligibility_unverified"],note="101 er kandidat til kontroll; stønad er ikke fastslått."),
 case(4,"Forebygging under 20 minutter", "development", "jpeg", [date("2026-08-10"),tooth(["13"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("10"),duration(15)],flags=["duration_below_101_minimum","eligibility_unverified"],forbidden_confirmed=["101"]),
 case(5,"Mulig takstkombinasjon", "development", "clear", [date("2026-08-11"),tooth(["24"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("10"),duration(25),tariff("207")],flags=["tariff_101_207_conflict","eligibility_unverified"],conflicting_pair=["101","207"],forbidden_confirmed=["101"]),
 case(6,"Manglende stønadspunkt", "development", "small", [date("2026-08-12"),tooth(["25"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),duration(25)],flags=["missing_support_point","eligibility_unverified"]),
 case(7,"Usikkert tannnummer", "development", "clear", [date("2026-08-15"),f("teeth","Tenner","11 eller 21 - usikkert",["11","21"],"uncertain",["11","21","usikkert"]),treat("klinisk undersøkelse"),status("utført")],flags=["uncertain_tooth"]),
 case(8,"Negert symptom", "development", "jpeg", [date("2026-08-16"),tooth(["46"]),f("symptoms","Symptomer","hevelse: fraværende",["hevelse: fraværende"]),treat("klinisk undersøkelse"),status("utført")]),
 case(9,"Manglende diagnose og tid", "development", "small", [date("2026-08-17"),tooth(["35"]),treat("tannrøntgen"),status("utført"),tariff("802")],flags=["missing_diagnosis"],sources=["HELFO-2026-T801-802-804"],note="Korrigert fra v1: 802 er tannrøntgen; 801 gjelder prøvetaking."),
 case(10,"Mulig diagnose", "development", "clear", [date("2026-08-18"),tooth(["46"]),f("diagnosis_text","Diagnose","mulig karies","karies","uncertain",["mulig karies"]),treat("klinisk undersøkelse"),status("utført")],flags=["uncertain_diagnosis"]),
 case(11,"To tenner, ulike tiltak", "validation", "clear", [date("2026-08-19"),tooth(["14","15"]),treat("ekstraksjon","komposittfylling"),f("treatment_by_tooth","Tann og tiltak","14: ekstraksjon; 15: komposittfylling",["14: ekstraksjon","15: komposittfylling"]),status("utført")]),
 case(12,"Tall som lett forveksles", "validation", "jpeg", [date("2026-08-20"),tooth(["36","46"]),*diag("K02.1","Dentinkaries"),treat("komposittfylling"),status("planlagt")],flags=["treatment_not_performed"]),
 case(13,"Historisk takst", "validation", "small", [date("2026-08-22"),tooth(["21"]),treat("etterkontroll"),status("utført"),f("historical_tariffs","Tidligere takst","501",["501"]),tariff("4")],note="Historiske og registrerte takster skal holdes atskilt."),
 case(14,"Apikal infeksjon", "test", "clear", [date("2026-08-23"),tooth(["11"]),*diag("K04.7","Periapikal abscess uten fistel"),f("symptoms","Symptomer","hevelse: til stede",["hevelse: til stede"]),treat("endodontisk akuttbehandling"),status("utført")]),
 case(15,"Motstridende datoer", "test", "jpeg", [f("visit_date","Dato","2026-08-24 eller 2026-08-25 - motstrid",["2026-08-24","2026-08-25"],"conflict",["2026-08-24","2026-08-25","motstrid"]),tooth(["27"]),treat("klinisk undersøkelse"),status("utført")],flags=["conflicting_date"]),
 case(16,"Forebygging uten varighet", "test", "small", [date("2026-08-26"),tooth(["33","43"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("14")],flags=["missing_duration","eligibility_unverified"]),
 case(17,"Egenomsorg med foreslått kontroll", "test", "jpeg", [date("2026-08-29"),tooth(["12","22"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("14"),duration(30)],required_codes=["101"],flags=["eligibility_unverified"]),
 case(18,"Forebygging med oppgitt punkt", "validation", "small", [date("2026-08-30"),tooth(["31","41"]),treat("individuell egenomsorgsopplæring","forebyggende behandling"),status("utført"),point("1"),duration(30)],required_codes=["101"],flags=["eligibility_unverified"]),
 prev(19,"validation",19,"jpeg","101-minimum"),
 prev(20,"validation",20,"jpeg","101-minimum"),
 prev(21,"test",40,"small","101-repeat"),
 prev(22,"test",41,"small","101-repeat"),
 perio(23,"validation",29,0,"table","501-minimum"),
 perio(24,"validation",30,0,"table","501-minimum"),
 perio(25,"test",59,0,"jpeg","501-repeat"),
 perio(26,"test",60,0,"jpeg","501-repeat"),
 perio(27,"test",60,13,"small","501-cap"),
 perio(28,"test",60,14,"small","501-cap"),
 case(29,"Tannrøntgen PA", "development","table",[date("2026-08-06"),tooth(["36"]),treat("tannrøntgen"),status("utført"),point("10")],required_codes=["802"],flags=["eligibility_unverified"],sources=["HELFO-2026-T801-802-804"]),
 case(30,"Panoramarøntgen", "development","table",[date("2026-08-07"),tooth(["18","28","38","48"]),findings("diagnostisk behov for oversikt over begge kjever"),treat("panoramarøntgen"),status("utført"),point("10")],required_codes=["804"],flags=["eligibility_unverified"],sources=["HELFO-2026-T801-802-804"]),
 case(31,"Prøvetaking til laboratoriet", "validation","jpeg",[date("2026-08-10"),tooth(["46"]),treat("prøvetaking til laboratorieundersøkelse"),status("utført"),point("6a")],required_codes=["801"],flags=["eligibility_unverified"],sources=["HELFO-2026-T801-802-804"]),
 case(32,"Røntgen og 801 uten prøvebeskrivelse", "validation","jpeg",[date("2026-08-11"),tooth(["46"]),treat("tannrøntgen"),status("utført"),tariff("801")],flags=["check_801_sampling_documentation"],sources=["HELFO-2026-T801-802-804"],note="Påpek at prøvetaking ikke er synlig; ikke konkluder at taksten er feil."),
 case(33,"Registrert dentinkaries", "development","small",[date("2026-08-12"),tooth(["36"]),f("diagnosis_text","Diagnose","Dentinkaries","Dentinkaries"),treat("klinisk undersøkelse"),status("utført")],diagnoses=["K02.1"],sources=["ICD10-K02.1"],note="K02.1 er kandidat for behandlerkontroll; diagnosen er skrevet men kode mangler."),
 case(34,"Usikker karies uten dybde", "test","table",[date("2026-08-13"),tooth(["46"]),f("diagnosis_text","Diagnose","mulig karies","karies","uncertain",["mulig karies"]),treat("klinisk undersøkelse"),status("utført")],flags=["uncertain_diagnosis"],sources=["ICD10-K02.1"],note="Ingen lokalisasjons- eller dybdekode kan fastslås bare fra 'mulig karies'."),
 case(35,"Tidligere og nåværende tenner", "test","jpeg",[date("2026-08-14"),tooth(["21"]),f("historical_teeth","Tidligere tenner","11",["11"]),treat("etterkontroll"),status("utført")]),
 case(36,"Fravær av hevelse med mulig karies", "validation","small",[date("2026-08-15"),tooth(["36"]),f("symptoms","Symptomer","hevelse: fraværende",["hevelse: fraværende"]),f("diagnosis_text","Diagnose","mulig karies","karies","uncertain",["mulig karies"]),treat("klinisk undersøkelse"),status("utført")],flags=["uncertain_diagnosis"]),
]
