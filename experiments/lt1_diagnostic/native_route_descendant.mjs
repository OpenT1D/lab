/** Fixed C18 descendant only; no command or script selector. */
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const [folder,depth]=process.argv.slice(2);
if(!folder||resolve(folder)!==folder||!['0','1',undefined].includes(depth))throw Error('Fixed C18 descendant');
if(depth!=='1'){
 const child=spawn(process.execPath,[fileURLToPath(import.meta.url),folder,'1'],{stdio:'ignore',env:{LANG:'C',LC_ALL:'C',PATH:'/usr/bin:/bin'}});
 fs.writeFileSync(join(folder,'grandchild.json'),JSON.stringify({pid:child.pid,ppid:process.pid}),{flag:'wx',mode:0o600});
}
const parent=process.ppid;
setInterval(()=>{if(process.ppid!==parent||fs.existsSync(join(folder,'descendant-stop')))process.exit(0);},20);
