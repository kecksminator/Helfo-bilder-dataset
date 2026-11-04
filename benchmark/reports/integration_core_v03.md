# Lokal test av en eldre Clinaxia-integrasjonspakke

Dette gjelder den tilgjengelige tidligere leveransen `clinaxia-integration-core-v0.3.zip` fra september 2026, ikke nåværende Clinaxia-app. Arkivets SHA-256 ved undersøkelsen var `f80c77606c791874ee45c4c7cb90009c9fc8c5842f04b5c43b4f42a52940c398`.

Pakken inneholder en mockbasert KUHR-adapter og generiske tester, men ingen OCR-motor eller komplett HELFO-regelmotor som kan evalueres med bildene. Seks eksisterende tester i `tests/core.test.js` ble kjørt lokalt 4. november 2026: seks bestått. Testene gjelder blant annet aktiveringsflagg, obligatoriske claim-felt, simulert kvittering og redaksjon av tekst; de verifiserer ikke takstgyldighet.

Med `src/probe_integration_v03.mjs` ble følgende syntetiske input gitt direkte til den lokale `preflight`-funksjonen uten nettverk eller innsending. Råresultatene finnes i `integration_probe.jsonl`.

| Syntetisk kontroll | Resultat fra v0.3 | Tolkning |
| --- | --- | --- |
| Manglende pasient-ID | `valid: false` | Det obligatoriske feltet kontrolleres. |
| Takst 101 med oppgitt 15 minutter | `valid: true` | Funksjonen vurderer ikke varighet. Resultatet bekrefter derfor ikke takstvilkår. |
| Takst 101 og 207 i samme eksempel | `valid: true` | Funksjonen vurderer ikke kombinasjonsbegrensningen. Resultatet bekrefter derfor ikke takstvilkår. |

Funnene viser hva denne gamle, bevisst enkle mockens sjekk gjør, ikke hva dagens Clinaxia eller KUHR gjør. Ingen reell pasientinformasjon, autentisering, kravinnsending eller offentlige tjenester ble brukt.

Reproduser med Node.js og en separat, utpakket kopi av arkivet:

```bash
node --test /sti/til/clinaxia-integration-core/tests/core.test.js
node src/probe_integration_v03.mjs /sti/til/clinaxia-integration-core
```
