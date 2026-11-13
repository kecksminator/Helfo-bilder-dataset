# Evalueringsrapport

Case i datasettet: 36. Case med prediksjoner: 36.

## OCR

Dekning: 36/36
Tegnfeilrate (mikro): 0.1155
Ordfeilrate (mikro): 0.2146
Eksakt gjenfunn av evidens: 163/230

## Tolkning fra OCR

Dekning: 36/36
Feltpresisjon: 0.6615; feltgjenfinningsgrad: 0.5837
Feilaktige verdier: 66; oppdiktede feltpåstander: 0; utelatte kjente felt: 26
Kildens usikkerhet gjort sikker: 0; bekreftede takster med uavklart refusjonsgrunnlag: 0
Bekreftede takstforslag som bryter med et spesifikt annotert vilkår: 0
Påkrevde kontrollkandidater funnet: 0/13
Takstantall riktige: 0/7; feil: 0; mangler: 7
Diagnosekandidater funnet: 1/1; ubekreftet faglig vurdering fremstilt som sikker: 0
Feltpåstander med sitert tekst i input: 195/195; ikke-gjenfunnet sitat: 0
Konfidensmålinger: n=0, Brier=None
Forventede usikkerhetsmarkører funnet: 31/36

## Tolkning fra fasittekst

Dekning: 36/36
Feltpresisjon: 1.0; feltgjenfinningsgrad: 1.0
Feilaktige verdier: 0; oppdiktede feltpåstander: 0; utelatte kjente felt: 0
Kildens usikkerhet gjort sikker: 0; bekreftede takster med uavklart refusjonsgrunnlag: 0
Bekreftede takstforslag som bryter med et spesifikt annotert vilkår: 0
Påkrevde kontrollkandidater funnet: 13/13
Takstantall riktige: 7/7; feil: 0; mangler: 0
Diagnosekandidater funnet: 1/1; ubekreftet faglig vurdering fremstilt som sikker: 0
Feltpåstander med sitert tekst i input: 221/221; ikke-gjenfunnet sitat: 0
Konfidensmålinger: n=0, Brier=None
Forventede usikkerhetsmarkører funnet: 36/36

## Parvis sammenlikning

Parede case: 36; kjente felt sammenliknet: 221.
Bare korrekt fra fasittekst: 92; feil i begge løp: 0; bare korrekt fra OCR-tekst: 0.
Forskjeller er observasjoner, ikke alene bevis for at OCR forårsaket feilen.

## Begrensninger

- Takstfasiten er et lite, åpent annotert sett; ekstra vurderingskandidater er ikke automatisk feil.
- Fasit fastslår aldri faktisk refusjonsrett. Et bekreftet forslag behandles som udokumentert sikkerhet i disse casene.
- Evidenssjekk viser om sitert tekst finnes i input; den viser ikke at sitatet støtter påstanden semantisk.
- Konfidensmål er bare beskrivende ved så få og selekterte prediksjoner; de kan ikke tolkes som klinisk kalibrering.
- Tegn- og ordfeil påvirkes av leserekkefølge og grensesnitttekst; evidenstreff er et eksakt delstrengssøk.
- Sammenlikning mellom bildeflyt og fasittekst isolerer en nyttig differanse, men beviser ikke årsak for hver feil.
