#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a unified, searchable catalog of the project's reusable media."""
from pathlib import Path
import csv, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "素材库"
OUT.mkdir(exist_ok=True)

def read_manifest(path):
    if not path.exists(): return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row.get("File", ""): row for row in csv.DictReader(f)}

city_sources = read_manifest(ROOT / "城市图片" / "素材来源.csv")
video_sources = read_manifest(ROOT / "剧情视频素材" / "素材来源.csv")
rows = []

def add(path, category, kind, tags="", usage="", rights="", seconds="", preview=""):
    path = Path(path)
    rows.append({
        "名称": path.name,
        "类别": category,
        "类型": kind,
        "主题标签": tags,
        "建议用途": usage,
        "授权备注": rights,
        "时长秒": seconds,
        "预览图": preview,
        "项目相对路径": path.relative_to(ROOT).as_posix(),
        "本机完整路径": str(path.resolve()),
    })

def video_duration(path):
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True,
            text=True, encoding="utf-8", timeout=20, check=True)
        return f"{float(p.stdout.strip()):.2f}"
    except Exception:
        return ""

character_roles = {
    "01.png": ("历史角色,未来战士,银发,半机械", "旧系列角色核验"),
    "02.png": ("当前固定角色,古代侠女,白灰云纹衣,带鞘佩剑", "新系列核对五官、高髻发簪、耳饰、腰封、护腕与带鞘佩剑"),
}
for p in sorted((ROOT / "数字人").rglob("*")):
    if p.is_file():
        tags, usage = character_roles.get(p.name, ("角色素材", "核实用途后选用"))
        add(p, "01 数字人", p.suffix.lower().lstrip("."), tags, usage, "项目角色参考")

for p in sorted((ROOT / "城市图片").rglob("*")):
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}: continue
    source = city_sources.get(p.name, {})
    group = p.parent.name if p.parent != ROOT / "城市图片" else "其他城市图片"
    tags = re.sub(r"[_\- ]+", ",", p.stem)
    add(p, f"02 阳新实景参考/{group}", "图片", tags,
        "地点建立镜头、环境插镜、AI场景参考", source.get("Usage", "阳新城市参考图"), source.get("RightsNote", "发布前核对授权"))

for p in sorted((ROOT / "剧情视频素材").glob("*.mp4")):
    source = video_sources.get(p.name, {})
    add(p, "03 外部视频参考", "视频", source.get("Usage", p.stem),
        "运镜、动作、服装、氛围参考；不得默认直接搬用画面或原声", source.get("RightsNote", "用户提供；发布前确认授权"), video_duration(p),
        f"剧情视频素材/图片索引/{p.stem}/视频联系表.jpg")

for p in sorted((ROOT / "剧情视频素材" / "图片索引").glob("*/*.jpg")):
    if p.name == "视频联系表.jpg": continue
    add(p, "04 外部视频抽帧", "图片", p.parent.name, "按时间点快速查找参考构图/动作；关联原视频使用", "仅内部参考，公开使用先确认授权", "", "")

generated_roots = [ROOT / "剧情视频素材" / "生成素材", ROOT / "成片" / "第02集_返航坐标阳新", ROOT / "成片" / "工作区"]
for base in generated_roots:
    if not base.exists(): continue
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".mp4", ".png", ".jpg", ".jpeg"}: continue
        if "quality" in p.parts or p.name.startswith("抽帧_"): continue
        ep = next((part for part in p.parts if re.match(r"第\d+集", part)), base.name)
        kind = "视频" if p.suffix.lower() == ".mp4" else "图片"
        add(p, f"05 项目生成素材/{ep}", kind, ep.replace("_", ","), "复用镜头、节奏、角色动作或构图参考", "项目生成素材", video_duration(p) if kind == "视频" else "")

for p in sorted((ROOT / "成片").glob("20??-??/*/视频.mp4")):
    add(p, f"06 已归档成片/{p.parent.parent.name}", "视频", p.parent.name, "叙事连续性、过往剧情与剪辑参考", "项目成片", video_duration(p), f"{p.parent.relative_to(ROOT).as_posix()}/封面.jpg")

rows.sort(key=lambda x: (x["类别"], x["名称"], x["项目相对路径"]))
csv_path = OUT / "素材总目录.csv"
with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["名称"])
    writer.writeheader(); writer.writerows(rows)

counts = {}
for row in rows: counts[row["类别"]] = counts.get(row["类别"], 0) + 1
guide = ["# 阳新数字人项目素材库", "", "按剧情策划阶段快速查找角色、阳新实景、参考视频和既有生成镜头。原素材保留在原目录；本目录只集中提供索引，不复制大型文件。", "",
         "## 素材分类", ""]
guide += [f"- `{k}`：{v}项" for k, v in counts.items()]
guide += ["", "## 快速使用", "", "1. 打开 `素材总目录.csv`，按类别筛选后搜索地点、主题、动作或情绪关键词。", "2. 图片素材可用 `预览图` 路径查看；参考视频对应每3秒抽帧联系表在 `剧情视频素材/图片索引/`。", "3. 侠女新作以 `数字人/02.png` 核对角色；`数字人/01.png` 用于历史系列。地点建立镜头从阳新实景图片挑选；动作和运镜可参考联系表。", "4. `本机完整路径` 可直接用于本机工作流；`项目相对路径` 便于迁移项目。", "5. 参考视频和城市转载图仅在授权范围内使用。标签和用途用于规划检索，不代表已确认素材权利。", "", "## 原素材位置", "", "- 角色：`数字人/`", "- 阳新照片：`城市图片/`", "- 外部参考视频和抽帧：`剧情视频素材/`", "- AI生成源片：`剧情视频素材/生成素材/`、`成片/第02集_返航坐标阳新/`、`成片/工作区/`", "- 最终作品：`成片/YYYY-MM/作品名/`", ""]
(OUT / "使用指南.md").write_text("\n".join(guide), encoding="utf-8")
print(json.dumps({"catalog": str(csv_path), "items": len(rows), "categories": counts}, ensure_ascii=False, indent=2))
