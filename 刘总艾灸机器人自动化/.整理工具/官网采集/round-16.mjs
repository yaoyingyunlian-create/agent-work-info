import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const lang of ['zh','en']) for(let n=1;n<=6;n++){
const route='/'+lang+'/products/'+n;await capture(page,route);
await page.evaluate(label=>[...document.querySelectorAll('button')].find(e=>e.innerText.trim()===label).click(),lang==='zh'?'客户评价':'Reviews');
await saveCurrent(page,route,lang+'-products-'+n+'-tab-2');
}
for(const lang of ['zh','en']) for(const region of ['CN','SG','MY','HK','TH','ID','PH']){
const route='/'+lang+'/rental-hosting?region='+region;await capture(page,route,lang+'-rental-'+region);
const cycles=await page.evaluate(()=>[...document.querySelectorAll('button')].map(b=>b.innerText.trim()).filter(t=>/^\d+\s*(天|days)/i.test(t)));
for(const [i,label] of cycles.entries()){
await page.evaluate(label=>[...document.querySelectorAll('button')].find(e=>e.innerText.trim()===label).click(),label);
await saveCurrent(page,route,lang+'-rental-'+region+'-cycle-'+i);
}}
console.log(await page.snapshot());
