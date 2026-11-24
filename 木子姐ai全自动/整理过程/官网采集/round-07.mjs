const task=await taskSpace(91); const page=task.page('p1');
await page.goto('http://127.0.0.1:8773/%E5%AE%98%E7%BD%91%E8%B5%84%E6%96%99/2026-11-24/%E5%AE%98%E7%BD%91%E8%B5%84%E6%96%99%E9%A2%84%E8%A7%88.html',{timeout:30000});
console.log(await page.snapshot());
console.log(await page.evaluate(()=>({title:document.title,count:document.querySelector('#count').textContent,total:document.querySelectorAll('article').length,visible:[...document.querySelectorAll('article')].filter(e=>!e.hidden).length,loadedImages:[...document.images].filter(i=>i.complete&&i.naturalWidth>0).length})));
