const task = await taskSpace('LA REINE 官网资料整理 20261124');
const page = task.page('p1');
console.log({spaceId: task.spaceId, page: page.label});
try { await page.goto('https://www.lareine.com.sg', {timeout:45000}); }
catch(e) { console.log({navigationError:String(e)}); }
console.log(await page.snapshot({scope:'full_page'}));
