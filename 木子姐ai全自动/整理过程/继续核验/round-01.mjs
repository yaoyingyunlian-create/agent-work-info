const spaces=await listTaskSpaces();
const old=spaces.find(s=>s.id===91);
const task=!old ? await taskSpace('资料库继续核验 20261124') : old.ownership==='user' ? await claimTaskSpace(91) : await taskSpace(91);
const page=(await task.pages())[0]??await task.adopt((await task.tabs())[0].page);
console.log({spaceId:task.spaceId,page:page.label});
await page.goto('http://127.0.0.1:8774/'+encodeURIComponent('官网资料')+'/2026-11-24/'+encodeURIComponent('官网资料预览.html'),{timeout:30000});
console.log(await page.snapshot());
