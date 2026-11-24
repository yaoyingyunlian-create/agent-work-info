const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,'');
const products=JSON.parse(read('知识库/官网/产品目录.json'));
const pages=JSON.parse(read('官网资料/2026-11-24/页面清单.json'));
const enquiry=products.filter(p=>p.price_status.startsWith('询价'));
const missing=products.filter(p=>p.price_status.startsWith('未提供价格'));
const priced=products.filter(p=>p.frontend_price_raw);
assert.equal(priced.length,21);assert.equal(enquiry.length,14);assert.equal(missing.length,5);
for(const p of enquiry){assert.equal(p.price_display,'询价 / Enquire about this product');assert.equal(p.current_api_amount_if_frontend_priced,null);assert.ok(pages.find(r=>r.url===p.url).text_en.includes('Enquire about this product'));}
for(const p of missing){assert.ok(p.price_display.startsWith('未提供价格'));assert.equal(p.current_api_amount_if_frontend_priced,null);assert.ok(!pages.find(r=>r.url===p.url).text_en.includes('Enquire about this product'));}
for(const p of [...enquiry,...missing]){
 assert.ok(read('知识库/官网/'+p.knowledge_path).includes('- 页面价格：'+p.price_display));
 assert.ok(read('知识库/官网/产品索引.md').split('\n').find(s=>s.startsWith('| '+p.id+' |')).includes(p.price_display));
}
const html=read('官网资料/2026-11-24/官网资料预览.html');
const decode=s=>s.replace(/&quot;/g,'"').replace(/&#x27;/g,"'").replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const cards=[...html.matchAll(/<article data-kind="([^"]*)" data-search="([^"]*)" data-flag="([^"]*)">/g)].map(m=>({dataset:{kind:decode(m[1]),search:decode(m[2]),flag:decode(m[3])},hidden:false}));
const nodes=Object.fromEntries(['q','kind','flag','count','empty'].map(id=>[id,{value:id==='kind'?'商品':'',addEventListener(){}}]));
const context={document:{querySelectorAll:()=>cards,getElementById:id=>nodes[id]}};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const shown=()=>cards.filter(c=>!c.hidden).length;
assert.equal(shown(),40);
nodes.q.value='enquire about this product';context.filter();assert.equal(shown(),14);
nodes.q.value='未提供价格';context.filter();assert.equal(shown(),5);
nodes.q.value='';nodes.flag.value='原模板候选';context.filter();assert.equal(shown(),15);
nodes.q.value='没有此素材-404';context.filter();assert.equal(shown(),0);
const report={verified_at:'2026-11-24',priced:21,explicit_enquiry:14,price_unprovided:5,product_markdown_and_index:'19/19核对通过',html_script_checks:'40商品、14询价、5缺价、15模板、无结果筛选通过',real_browser:'本轮未验证；此为实际HTML脚本的Node VM执行，不是浏览器或视觉布局测试'};
fs.writeFileSync(path.join(__dirname,'询价修复验证.json'),JSON.stringify(report,null,2)+'\n','utf8');
console.log(JSON.stringify(report));
