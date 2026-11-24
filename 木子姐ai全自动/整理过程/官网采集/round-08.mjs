const task=await taskSpace(91); const page=task.page('p1');
const fs=await import('node:fs/promises');
const assert=(await import('node:assert/strict')).default;
const checks=[];
async function state(label,expected){
 const result=await page.evaluate(()=>({visible:[...document.querySelectorAll('article')].filter(e=>!e.hidden).length,count:document.querySelector('#count').textContent,empty:!document.querySelector('#empty').hidden}));
 assert.equal(result.visible,expected);checks.push({label,...result});
}
await page.fill('#q','aqua light toner');await state('商品搜索',1);
await page.fill('#q','');await page.selectOption('#flag','待确认模板');await state('疑似模板',15);
await page.selectOption('#flag','');await page.selectOption('#kind','原始素材');await state('公开媒体记录',180);
await page.selectOption('#flag','视频');await state('视频筛选',3);
const videos=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article:not([hidden]) video')].map(v=>new Promise(resolve=>{
 const timeout=setTimeout(()=>resolve({url:v.getAttribute('src'),error:'metadata timeout'}),10000);
 v.addEventListener('loadedmetadata',()=>{clearTimeout(timeout);resolve({url:v.getAttribute('src'),duration:v.duration,width:v.videoWidth,height:v.videoHeight});},{once:true});
 v.addEventListener('error',()=>{clearTimeout(timeout);resolve({url:v.getAttribute('src'),error:'media error'});},{once:true});v.load();
}))));
assert.equal(videos.length,3);assert.ok(videos.every(v=>!v.error&&v.duration>0));
await page.selectOption('#flag','图片');await state('原始图片记录含2条同源失效占位图',161);
const images=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article:not([hidden]) img')].map(async i=>{i.loading='eager';try{await i.decode();return {ok:true};}catch(e){return {ok:false,src:i.getAttribute('src')};}})));
assert.equal(images.length,159);assert.ok(images.every(i=>i.ok));
await page.selectOption('#flag','');await page.selectOption('#kind','页面');await state('页面筛选',95);
await page.fill('#q','不存在的素材-123');await state('无匹配',0);
await page.fill('#q','');await page.selectOption('#kind','商品');await state('恢复商品视图',40);
const report={checks,videos,image_decode:{count:images.length,all_passed:true},real_browser:'Ego Lite',source:'本地HTTP预览'};
const dir='D:/codex_work/projects/木子姐ai全自动/官网资料/2026-11-24';
await fs.writeFile(dir+'/本地预览浏览器验收.json',JSON.stringify(report,null,2),'utf8');
console.log(report);
try{console.log({screenshot:await page.screenshot({path:dir+'/浏览器快照/本地官网素材预览.png'})});}catch(e){console.log({screenshotError:String(e)});}
