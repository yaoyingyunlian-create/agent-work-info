const task=await taskSpace(91); const page=task.page('p1');
await page.goto('https://lareine.com.sg/product/aqua-light-toner/',{timeout:45000});
const fs=await import('node:fs/promises');
const dir='D:/codex_work/projects/木子姐ai全自动/官网资料/2026-11-24/浏览器快照';
const one=await page.evaluate(()=>({url:location.href,title:document.title,text:document.body.innerText,languageBody:document.body.className}));
await fs.writeFile(dir+'/产品抽查-切换前.json',JSON.stringify(one,null,2),'utf8');
console.log({before:one.text.slice(0,1600)});
console.log(await page.snapshot());
