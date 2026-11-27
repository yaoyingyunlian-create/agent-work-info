import {capture} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const path of ['/en/login','/en/register','/en/apply/agent','/en/apply/rental','/en/apply/franchise','/zh/apply/agent','/zh/apply/rental','/zh/apply/franchise','/zh/account','/en/account','/zh/orders','/en/orders']){try{await capture(page,path)}catch(e){console.log('FAILED',path,e.message.slice(0,200))}}
console.log(await page.snapshot());
