const task=await taskSpace(91); const page=task.page('p1');
await page.click('loc=css:button[aria-label="Switch English and Chinese"]');
const fs=await import('node:fs/promises');
const dir='D:/codex_work/projects/木子姐ai全自动/官网资料/2026-11-24/浏览器快照';
const data=await page.evaluate(()=>({url:location.href,title:document.title,lang:document.documentElement.lang,classes:document.documentElement.className,text:document.body.innerText,html:document.documentElement.outerHTML}));
await fs.writeFile(dir+'/首页-中文.json',JSON.stringify(data,null,2),'utf8');
await fs.writeFile(dir+'/首页-中文.html',data.html,'utf8');
console.log({url:data.url,lang:data.lang,classes:data.classes,text:data.text.slice(0,1700)});
try{console.log({screenshot:await page.screenshot({path:dir+'/首页-中文.png'})});}catch(e){console.log({screenshotError:String(e)});}
