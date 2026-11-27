const task=await taskSpace(199);const page=task.page('p1');
console.log(await page.info());console.log(await page.snapshot());
console.log(await page.evaluate(()=>[...document.querySelectorAll('button')].filter(b=>['规格参数','产品视频','客户评价'].includes(b.innerText.trim())).map(b=>({text:b.innerText,rect:b.getBoundingClientRect().toJSON(),display:getComputedStyle(b).display}))));
