const task=await taskSpace(92),page=task.page('p1');
const fs=await import('node:fs/promises'),assert=(await import('node:assert/strict')).default;
const checks=[];
async function check(name,n){const value=await page.evaluate(()=>[...document.querySelectorAll('article')].filter(e=>!e.hidden).length);assert.equal(value,n);checks.push({name,count:value,passed:true});}
await check('默认商品',40);
await page.fill('#q','enquire about this product');await check('明确询价检索',14);
await page.fill('#q','未提供价格');await check('缺价检索',5);
await page.fill('#q','');await page.selectOption('#flag','原模板候选');await check('原分类候选',15);
await page.selectOption('#flag','');await page.fill('#q','aqua light toner');await check('英文品名检索',1);
await page.fill('#q','');
const productImages=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article:not([hidden]) img')].map(async i=>{i.loading='eager';try{await i.decode();return {ok:true};}catch{return {ok:false,src:i.getAttribute('src')};}})));
assert.ok(productImages.every(i=>i.ok));
await page.selectOption('#kind','原始素材');await check('媒体记录',180);
await page.selectOption('#flag','视频');await check('视频',3);
const videos=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article:not([hidden]) video')].map(v=>new Promise(resolve=>{const timer=setTimeout(()=>resolve({ok:false,src:v.getAttribute('src')}),10000);v.onloadedmetadata=()=>{clearTimeout(timer);resolve({ok:true,duration:v.duration,width:v.videoWidth,height:v.videoHeight});};v.onerror=()=>{clearTimeout(timer);resolve({ok:false,src:v.getAttribute('src')});};v.load();}))));
assert.ok(videos.every(v=>v.ok&&v.duration>0));
await page.selectOption('#flag','图片');await check('图片记录',161);
const images=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article:not([hidden]) img')].map(async i=>{i.loading='eager';try{await i.decode();return {ok:true};}catch{return {ok:false,src:i.getAttribute('src')};}})));
assert.equal(images.length,159);assert.ok(images.every(i=>i.ok));
await page.selectOption('#flag','');await page.selectOption('#kind','页面');await check('归档页面',95);
await page.selectOption('#kind','尺寸与技术文件');await check('尺寸与技术资源记录',1091);
await page.fill('#q','肯定没有此素材-404');await check('无匹配',0);
await page.fill('#q','');await page.selectOption('#kind','商品');
const localLinks=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('nav a')].map(a=>a.href).filter(u=>u.startsWith(location.origin)).map(async url=>{const r=await fetch(url);return {url,status:r.status};})));
assert.ok(localLinks.every(r=>r.status===200));
const layouts=[];
for(const width of [1366,390]){
 await page.cdp('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
 const layout=await page.evaluate(()=>({viewport:innerWidth,contentWidth:document.documentElement.scrollWidth,visible:[...document.querySelectorAll('article')].filter(e=>!e.hidden).length}));
 layouts.push(layout);assert.ok(layout.contentWidth<=layout.viewport);
}
await page.cdp('Emulation.clearDeviceMetricsOverride');
const report={checks,product_images_decoded:productImages.length,original_images_decoded:images.length,video_metadata:videos,local_navigation:localLinks,layout_measurements:layouts,confirmed_copy_visible:await page.evaluate(()=>document.body.innerText.includes('这批材料已经用户确认')),browser:'Ego Lite真实浏览器',scope:'交互、实际本地HTTP加载、媒体解码、宽度几何检查；未访问官网实时页面'};
await fs.writeFile('D:/codex_work/projects/木子姐ai全自动/整理过程/继续核验/官网预览浏览器核验.json',JSON.stringify(report,null,2),'utf8');
console.log(report);
await page.goto('http://127.0.0.1:8774/'+encodeURIComponent('素材库')+'/'+encodeURIComponent('素材预览.html'),{timeout:30000});
console.log(await page.snapshot());
