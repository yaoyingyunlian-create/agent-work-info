const fs=await import('node:fs/promises');
const base='D:/codex_work/projects/刘总艾灸机器人自动化/整理成果/官网采集/2026-11-27';
await fs.mkdir(base+'/页面',{recursive:true});
const task=await taskSpace(199);const page=task.page('p1');
const data=await page.evaluate(()=>({url:location.href,title:document.title,lang:document.documentElement.lang,text:document.body.innerText,html:document.documentElement.outerHTML,links:[...document.querySelectorAll('a[href]')].map(a=>({text:a.innerText,url:a.href})),images:[...document.images].map(i=>({url:i.currentSrc||i.src,alt:i.alt,width:i.naturalWidth,height:i.naturalHeight,srcset:i.srcset})),backgrounds:[...document.querySelectorAll('*')].map(e=>getComputedStyle(e).backgroundImage).filter(x=>x!=='none'),media:[...document.querySelectorAll('video,audio,source,iframe')].map(e=>({tag:e.tagName,src:e.src,poster:e.poster})),alternates:[...document.querySelectorAll('link[rel=alternate]')].map(e=>({lang:e.hreflang,url:e.href}))}));
await fs.writeFile(base+'/页面/home-zh.json',JSON.stringify(data,null,2),'utf8');
await fs.writeFile(base+'/页面/home-zh.txt',data.text,'utf8');
console.log(JSON.stringify({...data,text:data.text,html:undefined},null,2));
console.log('screenshot',await page.screenshot({path:base+'/页面/home-zh.png'}));
