const task=await taskSpace(91);
await task.finish({keep:[]});
console.log('官网采集与本地预览验收已结束，浏览器任务空间已关闭。');
