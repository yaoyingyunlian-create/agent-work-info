const fs=await import('node:fs/promises');const base='D:/codex_work/projects/刘总艾灸机器人自动化/整理成果/官网采集/2026-11-27';
const task=await taskSpace(199);const page=task.page('p1');
for(const route of ['/zh/about','/zh/products','/zh/rental-hosting','/zh/agents','/zh/franchise']){
try{await page.goto('https://www.airobot2028.com'+route,{timeout:45000});
await page.waitForFunction(()=>document.readyState==='complete'&&document.body.innerText.length>200,undefined,{timeout:20000});
const d=await page.evaluate(()=>({url:location.href,title:document.title,lang:document.documentElement.lang,text:document.body.innerText,html:document.documentElement.outerHTML,links:[...document.querySelectorAll('a[href]')].map(a=>({text:a.innerText,url:a.href})),images:[...document.images].map(i=>({url:i.currentSrc||i.src,alt:i.alt,width:i.naturalWidth,height:i.naturalHeight,srcset:i.srcset})),backgrounds:[...document.querySelectorAll('main *')].map(e=>getComputedStyle(e).backgroundImage).filter(x=>x!=='none'),media:[...document.querySelectorAll('video,audio,source,iframe')].map(e=>({tag:e.tagName,src:e.src,poster:e.poster}))}));
const name=route.slice(1).replaceAll('/','-');await fs.writeFile(base+'/页面/'+name+'.json',JSON.stringify(d,null,2),'utf8');await fs.writeFile(base+'/页面/'+name+'.txt',d.text,'utf8');console.log(JSON.stringify({route,url:d.url,title:d.title,chars:d.text.length,images:d.images,media:d.media,links:d.links}));
}catch(e){console.log('FAILED',route,e.message.slice(0,200));}}
console.log(await page.snapshot());
