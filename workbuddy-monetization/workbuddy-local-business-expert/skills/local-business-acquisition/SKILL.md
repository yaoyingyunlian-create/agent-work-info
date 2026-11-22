---
name: local-business-acquisition
description: 为美甲、美睫、皮肤管理和美发等线下美业单店建立匿名经营档案，生成 7 天到店获客计划、活动毛利测算、渠道营销素材和每日复盘建议；不代运营、不自动发布、不承诺经营结果。
allowed-tools: Read, Write, Bash
---

# WorkBuddy 本地商家获客专家

仅收集门店昵称和汇总经营数据；不得记录店主、顾客的真实姓名、电话、微信号、精确地址或订单明细。所有输出用简体中文，不承诺客流、营收、成交率等结果。

## 门店档案

新建或查看匿名门店档案：

```bash
python "${CODEBUDDY_PLUGIN_ROOT}/scripts/manage_store.py" add --nickname "小鹿美甲" --business-type 美甲 --stage 新店 --city-tier 二线 --district 商圈 --average-ticket 168 --daily-capacity 8 --daily-visits 2 --budget 1200 --channels 抖音,小红书,朋友圈 --main-problem 缺咨询
python "${CODEBUDDY_PLUGIN_ROOT}/scripts/manage_store.py" list
```

`business-type` 仅支持：美甲、美睫、皮肤管理、美发。档案不得使用真实姓名；若输入疑似手机号，应要求改用门店昵称。

## 生成获客计划

读取门店档案后生成方案：

```bash
python "${CODEBUDDY_PLUGIN_ROOT}/scripts/generate_plan.py" --store "小鹿美甲" --offer "新客单色美甲" --list-price 198 --offer-price 99 --variable-cost 28 --channel-cost 8 --fixed-cost 300
```

当单次活动毛利不大于零时，脚本会拒绝生成“保本”结论。应调整活动价、服务组合或成本后重试。计划只使用门店可用渠道，并同时包含每日渠道动作、承接动作、素材和观察指标。

## 录入复盘

只录入当天的汇总漏斗数据：

```bash
python "${CODEBUDDY_PLUGIN_ROOT}/scripts/record_review.py" --store "小鹿美甲" --plan WBA-20261027-001 --day 1 --views 800 --inquiries 36 --bookings 12 --visits 8 --deals 6 --adds 5 --cost 120 --blocker "晚高峰接待不足"
```

脚本只在有足够的前置数据时输出漏斗判断；没有曝光或咨询等关键数据时，说明样本不足，不虚构原因。复盘建议最多 3 项。

## 数据隔离与交付

默认运行数据写入插件根目录的 `data/`。通过 `WORKBUDDY_LOCAL_BUSINESS_DATA_DIR` 为每个商家指定独立目录，禁止不同商家共用数据目录。计划和复盘结果为 Markdown 文件，可直接交给店主执行。

运行测试：

```bash
python "${CODEBUDDY_PLUGIN_ROOT}/tests/self_test.py"
```
