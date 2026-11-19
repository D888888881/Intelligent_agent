# -*- coding: utf-8 -*-
"""填写绩效考核表（Intelligent Agent / Afs Agent 项目）。"""
from __future__ import annotations

import shutil
from pathlib import Path

import openpyxl

SRC = Path(r"c:\Users\34847\Downloads\绩效考核丁存恒.xlsx")
OUT_DOWNLOADS = Path(r"c:\Users\34847\Downloads\绩效考核丁存恒_已填写.xlsx")
OUT_PROJECT = Path(__file__).resolve().parents[1] / "docs" / "绩效考核丁存恒_202611.xlsx"

# (项目节点明细, 分值, 数据来源, 完成情况, 备注含时间段)
ROWS = [
    (
        "【11.01–11.08】Intelligent Agent 工程骨架：Django 多应用拆分、PostgreSQL 迁移、"
        "Celery 生图队列与健康检查 / 本地启动脚本",
        8,
        "代码仓库 README、/health/",
        "已完成",
        "基础环境与可部署结构",
    ),
    (
        "【11.01–11.08】账户与权限：注册登录 API、用户审批、UserProfile 与 model_catalog 模型偏好",
        8,
        "accounts 应用、管理后台",
        "已完成",
        "支撑公司内部账号使用",
    ),
    (
        "【11.09–11.12】登录/注册页 WebGL 宇宙海背景：Three.js 接入、auth-bg-fallback 降级、"
        "模板与静态资源版本管理",
        10,
        "static/js/auth-bg.js、templates/login.html",
        "已完成",
        "首屏视觉与稳定性",
    ),
    (
        "【11.12–11.15】液态银河海面：程序化贴图、多河带星系团着色、极光远景层",
        10,
        "makeCosmicSeaTexture、海面 shader",
        "已完成",
        "品牌差异化背景",
    ),
    (
        "【11.16–11.20】海面起伏迭代：主风向小浪、浪峰 bump、半俯瞰视角与海星 6:4 画幅",
        12,
        "auth-bg.js 波形与相机参数",
        "已完成",
        "多轮按反馈调参",
    ),
    (
        "【11.19–11.22】海面交互：鼠标点击/悬停涟漪（uRipples）、DOM 水纹动画与 CSS 联动",
        8,
        "auth-bg.js、app.css",
        "已完成",
        "取消自动涟漪，保留手动交互",
    ),
    (
        "【11.23–11.27】宇航员体系：GLTF 双备源加载、3 人左/中/右分区漂移、屏内 NDC 约束",
        12,
        "createSkyAstronaut、ASTRO_ZONES",
        "已完成",
        "避免三人扎堆",
    ),
    (
        "【11.26–11.28】星空卫星：程序化卫星模型、光晕与指示灯动画，左中天空锚点",
        8,
        "buildAuthSatellite",
        "已完成",
        "可见性增强",
    ),
    (
        "【11.26–11.30】登录框 UI 融合：毛玻璃、渐变标题、输入框/按钮与宇宙海配色统一",
        8,
        "app.css auth-card-glass",
        "已完成",
        "登录/注册页同步",
    ),
    (
        "【11.09–11.30】套图生成与对话链路维护：generation pipeline、GRSAI 调度、"
        "job 恢复与多市场 listing 策略模块",
        16,
        "generation/、chat/ 服务代码",
        "已完成",
        "核心业务 Afs Agent 能力",
    ),
]


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"源文件不存在: {SRC}")

    shutil.copy2(SRC, OUT_DOWNLOADS)
    wb = openpyxl.load_workbook(OUT_DOWNLOADS)
    ws = wb.active

    for i, (detail, score, source, status, note) in enumerate(ROWS):
        r = 5 + i
        ws.cell(r, 3, detail)
        ws.cell(r, 4, score)
        ws.cell(r, 5, source)
        ws.cell(r, 6, status)
        ws.cell(r, 8, note)

    OUT_PROJECT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT_DOWNLOADS)
    shutil.copy2(OUT_DOWNLOADS, OUT_PROJECT)
    print(f"已写入: {OUT_DOWNLOADS}")
    print(f"备份: {OUT_PROJECT}")
    print(f"分值合计: {sum(x[1] for x in ROWS)}")


if __name__ == "__main__":
    main()