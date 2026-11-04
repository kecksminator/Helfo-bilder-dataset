# Kilder og avgrensninger

## Repository- og prosjektundersøkelse

4. november 2026 ble `kecksminator/Helfo-bilder-dataset` kontrollert via tilgjengelig GitHub-tilgang. Hovedgrenen `main` hadde én tilgjengelig commit, `5463aac4304cd363f74515e912ff8cbc23f9c6b1` («Initial commit», 19. juli 2026), og kun `README.md`. Én gren, ingen pull requests og ingen releases ble returnert. Issue #1 hadde ingen beskrivelse og null kommentarer. Dette avgrenser funnet til tilgjengelig historikk og betyr ikke at annet testmateriale ikke finnes andre steder.

Forsøk på å lese `kecksminator/clinaxia` og `kecksminator/probrMD` ga 404 gjennom tilgjengelig GitHub-tilgang; det kan bety manglende tilgang eller feil/endret navn, og beviser ikke at kodebasene ikke finnes. Søk i tilgjengelig prosjektmateriale fant den eldre `clinaxia-integration-core-v0.3.zip`, som inneholder generiske integrasjonstester og en mockbasert KUHR-forhåndskontroll. Se testobservasjoner i `reports/integration_core_v03.md`. Det ble ikke funnet en egnet OCR-/HELFO-motor i denne pakken. Begrenset søk fant ikke et dokumentert, annotert OPUS-OCR-testsett; det utelukker ikke at slikt materiale finnes andre steder.

## HELFO

Følgende offentlige kilder ble kontrollert 4. november 2026. Reglene kan endres, og behandlingsdato avgjør hvilket regelverk som skal vurderes:

- [Helsedirektoratet: takster for tannbehandling](https://www.helsedirektoratet.no/rundskriv/kapittel-5-stonad-ved-helsetjenester/takster-for-tannbehandling-) – oppgir takster fra 1. januar 2026, inkludert at 101 har vilkår om blant annet tidsbruk og ikke kan kombineres med 207.
- [Helsedirektoratet: rundskriv og stønadspunkter](https://www.helsedirektoratet.no/rundskriv/folketrygdloven-kap-5/rundskriv-til-folketrygdloven--5-6--5-6-a-og--5-25--undersokelse-og-behandling-hos-tannlege-og-tannpleier-for-sykdom-og-skade) – angir rammene for stønad og nødvendige vurderinger.
- [Helfo: dokumentasjon av tannlegens refusjonskrav](https://www.helfo.no/tannlege/Oppgjer-for-tannlege/slik-dokumenterer-tannlege-refusjonskrav) – beskriver dokumentasjon og at enkelte takster og stønadspunkter har konkrete krav.
- [Helsedirektoratet: gjeldende takster og kodeverk](https://www.helsedirektoratet.no/tilskudd-og-finansiering/finansiering/takster) – tilgang til blant annet maskinlesbare takstfiler.

Koblingen mellom kildene og de få annoterte testforventningene ligger i `data/helfo_rules_reference.json`. Disse kildene inngår ikke som komplette regeldata. Registrerte koder i case er tekst som skal gjenkjennes, ikke et bevis på at en takst er riktig eller kan kreves. ICD-lignende koder er også dokumenttekst, ikke en bekreftelse av medisinsk diagnose.

Før bruk til reelle forslag må en versjonert regelkilde, behandlingstidspunkt, relevante merknader og dokumentasjon vurderes av kvalifisert fagperson. Denne testpakken dokumenterer ikke samsvar med KUHR, lovverket eller klinisk sikkerhet.

- [NHS ICD-10 klassifikasjonsoversikt K00–K14](https://classbrowser.nhs.uk/ICD-10-5TH-Edition/vol1/block-k00-k14.htm) – brukt som supplerende kontroll for K02.1. Kontroller den norske ICD-10-versjonen for det aktuelle året før klinisk koding.

Den norske oversikten med versjonerte filer er [Helsedirektoratets ICD-side](https://www.helsedirektoratet.no/digitalisering-og-e-helse/helsefaglige-kodeverk/icd).
