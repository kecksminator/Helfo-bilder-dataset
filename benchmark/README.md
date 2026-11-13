# Clinaxia – syntetisk OCR- og HELFO-benchmark v2

Dette er en første, selvstendig testpakke for journalimport og beslutningsstøtte. Alle 36 journalbilder og opplysninger er generert fra oppdiktede case. Grensesnittet er originalt og bruker ikke skjermbilder eller kode fra et journalsystem. Det er ikke en klinisk journal, en takstmotor eller et refusjonsgrunnlag.

Pakken inneholder skjermbilder i `data/images/`, maskinlesbar transkripsjon og feltfasit i `data/cases.jsonl`, integritetshasher, kildehenvisning til et lite sett takstvilkår, datagenerator, evaluator, adaptermal, en lokal demonstrasjon og automatiske tester.

## Rask start

Kommandoene kjøres fra mappen `benchmark/`. Python 3.12 er brukt ved leveranse. Evalueringsverktøyet og testene bruker bare standardbiblioteket.

```bash
python3 src/validate_dataset.py
python3 -m unittest discover -s tests -v
python3 src/evaluate.py --predictions outputs/baseline.jsonl --strict-coverage
```

Rapporten lagres som `reports/evaluation.md` og `reports/evaluation.json`. Den medfølgende demonstrasjonen er **Tesseract 5.3.4 med engelsk språkmodell** og en liten, maltilpasset parser; den er ikke Clinaxia. Resultatet sier ingenting om produksjonsytelsen i Clinaxia.

For en ny demonstrasjonskjøring kreves Tesseract lokalt. Bruk norsk språkpakke hvis den er installert; oppgi ellers et tilgjengelig språk eksplisitt. Dette kan gi andre resultater enn den medfølgende rapporten.

```bash
tesseract --list-langs
python3 src/run_baseline.py --lang nor
python3 src/evaluate.py --predictions outputs/baseline.jsonl --strict-coverage
```

For å generere bilder og fasit på nytt kreves Pillow og DejaVu Sans:

```bash
python3 -m pip install -r requirements.txt
python3 src/generate.py
python3 src/validate_dataset.py
```

Generatoren er deterministisk med samme kilde, Python-/Pillow-versjoner og fontfiler. Manifestet oppgir SHA-256 for data og fonter; avvikende systemfonter kan gi andre bildehasher. Ikke legg ekte pasientdata i pakken eller i et offentlig repository.

## Evalueringsløp

1. **OCR:** Originalt skjermbilde sammenliknes med referansetranskripsjon, blant annet med tegnfeilrate, ordfeilrate og eksakt gjenfunn av annotert feltevidens.
2. **Tolkning etter OCR:** Felter, påstander, manglende funn, usikkerhet og avgrensede takstforslag måles basert på OCR-teksten.
3. **Tolkning fra fasittekst:** Nøyaktig samme tolkningsfunksjon kjøres på korrekt transkripsjon. Dette gir grunnlag for å undersøke forskjellen mellom OCR-avhengige feil og feil som også oppstår uten OCR-feil. En forskjell er ikke alene bevis for årsak i hvert tilfelle.

Den merkede taksttesten inneholder kandidater til **faglig kontroll** for 101, 501, 801, 802 og 804, grenseverdier for tidsbruk og antall samt tilfeller med uavklart grunnlag. Antall er forslag til kontroll, ikke fasit for et reelt krav. Ekstra mulige kandidater er umerkede og teller ikke automatisk som feil. Ingen av casene fastslår at pasienten har rett til refusjon. Bekreftede takstforslag uten avklart grunnlag telles separat. Poengsummene er utviklingstester, ikke klinisk validering.

Se [datasett og metode](docs/DATASET.md), [integrasjon](docs/INTEGRATION.md) og [kilder og avgrensninger](docs/SOURCES_AND_LIMITS.md). Se også `reports/integration_core_v03.md` for hva som faktisk ble testet i en eldre integrasjonspakke.
