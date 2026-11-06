# GloriaX · 璞慧资料中心

客户知识库与素材库，可完整离线使用。打开根目录 `index.html`，或在 Windows 双击 `打开资料库.cmd`。不需要 Codex、网络、Python 或数据库。

## 客户电脑迁移

1. 将完整项目文件夹或 `dist/GloriaX-client.zip` 复制到客户电脑。
2. ZIP先完整解压，保持目录结构，不在压缩包内直接打开页面。
3. 双击 `index.html`，进入知识库或素材库。视频通过浏览器或系统播放器打开。

不要只复制 HTML，`资料库/原始资料`、预览、索引和知识库都必须一起交付。备份整个目录即可恢复。当前客户实际电脑尚未验收。

## 开发维护

Python 3.10+。查看、重新生成HTML、校验与打包只使用标准库：

```powershell
python 资料库/scripts/library.py render
python 资料库/scripts/library.py verify
python 资料库/scripts/library.py package
```

默认生成 `dist/GloriaX-client.zip`，已有同名包时会停止，避免覆盖；可使用 `--output dist/GloriaX-client-v2.zip`。打包前自动校验，输出包经过ZIP完整性检查。Git目录、虚拟环境、缓存、临时文件、dist与环境变量文件不进入交付包。

只有导入新文件、重建图片及视频预览、重新提取PDF时才需要额外工具：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# 安装 FFmpeg（包含ffprobe）、Poppler（包含pdftoppm），加入PATH。
.venv\Scripts\python 资料库/scripts/build_library.py
# 或从另一个资料文件夹增量导入：
.venv\Scripts\python 资料库/scripts/build_library.py --source "客户提供资料目录"
```

`PDFTOPPM` 可指定 pdftoppm 路径，`LIBRARY_FONT` 可指定总览字体；默认字体自动回退。依赖锁定为本次已实际使用的版本，无需安装到系统Python。

导入会保留原文件、复用既有ID、新文件追加ID。相同名称但内容不同会在写入前停止，需人工改名再导入。分类、简介与审阅状态存储于 `资料库/索引/素材标注.json`，按SHA-256关联，不再依赖文件排序。新增内容默认待分类；知识库中的人工整理文档需同步更新。当前PDF处理针对“8种不同产品介绍.pdf”，新增其他PDF仅归档，需另行提取整理。

## GitHub 提交

本项目已准备 `.gitignore`、`.gitattributes` 和持续校验配置。资料包含客户人物图片及原始需求，建议使用客户授权的私有仓库。当前约186MB，单个文件小于20MB，本次未引入Git LFS。ZIP交付包不提交到Git。

在项目根目录检查并明确添加需要提交的文件：

```powershell
git status --short
git add .gitignore .gitattributes .github README.md requirements.txt index.html 打开资料库.cmd 资料库
git diff --cached --stat
git commit -m "Prepare portable GloriaX knowledge and asset library"
# 将下面地址替换为实际私有仓库地址：
git remote add origin <仓库地址>
git push -u origin main
```

尚未创建远程仓库、提交或推送。本机 Git 已初始化时无需重复初始化。

## 验证与边界

校验覆盖清单/原始文件一致性、SHA-256、稳定ID、重复关联、全部页面本地链接和预览文件。迁移后可重新运行校验，无需安装第三方Python包。GitHub Actions使用同样命令检查提交内容。

资料情况与尚未完成的转录、OCR及功效核实见 [资料库说明](资料库/README.md)。本项目目前是离线文件资料中心，尚未接入向量数据库或AI问答。
