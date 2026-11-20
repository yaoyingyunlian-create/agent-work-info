from pathlib import Path
import re,json
root=Path(__file__).resolve().parent.parent
base=root/'整理成果/知识库/公司OCR'
pages=json.loads((base/'逐页OCR.json').read_text(encoding='utf-8'))
assert [p['page'] for p in pages]==list(range(1,51))
def normalize(text):
    text=re.sub(r'(?<=[\u4e00-\u9fff])[^\S\n]+(?=[\u4e00-\u9fff])','',text)
    return text
alltext='公司PDF 50页OCR检索版。仅清理汉字间空格，不纠正数字、英文和识别错误；原始OCR与页面图像另存。\n'
for p in pages:
    alltext+=f'\n\n【第{p["page"]}页】\n'+normalize(p['text'])
(base/'公司介绍_全量OCR_检索版.txt').write_text(alltext,encoding='utf-8')
topics=['封面','品牌理念','社团资料','公司定位','公司登记截图','股本截图','背景与关联主体介绍','三大业务板块','康养产品表一','康养产品表二','主推康养产品','认证宣传','市场布局','康养设备组合','迎宾配送设备','AI健康机器人生态','市场趋势宣传','加盟方案','教育培训','发展与IPO路线图','上市问题','上市目的','上市标准宣传','创始人介绍','员工持股案例一','员工持股案例二','品牌与上市图示','股权机会宣传','公众股东过渡页','会员与机器人项目关系','认购权证概念','会员套餐表一','会员套餐表二','奖金类别','会员权证方案','新人套餐','商家合作条款','商家推荐奖励','个人租赁托管','托管推荐奖励','权证获取路径','股价预测','退出机制','结束页','托管档位','360天方案一','360天方案二','720天方案一','720天方案二','720天方案三']
md='# 公司PDF全量OCR索引\n\n来源：S005；50页；Windows.Media.Ocr zh-Hans-CN；2026-11-20。所有页面已识别，原始OCR、检索版和原页面均保留。\n\n全量OCR指处理覆盖50/50页，不表示逐字校对完成。中文、英文均有识别结果；表格阅读顺序、数字、I/l/1、O/0等仍可能错误。检索版仅去除汉字间空格。\n\n- [检索版全文](公司介绍_全量OCR_检索版.txt)\n- [原始OCR全文](公司介绍_全量OCR.txt)\n- [逐页JSON](逐页OCR.json)\n- [关键校对与新增发现](关键校对.md)\n\n| 页码 | 内容主题（索引用） | 原始OCR字符数 | 文件 |\n| --- | --- | --- | --- |\n'
for p,topic in zip(pages,topics):
    n=p['page'];stem=f'page-{n:02}'
    md+=f'| {n} | {topic} | {len(p["text"])} | [文本]({stem}.txt) · [原页](页面/{stem}.png) |\n'
(base/'README.md').write_text(md,encoding='utf-8')
print('50 pages; OCR chars:',sum(len(p['text']) for p in pages))
