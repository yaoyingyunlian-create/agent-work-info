import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
const route='/en/products/1';await capture(page,route);
const versions=['Standard Commercial Version','Luxury Commercial Edition','Operation Center Edition'];
const plans=['outright purchase','24-month lease','Leasing and trusteeship','Franchise store configuration'];
for(const [v,version] of versions.entries())for(const [p,plan] of plans.entries()){
await page.evaluate(({version,plan})=>{for(const text of [version,plan]){const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()===text);if(!b)throw Error('missing version');b.click();}},{version,plan});
await saveCurrent(page,route,'en-product1-variant-'+v+'-'+p);
}
await capture(page,'/zh','home-zh');
console.log(await page.snapshot());
