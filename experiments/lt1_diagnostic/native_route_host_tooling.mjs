/** Explicit ordinary-tooling fixture: no entry grant, packet or native import. */
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {probe} from './native_route_host.mjs';
const need=(ok,why)=>{if(!ok)throw Error('C19 tooling refused: '+why);};
const key='OPENT1D_C19_TOOLING';
need(process.argv.length===2&&process.argv[1]===fileURLToPath(import.meta.url),'fixed tooling ABI');
const value=JSON.parse(process.env[key]??'null');delete process.env[key];
need(value&&Object.keys(value).sort().join(',')==='case_id,kind,nonce_sha256,roots,slot'&&value.kind==='invented'&&value.case_id==='C19'&&['base','allow-twin'].includes(value.slot)&&/^[a-f0-9]{64}$/.test(value.nonce_sha256),'fixed tooling context');
need(Object.keys(value.roots).sort().join(',')==='evidence,output'&&Object.values(value.roots).every(p=>typeof p==='string'&&p.startsWith('/')&&!p.includes('/../')&&fs.realpathSync(p)===p),'tooling roots');
const result=await probe(value);
process.stdout.write(JSON.stringify(result)+'\n');
