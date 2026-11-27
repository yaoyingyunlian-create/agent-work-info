const fs=await import('node:fs/promises');const base='D:/codex_work/projects/刘总艾灸机器人自动化/整理成果/官网采集/2026-11-27';
const task=await taskSpace(199);const page=task.page('p1');
console.log(await page.info());
try {console.log('shot',await page.screenshot({path:base+'/页面/home-zh.png'}));}catch(e){console.log('screenshot_failed',e.message.slice(0,160));}
for(const route of ['/robots.txt','/sitemap.xml']){try{const r=await page.fetch(route,{timeout:15000});await fs.writeFile(base+'/'+route.slice(1),r.body,'utf8');console.log(route,r.status,r.body.slice(0,5000));}catch(e){console.log(route,e.message.slice(0,160));}}
console.log(await page.snapshot());
