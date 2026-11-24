const task=await taskSpace(92),page=task.page('p1');
const fs=await import('node:fs/promises'),assert=(await import('node:assert/strict')).default;
await page.reload();
const selectors=await page.evaluate(()=>({q:!!document.querySelector('#q'),group:!!document.querySelector('#group'),lang:!!document.querySelector('#lang')}));
assert.ok(selectors.q&&selectors.group&&selectors.lang);
const checks=[];async function check(name,n){const count=await page.evaluate(()=>[...document.querySelectorAll('article')].filter(e=>!e.hidden).length);assert.equal(count,n);checks.push({name,count,passed:true});}
await check('全部图片与PDF页',76);
await page.fill('#q','A020');await check('图片编号',1);
await page.fill('#q','');await page.selectOption('#lang','英文');await check('英文图片及PDF页',17);
await page.fill('#q','D002');await check('英文PDF页',8);
await page.selectOption('#lang','中文');await check('组合无匹配',0);
await page.fill('#q','');await page.selectOption('#lang','');await page.selectOption('#group','Yvelise双乳礼盒');await check('产品分类',10);
await page.selectOption('#group','');
const images=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('article img')].map(async i=>{i.loading='eager';try{await i.decode();return {ok:true};}catch{return {ok:false,src:i.getAttribute('src')};}})));
assert.equal(images.length,76);assert.ok(images.every(i=>i.ok));
const links=await page.evaluate(async()=>await Promise.all([...document.querySelectorAll('nav a')].map(a=>a.href).filter(u=>u.startsWith(location.origin)).map(async url=>{const r=await fetch(url);return {url,status:r.status};})));
assert.ok(links.every(r=>r.status===200));
const layouts=[];
for(const width of [1366,390]){
 await page.cdp('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
 const s=await page.evaluate(()=>({viewport:innerWidth,contentWidth:document.documentElement.scrollWidth}));layouts.push(s);assert.ok(s.contentWidth<=s.viewport);
}
await page.cdp('Emulation.clearDeviceMetricsOverride');
const report={checks,images_decoded:images.length,local_navigation:links,layout_measurements:layouts,confirmed_copy_visible:await page.evaluate(()=>document.body.innerText.includes('这批材料已经用户确认')),browser:'Ego Lite真实浏览器',scope:'图片和全部16页PDF渲染图的加载检查；非对PDF成分与功效的重新判定'};
const dir='D:/codex_work/projects/木子姐ai全自动/整理过程/继续核验';
await fs.writeFile(dir+'/微信预览浏览器核验.json',JSON.stringify(report,null,2),'utf8');console.log(report);
try{const shot=await page.cdp('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});await fs.writeFile(dir+'/微信预览-桌面.png',Buffer.from(shot.data,'base64'));console.log({screenshot:'微信预览-桌面.png'});}catch(e){await fs.writeFile(dir+'/截图未完成.json',JSON.stringify({error:String(e),scope:'截图视觉验收未完成；交互与图片加载验证已完成'},null,2),'utf8');console.log({screenshotError:String(e)});}
