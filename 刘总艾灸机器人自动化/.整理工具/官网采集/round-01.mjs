const task = await taskSpace('CUCA官网知识与素材采集20261127');
const page = task.page('p1');
console.log({taskSpaceId:task.spaceId,page:page.label});
await page.goto('https://www.airobot2028.com/',{timeout:60000});
console.log(await page.snapshot({scope:'full_page'}));
console.log(await page.evaluate(()=>({title:document.title,links:[...document.querySelectorAll('a[href]')].map(a=>({text:a.innerText,url:a.href})),images:[...document.images].map(i=>({url:i.currentSrc||i.src,alt:i.alt})),media:[...document.querySelectorAll('video,audio,source')].map(e=>({tag:e.tagName,src:e.src,poster:e.poster}))})));
