import {capture} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(let n=1;n<=6;n++){try{await capture(page,'/en/products/'+n)}catch(e){console.log('FAILED',n,e.message.slice(0,200))}}
console.log(await page.snapshot({scope:'full_page'}));
