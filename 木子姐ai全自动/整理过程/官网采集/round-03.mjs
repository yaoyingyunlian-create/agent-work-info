const task=await taskSpace(91); const page=task.page('p1');
console.log(await page.snapshot({scope:'full_page'}));
console.log(await page.evaluate(()=>({url:location.href,lang:document.documentElement.lang,button:document.querySelector('button[aria-label="Switch English and Chinese"]')?.outerHTML,resources:performance.getEntriesByType('resource').map(r=>r.name)})));
