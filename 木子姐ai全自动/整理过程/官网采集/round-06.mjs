const task=await taskSpace(91); const page=task.page('p1');
await page.click('loc=css:button[aria-label="Switch English and Chinese"]');
const fs=await import('node:fs/promises');
const data=await page.evaluate(()=>({url:location.href,title:document.title,text:document.body.innerText}));
await fs.writeFile('D:/codex_work/projects/木子姐ai全自动/官网资料/2026-11-24/浏览器快照/产品抽查-英文.json',JSON.stringify(data,null,2),'utf8');
console.log({text:data.text.slice(0,900),hasChineseBenefits:data.text.includes('悉心研制')});
