import {capture} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const path of ['/zh/about','/zh/products','/zh/rental-hosting','/en','/en/about','/en/products']){try{await capture(page,path)}catch(e){console.log('FAILED',path,e.message.slice(0,200))}}
console.log(await page.snapshot({scope:'full_page'}));
