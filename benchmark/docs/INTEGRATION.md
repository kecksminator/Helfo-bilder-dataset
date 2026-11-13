# Koble til Clinaxia

En faktisk OCR-/HELFO-kodebase eller et testgrensesnitt for dagens Clinaxia var ikke tilgjengelig ved leveranse. `src/run_adapter.py` tilbyr derfor en konkret adapterkontrakt uten å gjette API-ruter eller koble seg til produksjon.

1. Kopier `src/example_adapter.py` til for eksempel `src/clinaxia_adapter.py`.
2. Implementer `ocr_image(image_path)` som returnerer rå OCR-tekst for bildet, og `interpret_text(text)` som returnerer et objekt med `fields`, `suggestions` og `flags` i formatet under. Konfigurer bare et autorisert testmiljø og bruk de syntetiske bildene.
3. Kjør samme tolkning på både rå OCR og fasittekst. Testløperen gjør begge kallene automatisk. Den sender ikke feltfasit eller takstpolicy til adapteren; korrekt transkripsjon gis bare til det separate referansetekstløpet.
4. Registrer app-/modellrevisjon og evaluer resultatet:

```bash
python3 src/run_adapter.py --adapter clinaxia_adapter --revision APP_COMMIT_OR_MODEL_VERSION --out outputs/clinaxia.jsonl
python3 src/evaluate.py --predictions outputs/clinaxia.jsonl --out-dir reports/clinaxia --strict-coverage
```

Adapteren må ikke bruke fasit ved tolkning av bildet. Bruk samme modell, innstillinger og prompt i begge tekstløp. Hvis appen ikke eksponerer OCR-tekst og teksttolkning separat, må utviklerne først eksponere et testgrensesnitt; et rent bilde-til-JSON-endepunkt gir bare ende-til-ende-mål og kan ikke isolere leddene på samme måte.

## Prediksjonskontrakt

Én JSON-linje per case; `case_id` må samsvare med datasettet. Eksempel, ikke en fullstendig fasit:

```json
{"case_id":"SYN-003","ocr_text":"...", "image_output":{"fields":{"teeth":{"state":"known","value":["13","23"]},"duration_minutes":{"state":"known","value":25}},"suggestions":[{"code":"101","status":"review"}],"flags":["eligibility_unverified"]}, "reference_output":{"fields":{},"suggestions":[],"flags":[]}}
```

Felt- og flaggnavn følger `data/cases.jsonl`. Feltstatus er `known`, `not_documented`, `uncertain` eller `conflict`; listen over mulige verdier bevares ved `uncertain` og `conflict`. Et uteblitt felt behandles som `not_documented`. Sikkerhetsstatus for takst er `review`, `confirmed` eller `rejected`. `confirmed` innebærer en sikker påstand og telles som uavklart i dette datasettet. `evidence` på felt er valgfri liste med sitat fra den aktuelle teksten. `confidence` på sikre felt er valgfri og må være 0–1; Brier og ECE rapporteres når verdier er tilgjengelige. `quantity` er valgfritt positivt heltall på takstforslag og måles der antall er annotert. `diagnosis_suggestions` er en egen liste med diagnosekode og samme statusverdier.

Validatoren avviser ukjente case-ID-er, duplikater, ukjente feltnavn og ugyldige statuser. Manglende case rapporteres som redusert dekning. Se `outputs/baseline.jsonl` for et komplett, kjørbart eksempel og `reports/evaluation.json` for detaljert resultat per case, felt og split.

Adapteren skriver en metadatafil med SHA-256 for casefil og manifest samt oppgitt app-/modellrevisjon. Når en slik metadatafil ligger ved prediksjonene, avviser evaluatoren uoverensstemmende data. Manuelt produsert JSONL uten metadata kan fortsatt evalueres; da opplyser rapporten at identiteten ikke ble verifisert.

## Valgfrie automatiske grenser

Ved kontinuerlig testing kan en utvikler sette egne terskler. De er ikke kliniske godkjenningskriterier. Hvis noen terskel brukes, krever evalueringsverktøyet full dekning for både bilde- og referanseløp.

```bash
python3 src/evaluate.py --predictions outputs/clinaxia.jsonl --strict-coverage --min-field-recall 0.90 --max-false-certainty 0 --max-unverified-tariffs 0
```

Terskelen 0,90 er bare et teknisk eksempel. Den må fastsettes og valideres for reell bruk, og må ikke tolkes som tilstrekkelig klinisk nøyaktighet.
