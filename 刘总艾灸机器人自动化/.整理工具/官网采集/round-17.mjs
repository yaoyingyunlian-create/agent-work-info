import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
await capture(page,'/zh/rental-hosting?region=SG','zh-rental-SG');
await page.click('loc=role:link[name="《AI按摩机器人租赁托管协议书》"]');
await saveCurrent(page,'/zh/rental-hosting?region=SG','zh-rental-agreement');
console.log(await page.snapshot({scope:'full_page'}));
