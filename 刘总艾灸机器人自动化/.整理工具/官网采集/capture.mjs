import fs from 'node:fs/promises';
export const base='D:/codex_work/projects/刘总艾灸机器人自动化/整理成果/官网采集/2026-11-27';
export async function capture(page,route,name){
  await page.goto('https://www.airobot2028.com'+route,{timeout:45000});
  await page.waitForFunction(()=>document.readyState==='complete'&&document.body.innerText.length>50,undefined,{timeout:20000});
  let settled=true;
  try{await page.waitForFunction(()=>!(/加载中|正在加载|Loading/i.test(document.body.innerText)),undefined,{timeout:18000});}catch(e){settled=false;}
  return await saveCurrent(page,route,name,settled);
}
export async function saveCurrent(page,route,name,settled=true){
  try{await page.waitForFunction(()=>!(/加载中|正在加载|Loading/i.test(document.body.innerText)),undefined,{timeout:12000});}catch(e){settled=false;}
  const d=await page.evaluate(()=>({url:location.href,title:document.title,lang:document.documentElement.lang,text:document.body.innerText,html:document.documentElement.outerHTML,links:[...document.querySelectorAll('a[href]')].map(a=>({text:a.innerText,url:a.href})),images:[...document.images].map(i=>({url:i.currentSrc||i.src,alt:i.alt,width:i.naturalWidth,height:i.naturalHeight,srcset:i.srcset})),backgrounds:[...new Set([...document.querySelectorAll('*')].map(e=>getComputedStyle(e).backgroundImage).filter(x=>x.includes('url(')))],media:[...document.querySelectorAll('video,audio,source,iframe')].map(e=>({tag:e.tagName,src:e.src,poster:e.poster})),fields:[...document.querySelectorAll('input,select,textarea,button')].map(e=>({tag:e.tagName,type:e.type,name:e.name,placeholder:e.placeholder,text:e.innerText,options:e.tagName==='SELECT'?[...e.options].map(o=>({text:o.text,value:o.value})):undefined}))}));
  d.requested_url='https://www.airobot2028.com'+route;d.collected_at='2026-11-27';d.settled=settled;
  const key=name||route.slice(1).replaceAll('/','-');
  await fs.writeFile(base+'/页面/'+key+'.json',JSON.stringify(d,null,2),'utf8');await fs.writeFile(base+'/页面/'+key+'.txt',d.text,'utf8');
  console.log(JSON.stringify({key,url:d.url,chars:d.text.length,settled,images:d.images.length,media:d.media.length}));
  return d;
}
