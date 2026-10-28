/** Read the native singleton parameters before any robustness trajectory. */
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {SOURCE, REVISION, verifySource} from '../m0/lt1/setup.mjs';
import {hash} from '../m0/lt1/record.mjs';
if(process.version!=='v22.22.2') throw Error('Use locked Node 22.22.2');
verifySource();
const model=resolve(SOURCE,'src/core/models/Cambridge.ts');
const {default:Cambridge}=await import(pathToFileURL(model).href);
const patient=new Cambridge({Gpeq:124.91784824923789});
console.log(JSON.stringify({upstream:REVISION,node:process.version,source_sha256:hash(model),
  parameters:{reference:structuredClone(patient.getParameterValues())}}));
