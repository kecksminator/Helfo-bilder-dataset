# Datasett og metode

## Innhold

36 forskjellige syntetiske case er fordelt på 13 utvikling, 11 validering og 12 test. Ingen case er delt mellom disse gruppene. Testsettet er lite og offentlig som del av pakken: det er nyttig for regresjonstesting, men gir ikke et uavhengig eller statistisk representativt estimat dersom utviklere eller modeller har sett fasiten.

Casene omfatter periodontitt, karies, forebygging, endodontisk akuttbehandling, røntgen, historikk, planlagt versus utført behandling, fravær av hevelse, tann-tiltak-relasjon, mulige diagnoser, motstridende dato og usikkert tannnummer. Skjermbildene har fire visuelle varianter: klart bilde, JPEG-forringelse lagret som PNG, nedskalert bilde og tabellvisning. De er enkle, ensartede syntetiske visninger og gjenskaper ikke alt ved reelle journalsystemer.

Fasiten i `data/cases.jsonl` angir per felt: `state`, eventuell `value` og synlig `evidence`. `known` betyr dokumentert; `not_documented` betyr at opplysningen ikke finnes i bildet; `uncertain` og `conflict` bevarer usikkerhet eller motstrid. `reference_transcript` inneholder også grensesnitttekst, slik at teksten som måles svarer til hele bildet. `policy` inneholder få, avgrensede kontrollforventninger, ikke et fullstendig HELFO-regelverk.

## Måledefinisjoner

- **Tegnfeilrate / ordfeilrate:** summerte Levenshtein-avstander delt på antall tegn / ord i fasittekst etter Unicode-, store/små bokstaver- og whitespace-normalisering. Forstyrres av rekkefølge på teksten og grafisk grensesnitt.
- **Eksakt gjenfunn av evidens:** antall annoterte evidensstrenger som finnes eksakt i normalisert OCR-tekst, delt på totalt antall evidensstrenger. Dette er ikke en fullstendig semantisk feltanalyse og samme tekst kan forekomme flere steder.
- **Felt:** Forventede dokumenterte felt er riktige bare når både status og verdi stemmer. Feil verdi gir én falsk positiv og én falsk negativ; manglende eller tilbakeholdt verdi gir en falsk negativ. En sikker påstand om et udokumentert eller usikkert felt er en falsk positiv. Presisjon og gjenfinningsgrad regnes mikroaggregert. Utelatelser og feil verdier telles separat; resultater per felt finnes i JSON-rapporten.
- **Usikkerhet:** Separat antall tilfeller der en usikker kildetekst presenteres som sikker, samt hvor mange annoterte varselmarkører som gjenfinnes. Ikke alle varsler eller mulige ekstra advarsler er merket.
- **Takster:** Andel påkrevde kandidater til kontroll som gjenfinnes, antall forslag med uavklart grunnlag som likevel er merket `confirmed`, og antall bekreftelser som bryter med spesifikke annoterte begrensninger. Andre kandidater er umerkede, ikke automatisk riktige eller gale. Derfor gis ikke en misvisende total takstpresisjon. Denne versjonen evaluerer unike takstkoder og annoterte antall/repetisjoner per case, men ikke tannkobling for hver takst eller beløp.
- **Diagnoseforslag:** Merkede diagnosekandidater til faglig vurdering måles separat fra koder som faktisk er gjengitt i journalen. Andre forslag er umerkede. En automatisk bekreftelse som klinisk beslutning telles separat.
- **Evidens:** Måler om tekstsitater finnes i inndata. Dette er ikke en semantisk bekreftelse på at sitatet støtter påstanden.
- **Kalibrering:** Når et system oppgir sikkerhet for sikre feltpåstander, beregnes Brier-score og ECE på disse feltene. Små og selekterte testsett er ikke tilstrekkelige for klinisk kalibrering.
- **Parvis sammenlikning:** For hvert dokumentert felt vises om bare referansetekstløpet treffer, bare OCR-tekstløpet treffer, begge treffer eller begge bommer. Modellvariasjon kan påvirke dette; en forskjell alene beviser ikke årsak.
- **Dekning:** Andel case med output for hvert løp. Tomt eller manglende output skal ikke rapporteres som fullverdig evaluering. `--strict-coverage` krever begge tolkningsløp og OCR-tekst for samtlige case.

`development`, `validation` og `test` rapporteres separat for tolkning. Ingen terskel for klinisk sikkerhet eller salgsmodenhet kan begrunnes med dette lille pilotutvalget. En påfølgende evaluering bør ha klinisk uavhengig annotasjon, flere UI-layout, vanskeligere bilder, større casevariasjon, dobbel annotasjon, kilderevisjon og en skjermet testgruppe.

## Korrigering fra v1

SYN-009 beskrev røntgen, men viste tidligere registrert kode 801. v2 bruker 802 for tannrøntgen; 801 gjelder prøvetaking. SYN-032 tester at en registrert 801 uten synlig prøvebeskrivelse utløser kontroll, uten at fasiten hevder at taksten er feil.

De fiktive behandlingsdatoene er lagt til august 2026, etter den 1. juli-oppdateringen av nettsiden som ble kontrollert. Dette forenkler versjonsforståelsen, men erstatter ikke kontroll av datorelevant regelverk.
