import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const lang of ['zh','en']){
for(let n=1;n<=6;n++){
 const route='/'+lang+'/products/'+n;await capture(page,route);
 const buttons=lang==='zh'?['规格参数','产品视频','客户评价']:['Specifications','Product Video','Customer Reviews'];
 const states=await page.evaluate(()=>[...document.querySelectorAll('button')].map(b=>b.innerText.trim()));
 console.log('buttons',lang,n,states);
 for(let k=0;k<buttons.length;k++){
   const label=buttons[k];if(!states.includes(label)){console.log('MISSING_TAB',lang,n,label);continue;}
   await page.click('loc=role:button[name="'+label+'"]');
   await saveCurrent(page,route,lang+'-products-'+n+'-tab-'+k);
 }
}}
console.log(await page.snapshot());
