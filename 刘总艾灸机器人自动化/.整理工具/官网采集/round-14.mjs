import {capture,saveCurrent} from './capture.mjs';
const task=await taskSpace(199);const page=task.page('p1');
for(const lang of ['zh','en']) for(let n=1;n<=6;n++){
 const route='/'+lang+'/products/'+n;await capture(page,route);
 const labels=await page.evaluate(()=>[...document.querySelectorAll('button')].map(b=>b.innerText.trim()));
 console.log('buttons',lang,n,labels);
 const targets=lang==='zh'?['规格参数','产品视频','客户评价']:labels.filter(x=>/^(Specs|Specifications|Video|Reviews|Customer Reviews|Product Video)$/.test(x));
 for(const [k,label] of targets.entries()){
 await page.evaluate(label=>{const b=[...document.querySelectorAll('button')].filter(e=>e.innerText.trim()===label);if(b.length!==1)throw Error('ambiguous tab');b[0].scrollIntoView({block:'center'});b[0].click();},label);
 await saveCurrent(page,route,lang+'-products-'+n+'-tab-'+k);
 }
}
console.log(await page.snapshot({scope:'full_page'}));
