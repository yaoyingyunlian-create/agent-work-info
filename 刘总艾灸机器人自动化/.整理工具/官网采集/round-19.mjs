import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const lang of ['zh','en']){
 const route='/'+lang+'/rental-hosting?region=SG';await capture(page,route,lang+'-rental-SG');
 const labels=await page.evaluate(()=>[...document.querySelectorAll('a')].filter(a=>a.getAttribute('href')==='javascript:void(0)').map(a=>a.innerText));
 for(const [i,label] of labels.entries()){
 await page.evaluate(label=>[...document.querySelectorAll('a')].find(a=>a.innerText===label).click(),label);
 await saveCurrent(page,route,lang+'-rental-document-'+i);
 }
}
for(const lang of ['zh','en']){
const route='/'+lang+'/products/1';await capture(page,route);
const versions=lang==='zh'?['标准商用版','豪华商用版','运营中心版']:['Standard Commercial','Premium Commercial','Operation Center'];
const plans=lang==='zh'?['直接购买','24个月租赁','租赁托管','加盟店配置']:['Purchase','24-month Lease','Rental Hosting','Franchise Setup'];
const labels=await page.evaluate(()=>[...document.querySelectorAll('button')].map(b=>b.innerText.trim()));console.log(lang,labels);
for(const [v,version] of versions.entries())for(const [p,plan] of plans.entries()){
if(!labels.includes(version)||!labels.includes(plan)){console.log('VARIANT_LABEL_MISMATCH',lang,version,plan);continue;}
await page.evaluate(({version,plan})=>{for(const text of [version,plan]){[...document.querySelectorAll('button')].find(b=>b.innerText.trim()===text).click();}},{version,plan});
await saveCurrent(page,route,lang+'-product1-variant-'+v+'-'+p);
}}
console.log(await page.snapshot());
