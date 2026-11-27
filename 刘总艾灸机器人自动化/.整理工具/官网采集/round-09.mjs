import {capture} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const path of ['/en/agents','/en/franchise','/en/rental-hosting','/zh/login','/zh/register','/zh/apply/agent','/zh/apply/rental','/zh/apply/franchise']){try{await capture(page,path)}catch(e){console.log('FAILED',path,e.message.slice(0,200))}}
console.log(await page.snapshot({scope:'full_page'}));
