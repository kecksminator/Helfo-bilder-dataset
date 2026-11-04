// Frivillig read-only kjøring mot en LOKALT utpakket kopi av Clinaxia integration core v0.3.
// Bruker bare syntetiske data og preflight; ingen nettverkskall eller innsendinger.
// node src/probe_integration_v03.mjs /absolutt/sti/til/clinaxia-integration-core
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.argv[2];
if (!root) throw new Error('Oppgi sti til utpakket clinaxia-integration-core');
const modulePath = pathToFileURL(path.resolve(root,'src/integrations/adapters.js')).href;
const { KuhrAdapter } = await import(modulePath);
const adapter = new KuhrAdapter({name:'kuhr', enabled:true, mode:'mock'});
const base = {patientId:'SYN-004',providerId:'TEST-PROVIDER'};
const tests = [
  {name:'missing_patient', input:{providerId:'TEST-PROVIDER',items:[{code:'101',amount:0}]}},
  {name:'under_20_minutes', input:{...base,supportPoint:'10',durationMinutes:15,items:[{code:'101',amount:0}]}},
  {name:'101_207_together', input:{...base,supportPoint:'10',durationMinutes:25,items:[{code:'101',amount:0},{code:'207',amount:0}]}},
];
for (const t of tests) console.log(JSON.stringify({name:t.name,result:adapter.preflight(t.input)}));
