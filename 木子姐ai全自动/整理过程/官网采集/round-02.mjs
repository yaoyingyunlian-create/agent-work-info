const task = await taskSpace(91);
const page = task.page('p1');
const fs = await import('node:fs/promises');
const dir = 'D:/codex_work/projects/木子姐ai全自动/官网资料/2026-11-24';
await fs.mkdir(dir+'/浏览器快照', {recursive:true});
async function capture(name) {
  const result=await page.evaluate(()=>({url:location.href,title:document.title,lang:document.documentElement.lang,text:document.body.innerText,html:document.documentElement.outerHTML,links:[...document.querySelectorAll('a[href]')].map(a=>({text:a.innerText,url:a.href})),media:[...document.querySelectorAll('img,video,source')].map(e=>({tag:e.tagName,url:e.currentSrc||e.src,srcset:e.srcset,alt:e.alt})),styleAssets:[...document.querySelectorAll('[style]')].map(e=>e.getAttribute('style')).filter(s=>s.includes('url('))}));
  await fs.writeFile(dir+'/浏览器快照/'+name+'.json',JSON.stringify(result,null,2),'utf8');
  await fs.writeFile(dir+'/浏览器快照/'+name+'.html',result.html,'utf8');
  await page.screenshot({path:dir+'/浏览器快照/'+name+'.png'});
  console.log({name,url:result.url,lang:result.lang,text:result.text.slice(0,600),media:result.media,styleAssets:result.styleAssets});
}
await capture('首页-英文');
await page.click('loc=css:button[aria-label="Switch English and Chinese"]');
await capture('首页-中文');
console.log(await page.snapshot({scope:'full_page'}));
