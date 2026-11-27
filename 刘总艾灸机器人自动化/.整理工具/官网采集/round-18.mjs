import {saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
console.log(await page.snapshot());
console.log(await page.evaluate(()=>[...document.querySelectorAll('a')].filter(a=>a.textContent.includes('协议书')).map(a=>({text:a.innerText,href:a.href,rect:a.getBoundingClientRect().toJSON()}))));
await page.evaluate(()=>[...document.querySelectorAll('a')].find(a=>a.innerText==='《AI按摩机器人租赁托管协议书》').click());
await saveCurrent(page,'/zh/rental-hosting?region=SG','zh-rental-agreement');
console.log(await page.snapshot({scope:'full_page'}));
