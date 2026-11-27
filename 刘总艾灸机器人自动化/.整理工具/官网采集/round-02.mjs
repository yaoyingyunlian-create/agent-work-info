const task=await taskSpace(199);const page=task.page('p1');
console.log(await page.info());
console.log(await page.evaluate(()=>({url:location.href,ready:document.readyState,html:document.documentElement.outerHTML.slice(0,12000)})));
console.log(await page.snapshot({scope:'full_page'}));
