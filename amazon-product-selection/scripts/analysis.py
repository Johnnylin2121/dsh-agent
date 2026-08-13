#!/usr/bin/env python3
"""
亚马逊选品分析脚本
基于卖家精灵导出的关键词数据，执行趋势、机会、利润、综合评分分析。

用法:
    # 卖家精灵标准数据
    python analysis.py report --input data.xlsx --output report.md
    python analysis.py preprocess --input data.xlsx

    # ABA 关键词趋势数据
    python analysis.py aba-report --input data.xlsx --output report.md

依赖:
    pip install pandas openpyxl
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re


# ============================================================
# 默认参数
# ============================================================

DEFAULT_PARAMS = {
    # 趋势筛选
    "trend_min_search": 1000,
    "trend_min_growth": 0.10,

    # 机会筛选
    "opp_min_dsr": 10,
    "opp_max_reviews": 500,
    "opp_min_search": 500,
    "opp_min_price": 200,

    # 利润筛选
    "profit_min_search": 2000,
    "profit_price_min": 300,
    "profit_price_max": 3000,
    "profit_max_reviews": 800,
    "profit_max_products": 500,

    # 综合评分
    "score_min_search": 1000,
    "score_min_dsr": 5,
    "score_max_reviews": 1000,
    "score_min_price": 200,
    "weight_search": 0.30,
    "weight_dsr": 0.30,
    "weight_growth": 0.20,
    "weight_competition": 0.20,

    # 价格段
    "price_bins": [0, 500, 1000, 2000, 5000, float('inf')],
    "price_labels": ["<500", "500-1000", "1000-2000", "2000-5000", "5000+"],

    # 输出
    "top_n": 10,
    "output_dir": r"D:\OneDrive\ObsidianVault\工作\选品报告",
}

# 品类分类规则
CATEGORY_RULES = {
    "充电/电源类": ["cargador", "charger", "usb", "cable", "power bank", "batería", "bateria", "nexode", "carga"],
    "音频类": ["audífono", "audifono", "earbuds", "speaker", "sonido", "audio", "wf-", "sonos", "airpods"],
    "支架/配件类": ["soporte", "mount", "holder", "stand", "tripie", "trípode"],
    "显示/电视类": ["tv", "pantalla", "monitor", "led", "antena", "antenna", "hdmi"],
    "摄影类": ["cámara", "camara", "lente", "lens", "dji", "gopro", "insta"],
    "外设/游戏类": ["teclado", "keyboard", "mouse", "ratón", "gaming", "logitech", "rog"],
    "智能/网络类": ["wifi", "router", "bluetooth", "smart", "ring", "switch"],
    "散热/照明类": ["fan", "ventilador", "cooling", "foco", "lamp", "led strip"],
}


# ============================================================
# 共享工具函数
# ============================================================

# 站点配置
SITE_CONFIG = {
    "MX": {"name": "墨西哥", "currency": "MX$", "domain": "amazon.com.mx"},
    "US": {"name": "美国", "currency": "$", "domain": "amazon.com"},
    "JP": {"name": "日本", "currency": "¥", "domain": "amazon.co.jp"},
    "EU": {"name": "欧洲", "currency": "€", "domain": "amazon.de"},
}

# 各站点 PPC 价格评分阈值（用于 score_ad_efficiency 和 assess_risk）
# 格式: [低, 中低, 中, 中高] — 越低越好
SITE_PPC_THRESHOLDS = {
    "MX": [2, 5, 10, 15],
    "US": [0.5, 1, 2, 5],
    "JP": [50, 100, 200, 500],
    "EU": [0.5, 1, 2, 5],
    "default": [2, 5, 10, 15],
}


def infer_site(filename: str) -> dict:
    """
    从文件名推断站点信息

    Returns:
        dict with keys: name, currency, domain, code
    """
    filename_upper = filename.upper()
    for code, config in SITE_CONFIG.items():
        if code in filename_upper:
            return {"code": code, **config}
    return {"code": "未知", "name": "未知", "currency": "", "domain": "amazon.com"}


def write_report_file(report: str, output_path: str) -> str:
    """写入报告文件"""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    return output_path


def extract_regex_field(series: pd.Series, pattern: str, default=0.0):
    """从字符串列中提取正则匹配的数值"""
    def _extract(x):
        if pd.isna(x):
            return default
        match = re.search(pattern, str(x))
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except (ValueError, IndexError):
                return default
        return default
    return series.apply(_extract)


# ============================================================
# 核心函数
# ============================================================

def clean_price(series: pd.Series) -> pd.Series:
    """清洗价格列，去除货币符号和千位分隔符，转为数值"""
    def _clean(x):
        if pd.isna(x):
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        x = str(x)
        x = re.sub(r'[A-Z]{2,3}\$', '', x)  # 去除 USD$, MX$ 等
        x = x.replace(',', '').strip()
        try:
            return float(x)
        except ValueError:
            return 0.0
    return series.apply(_clean)


def load_and_preprocess(filepath: str) -> pd.DataFrame:
    """加载并预处理 Excel 数据"""
    df = pd.read_excel(filepath)

    # 清洗价格列
    if '均价' in df.columns:
        df['均价_num'] = clean_price(df['均价'])
    else:
        df['均价_num'] = 0.0

    # 确保数值列类型正确
    numeric_cols = ['月搜索量', '商品数', '需供比', '评分数', '近3个月增长率', '搜索增长率']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df


def filter_trending(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """趋势市场筛选：高搜索量 + 高增长率"""
    mask = (
        (df['月搜索量'] > params['trend_min_search']) &
        (df['近3个月增长率'] > params['trend_min_growth'])
    )
    result = df[mask].copy()
    result = result.sort_values('近3个月增长率', ascending=False)
    return result


def filter_opportunity(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """机会市场筛选：高需供比 + 低评论"""
    mask = (
        (df['需供比'] > params['opp_min_dsr']) &
        (df['评分数'] < params['opp_max_reviews']) &
        (df['月搜索量'] > params['opp_min_search']) &
        (df['均价_num'] > params['opp_min_price'])
    )
    result = df[mask].copy()
    result = result.sort_values('需供比', ascending=False)
    return result


def filter_profitable(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """利润空间筛选：高搜索 + 合理价格 + 低竞争"""
    mask = (
        (df['月搜索量'] > params['profit_min_search']) &
        (df['均价_num'] > params['profit_price_min']) &
        (df['均价_num'] < params['profit_price_max']) &
        (df['评分数'] < params['profit_max_reviews']) &
        (df['商品数'] < params['profit_max_products'])
    )
    result = df[mask].copy()
    result = result.sort_values('月搜索量', ascending=False)
    return result


def calculate_composite_score(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """综合评分：多维加权排序"""
    mask = (
        (df['月搜索量'] > params['score_min_search']) &
        (df['需供比'] > params['score_min_dsr']) &
        (df['评分数'] < params['score_max_reviews']) &
        (df['均价_num'] > params['score_min_price'])
    )
    result = df[mask].copy()

    if len(result) == 0:
        return result

    # Min-Max 归一化
    for col in ['月搜索量', '需供比', '近3个月增长率']:
        min_v = result[col].min()
        max_v = result[col].max()
        result[col + '_norm'] = (result[col] - min_v) / (max_v - min_v) if max_v > min_v else 0

    # 评分数反向（越低越好）
    min_r = result['评分数'].min()
    max_r = result['评分数'].max()
    result['低竞争_norm'] = 1 - (result['评分数'] - min_r) / (max_r - min_r) if max_r > min_r else 0

    # 综合评分
    result['综合评分'] = (
        result['月搜索量_norm'] * params['weight_search'] +
        result['需供比_norm'] * params['weight_dsr'] +
        result['近3个月增长率_norm'] * params['weight_growth'] +
        result['低竞争_norm'] * params['weight_competition']
    )

    result = result.sort_values('综合评分', ascending=False)
    return result


def analyze_price_segments(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """价格段分析"""
    bins = params['price_bins']
    labels = params['price_labels']

    df_copy = df.copy()
    df_copy['价格段'] = pd.cut(df_copy['均价_num'], bins=bins, labels=labels, right=False)

    analysis = df_copy.groupby('价格段', observed=True).agg({
        '关键词': 'count',
        '月搜索量': 'mean',
        '需供比': 'mean',
        '评分数': 'mean',
        '近3个月增长率': 'mean'
    }).round(2)

    analysis.columns = ['关键词数', '平均搜索量', '平均需供比', '平均评分数', '平均增长率']
    return analysis


def classify_keywords(df: pd.DataFrame) -> pd.DataFrame:
    """按关键词翻译分类产品方向"""
    def _classify(kw):
        kw_lower = str(kw).lower()
        for cat, keywords in CATEGORY_RULES.items():
            if any(k in kw_lower for k in keywords):
                return cat
        return '其他电子类'

    df_copy = df.copy()
    df_copy['产品方向'] = df_copy['关键词翻译'].apply(_classify)
    return df_copy


def analyze_categories(df: pd.DataFrame) -> pd.DataFrame:
    """品类分析"""
    df_classified = classify_keywords(df)

    results = []
    for cat in df_classified['产品方向'].value_counts().index:
        cat_df = df_classified[df_classified['产品方向'] == cat]
        results.append({
            '品类': cat,
            '关键词数': len(cat_df),
            '平均搜索量': cat_df['月搜索量'].mean(),
            '平均需供比': cat_df['需供比'].mean(),
            '平均评分数': cat_df['评分数'].mean(),
            '平均价格': cat_df['均价_num'].mean(),
            '平均增长率': cat_df['近3个月增长率'].mean(),
        })

    return pd.DataFrame(results)


def get_top_n(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """取前 N 条"""
    return df.head(n)


# ============================================================
# ABA 数据分析函数
# ============================================================

# 已知品牌列表（用于关键词分类）
KNOWN_BRANDS = [
    # 消费电子
    'apple', 'samsung', 'xiaomi', 'huawei', 'oppo', 'vivo', 'oneplus', 'google',
    'sony', 'lg', 'philips', 'panasonic', 'bose', 'sennheiser', 'jabra', 'skullcandy',
    'jbl', 'soundcore', 'harman kardon', 'marshall', 'beats',
    'logitech', 'razer', 'corsair', 'steelseries', 'hyperx',
    'hp', 'dell', 'lenovo', 'asus', 'acer', 'msi', 'microsoft',
    # 手机配件
    'iphone', 'ugreen', 'anker', 'belkin', 'mophie', 'spigen', 'otterbox', 'mous',
    # 影音设备
    'dji', 'gopro', 'insta360', 'canon', 'nikon', 'fujifilm', 'sony',
    # 智能家居
    'amazon', 'alexa', 'echo', 'kindle', 'fire tv', 'chromecast',
    'ring', 'nest', 'wyze', 'arlo', 'eufy', 'tuya',
    # 家电
    'dyson', 'shark', 'bissell', 'roomba', 'irobot', 'ecovacs', 'dreame', 'roborock',
    'kitchenaid', 'cuisinart', 'ninja', 'instant pot', 'braun', 'oral-b',
    # 时尚/运动
    'nike', 'adidas', 'puma', 'reebok', 'new balance', 'under armour',
    'zara', 'h&m', 'uniqlo', 'primark', 'shein',
    'asics', 'salomon', 'merrell', 'columbia', 'north face',
    'skechers', 'clarks', 'dr. martens', 'timberland',
    # 手表
    'casio', 'seiko', 'citizen', 'fossil', 'garmin', 'fitbit', 'amazfit',
    'ossil', 'pagani', 'orient', 'tissot', 'swatch', 'apple watch',
    # 娱乐/IP
    'disney', 'marvel', 'dc', 'pokemon', 'mario', 'nintendo', 'playstation', 'xbox',
    'lego', 'mattel', 'hasbro', 'bandai',
    # 工具
    'dremel', 'ryobi', 'dewalt', 'milwaukee', 'black+decker', 'makita', 'bosch',
    # 家居
    'ikea', 'muji',
    # 行李箱
    'samsonite', 'american tourister', 'kipling', 'lipault',
    # 音乐（避免误匹配）
    'metallica', 'megadeth', 'iron maiden',
]

# 大品牌列表（用于竞争评分和风险评估，统一维护）
MAJOR_BRANDS = [
    'apple', 'samsung', 'jbl', 'sony', 'lg', 'xiaomi', 'hp', 'dell', 'lenovo',
    'asus', 'acer', 'philips', 'bosch', 'nike', 'adidas', 'canon', 'nikon',
    'bose', 'sennheiser', 'anker', 'dji', 'gopro', 'dyson', 'microsoft',
]


def classify_keyword_type(keyword: str) -> str:
    """
    将关键词分为三类：品牌词、品类词、长尾词

    规则：
    1. 如果包含已知品牌名 → 品牌词
    2. 如果包含场景/人群修饰词 → 长尾词
    3. 否则 → 品类词
    """
    kw_lower = str(keyword).lower().strip()

    # 检查是否包含品牌名（词边界匹配）
    for brand in KNOWN_BRANDS:
        if len(brand) <= 2:
            # 短品牌名（如 hp, lg）需要严格词边界
            pattern = r'\b' + re.escape(brand.lower()) + r'\b'
            if re.search(pattern, kw_lower):
                return '品牌词'
        elif brand.lower() in kw_lower:
            return '品牌词'

    # 长尾词判断：只匹配明确的场景/人群修饰短语
    # 不使用通用介词（de, en, con, por, sin）和产品属性词（usb, bluetooth, wireless）
    longtail_patterns = [
        # 人群
        r'\bpara\s+hombre\b', r'\bpara\s+mujer\b', r'\bde\s+hombre\b', r'\bde\s+mujer\b',
        r'\bpara\s+niño', r'\bpara\s+niña\b', r'\binfantil\b', r'\bjuvenil\b',
        r'\bescolar\b', r'\bprofesional\b',
        # 场景
        r'\bpara\s+deporte', r'\bpara\s+gaming\b', r'\bpara\s+oficina\b',
        r'\bpara\s+auto\b', r'\bpara\s+carro\b', r'\bpara\s+cocina\b',
        r'\bde\s+viaje\b', r'\bpara\s+viaje\b',
        r'\bpara\s+exteriores?\b', r'\bpara\s+interiores?\b',
        # 用途修饰（明确限定词）
        r'\bportátil\b', r'\bde\s+escritorio\b',
        r'\bpara\s+montar\b', r'\bde\s+montar\b',
    ]

    for pattern in longtail_patterns:
        if re.search(pattern, kw_lower):
            return '长尾词'

    return '品类词'


def load_aba_data(filepath: str) -> pd.DataFrame:
    """加载并预处理 ABA 数据"""
    df = pd.read_excel(filepath)

    # 清洗 PPC 价格（支持多种货币格式）
    if 'PPC价格' in df.columns:
        df['PPC价格_num'] = clean_price(df['PPC价格'])
    else:
        df['PPC价格_num'] = 0.0

    # 清洗 周变化率 - 提取上周值
    if '周变化率' in df.columns:
        df['周变化率_lastweek'] = extract_regex_field(
            df['周变化率'], r'上周:\s*\+?([-\d.]+)%', 0.0
        )
    else:
        df['周变化率_lastweek'] = 0.0

    # 清洗 点击占比 - 提取合计值
    if '点击占比' in df.columns:
        df['点击占比_合计'] = extract_regex_field(
            df['点击占比'], r'合计:\s*([\d.]+)%', 0.0
        )
    else:
        df['点击占比_合计'] = 0.0

    # 提取 4周变化量和4周变化率（用于季节性风险检测）
    if '周变化量' in df.columns:
        df['4周变化量'] = extract_regex_field(
            df['周变化量'], r'4周前:\s*[+]?\s*([\d,]+)', 0
        ).astype(int)
    else:
        df['4周变化量'] = 0

    if '周变化率' in df.columns:
        df['4周变化率'] = extract_regex_field(
            df['周变化率'], r'4周前:\s*\+?([-\d.]+)%', 0.0
        )
    else:
        df['4周变化率'] = 0.0

    # 清洗 转化占比 - 提取合计值
    if '转化占比' in df.columns:
        df['转化占比_合计'] = extract_regex_field(
            df['转化占比'], r'合计:\s*([\d.]+)%', 0.0
        )
    else:
        df['转化占比_合计'] = 0.0

    # 提取 TOP1 点击占比
    if '点击占比' in df.columns:
        df['点击占比_TOP1'] = extract_regex_field(
            df['点击占比'], r'TOP1:\s*([\d.]+)%', 0.0
        )
    else:
        df['点击占比_TOP1'] = 0.0

    # 提取 TOP1 转化占比
    if '转化占比' in df.columns:
        df['转化占比_TOP1'] = extract_regex_field(
            df['转化占比'], r'TOP1:\s*([\d.]+)%', 0.0
        )
    else:
        df['转化占比_TOP1'] = 0.0

    # 关键词分类
    df['关键词类型'] = df['关键词'].apply(classify_keyword_type)

    # 确保数值列
    for col in ['周搜索量', 'SPR', '展示量', '标题密度']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df


def score_demand(row: pd.Series) -> float:
    """
    需求强度评分（0-1）

    指标：
    - 周搜索量：>5000 高分，<1000 低分
    - SPR：>=5 高分，<2 低分
    - 展示量：>50000 高分，<10000 低分
    """
    score = 0.0

    # 搜索量评分 (0-0.4)
    vol = row.get('周搜索量', 0)
    if vol >= 10000:
        vol_score = 1.0
    elif vol >= 5000:
        vol_score = 0.8
    elif vol >= 2000:
        vol_score = 0.6
    elif vol >= 1000:
        vol_score = 0.4
    else:
        vol_score = 0.2
    score += vol_score * 0.4

    # SPR 评分 (0-0.35)
    spr = row.get('SPR', 0)
    if spr >= 20:
        spr_score = 1.0
    elif spr >= 10:
        spr_score = 0.8
    elif spr >= 5:
        spr_score = 0.6
    elif spr >= 2:
        spr_score = 0.4
    else:
        spr_score = 0.2
    score += spr_score * 0.35

    # 展示量评分 (0-0.25)
    imp = row.get('展示量', 0)
    if imp >= 100000:
        imp_score = 1.0
    elif imp >= 50000:
        imp_score = 0.8
    elif imp >= 20000:
        imp_score = 0.6
    elif imp >= 10000:
        imp_score = 0.4
    else:
        imp_score = 0.2
    score += imp_score * 0.25

    return round(score, 3)


def score_competition(row: pd.Series) -> float:
    """
    竞争强度评分（0-1，越高表示竞争越低/越好）

    指标：
    - 标题密度：<10 高分（低竞争），>30 低分（高竞争）
    - 点击占比 TOP1：<10% 高分（分散），>25% 低分（垄断）
    - 品牌集中度：无大品牌 高分
    """
    score = 0.0

    # 标题密度评分 (0-0.4) - 越低越好
    td = row.get('标题密度', 0)
    if td <= 5:
        td_score = 1.0
    elif td <= 10:
        td_score = 0.8
    elif td <= 20:
        td_score = 0.6
    elif td <= 30:
        td_score = 0.4
    else:
        td_score = 0.2
    score += td_score * 0.4

    # 点击集中度评分 (0-0.35) - TOP1 越低越好
    top1_click = row.get('点击占比_TOP1', 0)
    if pd.isna(top1_click):
        top1_click = 0
    if top1_click <= 5:
        click_score = 1.0
    elif top1_click <= 10:
        click_score = 0.8
    elif top1_click <= 15:
        click_score = 0.6
    elif top1_click <= 25:
        click_score = 0.4
    else:
        click_score = 0.2
    score += click_score * 0.35

    # 品牌集中度评分 (0-0.25) - 检查是否被大品牌垄断
    brands = str(row.get('点击前三品牌', ''))
    has_major_brand = any(b.lower() in brands.lower() for b in MAJOR_BRANDS)
    brand_score = 0.3 if has_major_brand else 0.9
    score += brand_score * 0.25

    return round(score, 3)


def score_market_structure(row: pd.Series) -> float:
    """
    市场结构评分（0-1，越高表示市场结构越有利）

    指标：
    - 转化占比 TOP1：<20% 高分（分散），>40% 低分（垄断）
    - 点击占比合计：适中为好
    """
    score = 0.0

    # 转化集中度评分 (0-0.5) - TOP1 越低越好
    top1_conv = row.get('转化占比_TOP1', 0)
    if pd.isna(top1_conv):
        top1_conv = 0
    if top1_conv <= 10:
        conv_score = 1.0
    elif top1_conv <= 20:
        conv_score = 0.8
    elif top1_conv <= 30:
        conv_score = 0.6
    elif top1_conv <= 40:
        conv_score = 0.4
    else:
        conv_score = 0.2
    score += conv_score * 0.5

    # 点击合计评分 (0-0.5) - 适中为好（不要太集中也不要太分散）
    click_total = row.get('点击占比_合计', 0)
    if pd.isna(click_total):
        click_total = 0
    if 15 <= click_total <= 35:
        click_score = 1.0  # 适中
    elif 10 <= click_total <= 45:
        click_score = 0.7
    elif click_total < 10:
        click_score = 0.5  # 太分散，可能是小市场
    else:
        click_score = 0.4  # 太集中
    score += click_score * 0.5

    return round(score, 3)


def score_ad_efficiency(row: pd.Series, site_code: str = "default") -> float:
    """
    广告效率评分（0-1，越高表示广告效率越高）

    指标：
    - PPC 价格：按站点货币阈值评分
    - PPC/SPR 比值：<1 高分，>5 低分
    """
    score = 0.0

    ppc = row.get('PPC价格_num', 0)
    spr = row.get('SPR', 0)

    # PPC 价格评分 (0-0.5) - 越低越好，阈值按站点货币适配
    thresholds = SITE_PPC_THRESHOLDS.get(site_code, SITE_PPC_THRESHOLDS["default"])
    if pd.isna(ppc) or ppc <= 0:
        ppc_score = 0.5  # 无数据，给中等分
    elif ppc <= thresholds[0]:
        ppc_score = 1.0
    elif ppc <= thresholds[1]:
        ppc_score = 0.8
    elif ppc <= thresholds[2]:
        ppc_score = 0.6
    elif ppc <= thresholds[3]:
        ppc_score = 0.4
    else:
        ppc_score = 0.2
    score += ppc_score * 0.5

    # PPC/SPR 比值评分 (0-0.5) - 越低越好
    if spr > 0 and not pd.isna(ppc) and ppc > 0:
        ratio = ppc / spr
        if ratio <= 0.5:
            ratio_score = 1.0
        elif ratio <= 1:
            ratio_score = 0.8
        elif ratio <= 2:
            ratio_score = 0.6
        elif ratio <= 5:
            ratio_score = 0.4
        else:
            ratio_score = 0.2
    else:
        ratio_score = 0.5
    score += ratio_score * 0.5

    return round(score, 3)


def calculate_aba_feasibility(df: pd.DataFrame, site_code: str = "default") -> pd.DataFrame:
    """
    计算 ABA 数据的可行性评分

    综合评分 = 需求强度 × 0.30 + 竞争强度 × 0.30 + 市场结构 × 0.20 + 广告效率 × 0.20
    """
    result = df.copy()

    # 只对品类词和长尾词计算评分（品牌词跳过）
    mask = result['关键词类型'].isin(['品类词', '长尾词'])

    # 初始化评分列
    result['需求强度'] = 0.0
    result['竞争强度'] = 0.0
    result['市场结构'] = 0.0
    result['广告效率'] = 0.0
    result['可行性评分'] = 0.0

    # 计算各维度评分
    for idx, row in result[mask].iterrows():
        result.at[idx, '需求强度'] = score_demand(row)
        result.at[idx, '竞争强度'] = score_competition(row)
        result.at[idx, '市场结构'] = score_market_structure(row)
        result.at[idx, '广告效率'] = score_ad_efficiency(row, site_code)

    # 综合评分
    result.loc[mask, '可行性评分'] = (
        result.loc[mask, '需求强度'] * 0.30 +
        result.loc[mask, '竞争强度'] * 0.30 +
        result.loc[mask, '市场结构'] * 0.20 +
        result.loc[mask, '广告效率'] * 0.20
    )

    # 品牌词标记为不可行
    result.loc[result['关键词类型'] == '品牌词', '可行性评分'] = 0.0

    # 排序
    result = result.sort_values('可行性评分', ascending=False)

    return result


def get_action_suggestion(row: pd.Series) -> str:
    """根据关键词特征生成具体行动建议"""
    suggestions = []

    # 基于需求强度
    vol = row.get('周搜索量', 0)
    if vol >= 10000:
        suggestions.append("高搜索量市场，需求旺盛")
    elif vol >= 5000:
        suggestions.append("中等搜索量，需求稳定")

    # 基于竞争强度
    td = row.get('标题密度', 0)
    if td <= 10:
        suggestions.append("标题密度低，新品有机会")
    elif td >= 30:
        suggestions.append("标题密度高，需要差异化")

    # 基于品牌集中度
    top1_click = row.get('点击占比_TOP1', 0)
    if pd.isna(top1_click):
        top1_click = 0
    if top1_click <= 10:
        suggestions.append("市场分散，无明显垄断")
    elif top1_click >= 25:
        suggestions.append("头部集中，需谨慎评估")

    # 基于 PPC
    ppc = row.get('PPC价格_num', 0)
    if not pd.isna(ppc) and ppc <= 5:
        suggestions.append("PPC 成本可控")

    return "；".join(suggestions) if suggestions else "建议进一步调研"


# ============================================================
# 卖家精灵选品方法（基于ABA数据）
# ============================================================

def filter_trend_market(df: pd.DataFrame, min_rank_change: int = 10000, min_growth_rate: float = 0.10) -> pd.DataFrame:
    """
    方法1：基于市场趋势选品
    
    筛选条件：排名增长量近4周>10000，增长率>10%
    ABA数据映射：
    - 排名增长量 → 从"周变化量"提取4周前的值
    - 增长率 → 从"周变化率"提取4周前的值
    """
    # 提取4周前的排名变化量
    def extract_4week_change(x):
        if pd.isna(x):
            return 0
        match = re.search(r'4周前:\s*[+]?\s*([\d,]+)', str(x))
        return int(match.group(1).replace(',', '')) if match else 0

    # 提取4周前的排名变化率
    def extract_4week_rate(x):
        if pd.isna(x):
            return 0
        match = re.search(r'4周前:\s*\+?([-\d.]+)%', str(x))
        return float(match.group(1)) if match else 0

    result = df.copy()
    if '周变化量' in result.columns:
        result['4周变化量'] = result['周变化量'].apply(extract_4week_change)
    else:
        result['4周变化量'] = 0

    if '周变化率' in result.columns:
        result['4周变化率'] = result['周变化率'].apply(extract_4week_rate)
    else:
        result['4周变化率'] = 0

    mask = (
        (result['4周变化量'] > min_rank_change) &
        (result['4周变化率'] > min_growth_rate * 100) &
        (result['关键词类型'].isin(['品类词', '长尾词']))
    )
    return result[mask].sort_values('4周变化率', ascending=False)


def filter_potential_market(df: pd.DataFrame, rank_min: int = 20000, rank_max: int = 100000, min_weekly_growth: float = 0.20) -> pd.DataFrame:
    """
    方法2：基于市场潜力选品
    
    筛选条件：排名20000-100000，近1周增长率>20%
    ABA数据映射：
    - 排名 → 现排名
    - 周增长率 → 周变化率_lastweek
    """
    mask = (
        (df['现排名'] >= rank_min) &
        (df['现排名'] <= rank_max) &
        (df['周变化率_lastweek'] > min_weekly_growth * 100) &
        (df['关键词类型'].isin(['品类词', '长尾词']))
    )
    return df[mask].sort_values('周变化率_lastweek', ascending=False)


def filter_surge_market(df: pd.DataFrame, min_weekly_growth: float = 0.50) -> pd.DataFrame:
    """
    方法3：基于搜索飙升选品
    
    筛选条件：近1周增长率>50%
    ABA数据映射：
    - 周增长率 → 周变化率_lastweek
    """
    mask = (
        (df['周变化率_lastweek'] > min_weekly_growth * 100) &
        (df['关键词类型'].isin(['品类词', '长尾词']))
    )
    return df[mask].sort_values('周变化率_lastweek', ascending=False)


def filter_low_competition(df: pd.DataFrame, max_click_concentration: float = 50) -> pd.DataFrame:
    """
    方法4：基于市场竞争选品
    
    筛选条件：点击集中度（前3名点击占比）<50%
    ABA数据映射：
    - 点击集中度 → 点击占比_合计
    """
    mask = (
        (df['点击占比_合计'] > 0) &
        (df['点击占比_合计'] < max_click_concentration) &
        (df['关键词类型'].isin(['品类词', '长尾词']))
    )
    return df[mask].sort_values('点击占比_合计', ascending=True)


def filter_ad_cost(df: pd.DataFrame) -> pd.DataFrame:
    """
    方法5：基于营销成本选品
    
    计算货流值 = PPC价格 / (PPC价格 × 10) × 100% = 10%
    实际上，我们用 PPC/SPR 作为效率指标
    ABA数据映射：
    - PPC价格 → PPC价格_num
    - SPR → SPR
    """
    result = df.copy()
    # 计算广告效率 = SPR / PPC（越高越好）
    result['广告效率'] = result.apply(
        lambda r: r['SPR'] / r['PPC价格_num'] if r['PPC价格_num'] > 0 else 0,
        axis=1
    )
    mask = (
        (result['PPC价格_num'] > 0) &
        (result['SPR'] > 0) &
        (result['关键词类型'].isin(['品类词', '长尾词']))
    )
    return result[mask].sort_values('广告效率', ascending=False)


def filter_long_tail(df: pd.DataFrame, min_words: int = 3) -> pd.DataFrame:
    """
    方法6：基于长尾细分市场选品
    
    筛选条件：单词数≥3的长尾词
    ABA数据映射：
    - 关键词 → 关键词列，计算单词数
    """
    result = df.copy()
    result['关键词字数'] = result['关键词'].apply(lambda x: len(str(x).split()))
    mask = (
        (result['关键词字数'] >= min_words) &
        (result['关键词类型'].isin(['品类词', '长尾词']))
    )
    return result[mask].sort_values('周搜索量', ascending=False)


# ============================================================
# 场景化选品建议
# ============================================================

# 卖家类型定义
SELLER_TYPES = {
    "新手卖家": {
        "特征": "资金少、无经验、需要低风险入门",
        "关注维度": ["低PPC", "低竞争", "高SPR"],
        "推荐策略": "主打长尾细分市场，避开大词，优先选择低PPC（低于站点中位数）、标题密度<10的关键词",
        "ppc_multiplier": 1.5,  # PPC 阈值 = 站点基准 × 此系数
    },
    "工厂卖家": {
        "特征": "有供应链、可定制产品、追求差异化",
        "关注维度": ["高搜索量", "可差异化", "中等竞争"],
        "推荐策略": "选择品类词，通过产品改进（材质、功能、设计）建立竞争壁垒",
        "ppc_multiplier": None,
    },
    "品牌卖家": {
        "特征": "有品牌溢价、追求利润",
        "关注维度": ["高客单价", "品牌词周边", "低PPC"],
        "推荐策略": "选择品牌词相关的配件/周边市场，利用品牌效应获取溢价",
        "ppc_multiplier": 2.0,
    },
    "铺货卖家": {
        "特征": "追求量、快速测款、多SKU",
        "关注维度": ["低门槛", "多SKU机会", "快速周转"],
        "推荐策略": "选择薄利多销类产品，优先选择评论数少、排名中等的市场",
        "ppc_multiplier": 2.5,
    },
}


def assess_risk(row: pd.Series, site_code: str = "default") -> dict:
    """
    评估关键词的风险

    返回:
        dict: 包含风险类型和风险等级
    """
    risks = []

    # 1. 季节性风险
    four_week_change = row.get('4周变化量', 0)
    weekly_change = row.get('周变化率_lastweek', 0)
    if four_week_change > 10000 and weekly_change < 0:
        risks.append({
            "类型": "季节性风险",
            "等级": "高",
            "说明": "4周前排名大幅上升，但最近在下降，可能是季节性产品"
        })

    # 2. 品牌垄断风险
    brands = str(row.get('点击前三品牌', ''))
    has_major_brand = any(b.lower() in brands.lower() for b in MAJOR_BRANDS)
    if has_major_brand:
        risks.append({
            "类型": "品牌垄断风险",
            "等级": "中",
            "说明": f"被大品牌垄断：{brands}"
        })

    # 3. PPC风险（按站点货币阈值适配）
    ppc = row.get('PPC价格_num', 0)
    spr = row.get('SPR', 0)
    thresholds = SITE_PPC_THRESHOLDS.get(site_code, SITE_PPC_THRESHOLDS["default"])
    ppc_high = thresholds[3]  # 最高阈值作为"高风险"基准
    if ppc > 0 and spr > 0:
        ratio = ppc / spr
        if ratio > 3:
            risks.append({
                "类型": "PPC风险",
                "等级": "高",
                "说明": f"PPC/SPR比值过高({ratio:.1f})，广告难以盈利"
            })
        elif ratio > 1.5:
            risks.append({
                "类型": "PPC风险",
                "等级": "中",
                "说明": f"PPC/SPR比值偏高({ratio:.1f})，需要较高转化率才能盈利"
            })
    elif ppc > ppc_high:
        risks.append({
            "类型": "PPC风险",
            "等级": "中",
            "说明": f"PPC价格偏高({ppc:.2f})，广告成本压力大"
        })

    # 4. 市场集中度风险
    click_concentration = row.get('点击占比_合计', 0)
    if click_concentration > 40:
        risks.append({
            "类型": "市场集中风险",
            "等级": "中",
            "说明": f"点击集中度较高({click_concentration:.1f}%)，头部卖家优势明显"
        })

    # 5. 竞争强度风险
    title_density = row.get('标题密度', 0)
    if title_density > 25:
        risks.append({
            "类型": "竞争强度风险",
            "等级": "中",
            "说明": f"标题密度高({title_density})，竞争激烈"
        })

    return {
        "风险数": len(risks),
        "最高风险": max([r["等级"] for r in risks], key=lambda x: {"高": 3, "中": 2, "低": 1}.get(x, 0)) if risks else "低",
        "风险列表": risks
    }


def generate_scenario_recommendations(df: pd.DataFrame, seller_type: str = None, site_code: str = "MX") -> str:
    """
    根据卖家类型生成场景化选品建议

    Args:
        df: 已评分的DataFrame
        seller_type: 卖家类型（可选，如果不指定则生成所有类型）
        site_code: 站点代码（MX/US/JP/EU），用于 PPC 阈值和货币显示

    Returns:
        str: Markdown格式的建议
    """
    if seller_type and seller_type in SELLER_TYPES:
        types_to_analyze = {seller_type: SELLER_TYPES[seller_type]}
    else:
        types_to_analyze = SELLER_TYPES

    site_info = SITE_CONFIG.get(site_code, SITE_CONFIG.get("MX"))
    currency = site_info['currency']
    # PPC 基准阈值取站点阈值的中位数
    ppc_thresholds = SITE_PPC_THRESHOLDS.get(site_code, SITE_PPC_THRESHOLDS["default"])
    ppc_base = ppc_thresholds[1]  # 中低阈值作为基准

    report = ""

    for stype, sinfo in types_to_analyze.items():
        report += f"### {stype}\n\n"
        report += f"**特征**：{sinfo['特征']}\n\n"
        report += f"**推荐策略**：{sinfo['推荐策略']}\n\n"

        # 根据卖家类型筛选关键词（PPC 阈值按站点适配）
        ppc_mult = sinfo.get('ppc_multiplier')
        ppc_limit = ppc_base * ppc_mult if ppc_mult else None

        if stype == "新手卖家":
            mask = (
                (df['PPC价格_num'] > 0) &
                (df['PPC价格_num'] < ppc_limit) &
                (df['标题密度'] < 10) &
                (df['SPR'] >= 3) &
                (df['关键词类型'].isin(['品类词', '长尾词']))
            )
        elif stype == "工厂卖家":
            mask = (
                (df['周搜索量'] > 5000) &
                (df['标题密度'] >= 5) &
                (df['标题密度'] <= 20) &
                (df['关键词类型'].isin(['品类词']))
            )
        elif stype == "品牌卖家":
            mask = (
                (df['SPR'] >= 10) &
                (df['PPC价格_num'] > 0) &
                (df['PPC价格_num'] < ppc_limit) &
                (df['关键词类型'].isin(['品类词']))
            )
        elif stype == "铺货卖家":
            mask = (
                (df['周搜索量'] > 1000) &
                (df['周搜索量'] < 10000) &
                (df['标题密度'] < 15) &
                (df['关键词类型'].isin(['品类词', '长尾词']))
            )
        else:
            mask = pd.Series([False] * len(df), index=df.index)

        recommendations = df[mask].head(5)
        if len(recommendations) > 0:
            report += f"**推荐关键词（Top 5）**：\n\n"
            report += "| 关键词 | 中文 | 搜索量 | PPC | SPR | 标题密度 |\n"
            report += "|--------|------|--------|-----|-----|----------|\n"
            for _, row in recommendations.iterrows():
                report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} | {row['标题密度']} |\n"
            report += "\n"
        else:
            report += "*该类型暂无符合条件的推荐关键词*\n\n"

    return report


def generate_risk_summary(df: pd.DataFrame, top_n: int = 10, site_code: str = "default") -> str:
    """
    生成风险评估摘要

    Args:
        df: 已评分的DataFrame
        top_n: 分析前N个关键词
        site_code: 站点代码

    Returns:
        str: Markdown格式的风险摘要
    """
    # 获取评分最高的关键词
    top_keywords = df[df['关键词类型'].isin(['品类词', '长尾词'])].head(top_n)

    report = ""
    high_risk_count = 0
    medium_risk_count = 0

    for _, row in top_keywords.iterrows():
        risk = assess_risk(row, site_code)
        if risk['最高风险'] == '高':
            high_risk_count += 1
            report += f"- ⚠️ **{row['关键词']}** ({row['关键词翻译']})\n"
            for r in risk['风险列表']:
                report += f"  - {r['类型']}（{r['等级']}）：{r['说明']}\n"
        elif risk['最高风险'] == '中':
            medium_risk_count += 1

    if high_risk_count == 0:
        report = "*Top 10 关键词中未发现高风险项目*\n"
    else:
        report = f"**高风险关键词（{high_risk_count}个）**：\n\n" + report
        report += f"\n**中等风险关键词**：{medium_risk_count}个\n"

    return report


# ============================================================
# 深度分析函数
# ============================================================

def analyze_keyword_deep_dive(df: pd.DataFrame, keyword: str, site_code: str = "default") -> dict:
    """
    对单个关键词进行深度分析

    Args:
        df: 完整的ABA数据
        keyword: 要分析的关键词

    Returns:
        dict: 包含深度分析结果
    """
    # 找到关键词
    kw_row = df[df['关键词'] == keyword]
    if len(kw_row) == 0:
        return {"error": f"未找到关键词: {keyword}"}

    row = kw_row.iloc[0]

    # 1. 关键词概况
    overview = {
        "关键词": keyword,
        "中文翻译": row.get('关键词翻译', ''),
        "周搜索量": row.get('周搜索量', 0),
        "现排名": row.get('现排名', 0),
        "SPR": row.get('SPR', 0),
        "PPC价格": row.get('PPC价格_num', 0),
        "标题密度": row.get('标题密度', 0),
        "点击占比合计": row.get('点击占比_合计', 0),
        "转化占比合计": row.get('转化占比_合计', 0),
        "所属类目": row.get('所属类目', ''),
    }

    # 2. 竞品分析
    top3_asins = str(row.get('点击前三ASIN', '')).split('、')
    top3_brands = str(row.get('点击前三品牌', '')).split('、')
    top10_asins = str(row.get('前10ASIN', '')).split(',')

    competitors = {
        "前3 ASIN": [a.strip() for a in top3_asins if a.strip()],
        "前3 品牌": [b.strip() for b in top3_brands if b.strip()],
        "前10 ASIN数量": len([a for a in top10_asins if a.strip()]),
    }

    # 3. 定价分析
    ppc = row.get('PPC价格_num', 0)
    spr = row.get('SPR', 0)

    pricing = {
        "PPC价格": ppc,
        "建议售价下限": max(ppc * 10, 200) if ppc > 0 else 200,  # 经验值：PPC × 10，最低MX$200
        "建议售价上限": max(ppc * 20, 500) if ppc > 0 else 500,
        "广告效率": spr / ppc if ppc > 0 else 0,
        "PPC/SPR比值": ppc / spr if spr > 0 else 0,
    }

    # 4. 差异化机会
    title_density = row.get('标题密度', 0)
    click_concentration = row.get('点击占比_合计', 0)
    ppc_low_threshold = SITE_PPC_THRESHOLDS.get(site_code, SITE_PPC_THRESHOLDS["default"])[0]

    opportunities = []
    if title_density < 10:
        opportunities.append("标题密度低，SEO优化空间大")
    if click_concentration < 20:
        opportunities.append("市场分散，无明显垄断")
    if spr >= 10:
        opportunities.append("转化效率高，用户购买意愿强")
    if ppc > 0 and ppc < ppc_low_threshold:
        opportunities.append("广告成本低，适合新品推广")

    # 5. 风险评估
    risk = assess_risk(row, site_code)

    # 6. 行动清单
    actions = [
        f"1. 在 Amazon 前台搜索 `{keyword}`，分析前10名竞品",
        f"2. 点击参考 ASIN {top3_asins[0].strip() if top3_asins else 'N/A'}，记录其标题、价格、Review数",
        f"3. 在1688搜索同类产品，估算采购成本",
        f"4. 制定定价策略（建议售价区间：{pricing['建议售价下限']:.0f}-{pricing['建议售价上限']:.0f}）",
        "5. 准备差异化卖点（功能、设计、包装）",
        "6. 制定小批量试单计划",
    ]

    return {
        "概况": overview,
        "竞品": competitors,
        "定价": pricing,
        "差异化机会": opportunities,
        "风险": risk,
        "行动清单": actions,
    }


def generate_deep_dive_report(analysis: dict, currency: str = "MX$", domain: str = "amazon.com.mx") -> str:
    """
    生成深度分析报告

    Args:
        analysis: analyze_keyword_deep_dive 返回的结果
        currency: 货币符号
        domain: 域名

    Returns:
        str: Markdown格式的深度分析报告
    """
    if "error" in analysis:
        return f"# 错误\n\n{analysis['error']}\n"

    overview = analysis['概况']
    competitors = analysis['竞品']
    pricing = analysis['定价']
    opportunities = analysis['差异化机会']
    risk = analysis['风险']
    actions = analysis['行动清单']

    report = f"""# 深度分析：{overview['关键词']}

> 关键词：{overview['关键词']} ({overview['中文翻译']})
> 分析日期：{datetime.now().strftime('%Y-%m-%d')}

---

## 一、关键词概况

| 指标 | 数值 |
|------|------|
| 周搜索量 | {overview['周搜索量']:,} |
| 现排名 | {overview['现排名']:,} |
| SPR | {overview['SPR']} |
| PPC价格 | {currency}{overview['PPC价格']:.2f} |
| 标题密度 | {overview['标题密度']} |
| 点击占比合计 | {overview['点击占比合计']:.1f}% |
| 转化占比合计 | {overview['转化占比合计']:.1f}% |
| 所属类目 | {overview['所属类目']} |

---

## 二、竞品分析

**前3名竞品**：
"""
    for i, (asin, brand) in enumerate(zip(competitors['前3 ASIN'], competitors['前3 品牌']), 1):
        report += f"{i}. ASIN: {asin} | 品牌: {brand}\n"

    report += f"""
**前10 ASIN数量**：{competitors['前10 ASIN数量']}

**竞品分析建议**：
- 点击前3 ASIN，分析其标题关键词布局
- 查看竞品的Review数量和评分
- 记录竞品的价格区间
- 分析竞品的主图和A+页面

---

## 三、定价策略

| 指标 | 数值 |
|------|------|
| PPC价格 | {currency}{pricing['PPC价格']:.2f} |
| 建议售价下限 | {currency}{pricing['建议售价下限']:.0f} |
| 建议售价上限 | {currency}{pricing['建议售价上限']:.0f} |
| 广告效率 (SPR/PPC) | {pricing['广告效率']:.2f} |
| PPC/SPR比值 | {pricing['PPC/SPR比值']:.2f} |

**定价建议**：
"""
    if pricing['PPC/SPR比值'] < 1:
        report += "- ✅ 广告效率高，可以适当提高售价获取更高利润\n"
    elif pricing['PPC/SPR比值'] < 2:
        report += "- ⚠️ 广告效率中等，建议控制PPC成本\n"
    else:
        report += "- ❌ 广告效率低，需要优化转化率或寻找更低PPC的关键词\n"

    report += """
---

## 四、差异化机会

"""
    if opportunities:
        for opp in opportunities:
            report += f"- ✅ {opp}\n"
    else:
        report += "- ⚠️ 当前数据未发现明显差异化机会，建议深入分析竞品评论\n"

    report += """
---

## 五、风险评估

"""
    if risk['风险数'] == 0:
        report += "- ✅ 未发现明显风险\n"
    else:
        report += f"**风险等级**：{risk['最高风险']}\n\n"
        for r in risk['风险列表']:
            emoji = "⚠️" if r['等级'] == '高' else "⚡"
            report += f"- {emoji} **{r['类型']}**（{r['等级']}）：{r['说明']}\n"

    report += f"""
---

## 六、行动清单

"""
    for action in actions:
        report += f"{action}\n"

    report += f"""
---

## 七、前台搜索链接

- 搜索 `{overview['关键词']}`: `https://{domain}/s?k={overview['关键词'].replace(' ', '+')}`
- 查看 ASIN {competitors['前3 ASIN'][0] if competitors['前3 ASIN'] else 'N/A'}: `https://{domain}/dp/{competitors['前3 ASIN'][0] if competitors['前3 ASIN'] else 'N/A'}`

---

*深度分析完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report


# ============================================================
# 报告生成
# ============================================================

def generate_report(filepath: str, output_path: str, params: dict) -> str:
    """生成完整的选品分析报告"""
    # 加载数据
    df = load_and_preprocess(filepath)
    now = datetime.now().strftime('%Y-%m-%d')

    # 推断站点和类目
    site_info = infer_site(Path(filepath).stem)
    site = site_info['name']
    # 从数据中提取类目，或从文件名推断
    if '所属类目' in df.columns and df['所属类目'].notna().any():
        category = df['所属类目'].mode().iloc[0] if len(df['所属类目'].mode()) > 0 else "未知"
    else:
        # 从文件名提取类目（如 KeywordResearch-MX-Electronics）
        stem_parts = Path(filepath).stem.split('-')
        category = stem_parts[-1] if len(stem_parts) > 2 else "未知"

    # 执行分析
    trending = filter_trending(df, params)
    opportunity = filter_opportunity(df, params)
    profitable = filter_profitable(df, params)
    scored = calculate_composite_score(df, params)
    price_segments = analyze_price_segments(df, params)
    category_analysis = analyze_categories(df)

    n = params['top_n']

    # 构建报告
    report = f"""# {now} {site}站 {category} 选品分析

> 数据来源：卖家精灵关键词研究
> 分析日期：{now}
> 站点：{site}站 | 数据文件：{Path(filepath).name}

---

## 数据概览

| 指标 | 数值 |
|------|------|
| 总关键词数 | {len(df):,} 条 |
| 月搜索量范围 | {df['月搜索量'].min():,.0f} ~ {df['月搜索量'].max():,.0f} |
| 月搜索量中位数 | {df['月搜索量'].median():,.0f} |
| 价格范围 | {df['均价_num'].min():,.0f} ~ {df['均价_num'].max():,.0f} |
| 评分数范围 | {df['评分数'].min():,.0f} ~ {df['评分数'].max():,.0f} |

---

## 一、趋势市场（近3个月增长 > {params['trend_min_growth']:.0%}）

**{len(trending)} 个关键词**在持续增长

### Top {n} 趋势关键词

| 产品方向 | 月搜索量 | 3月增长率 | 需供比 | 均价 | 评论数 | 商品数 |
|---------|---------|----------|-------|------|-------|-------|
"""
    for _, row in get_top_n(trending, n).iterrows():
        report += f"| {row['关键词翻译']} | {row['月搜索量']:,.0f} | **+{row['近3个月增长率']:.0%}** | {row['需供比']:.1f} | {row['均价_num']:,.0f} | {row['评分数']:,.0f} | {row['商品数']:,.0f} |\n"

    report += f"""
---

## 二、机会市场（需供比 > {params['opp_min_dsr']} + 评论 < {params['opp_max_reviews']}）

**{len(opportunity)} 个关键词**供不应求

### Top {n} 蓝海机会

| 产品方向 | 月搜索量 | 需供比 | 评论数 | 均价 | 商品数 |
|---------|---------|-------|-------|------|-------|
"""
    for _, row in get_top_n(opportunity, n).iterrows():
        report += f"| {row['关键词翻译']} | {row['月搜索量']:,.0f} | **{row['需供比']:.0f}** | {row['评分数']:,.0f} | {row['均价_num']:,.0f} | {row['商品数']:,.0f} |\n"

    report += f"""
---

## 三、利润空间（搜索量 > {params['profit_min_search']:,} + 价格 {params['profit_price_min']}-{params['profit_price_max']}）

**{len(profitable)} 个关键词**有利润空间

### Top {n} 利润候选

| 产品方向 | 月搜索量 | 均价 | 评论数 | 需供比 | 3月增长率 |
|---------|---------|------|-------|-------|----------|
"""
    for _, row in get_top_n(profitable, n).iterrows():
        growth = row['近3个月增长率']
        growth_str = f"+{growth:.0%}" if growth > 0 else f"{growth:.0%}"
        report += f"| {row['关键词翻译']} | {row['月搜索量']:,.0f} | {row['均价_num']:,.0f} | {row['评分数']:,.0f} | {row['需供比']:.1f} | {growth_str} |\n"

    report += f"""
---

## 四、综合评分 Top {n}

综合考虑：搜索量({params['weight_search']:.0%}) + 需供比({params['weight_dsr']:.0%}) + 增长率({params['weight_growth']:.0%}) + 低竞争({params['weight_competition']:.0%})

| 排名 | 产品方向 | 综合评分 | 月搜索量 | 需供比 | 评论数 | 均价 |
|-----|---------|---------|---------|-------|-------|------|
"""
    for i, (_, row) in enumerate(get_top_n(scored, n).iterrows(), 1):
        report += f"| {i} | {row['关键词翻译']} | **{row['综合评分']:.3f}** | {row['月搜索量']:,.0f} | {row['需供比']:.1f} | {row['评分数']:,.0f} | {row['均价_num']:,.0f} |\n"

    report += f"""
---

## 五、价格段机会分析

| 价格段 | 关键词数 | 平均需供比 | 平均评论数 | 平均增长率 |
|--------|---------|-----------|-----------|-----------|
"""
    for idx, row in price_segments.iterrows():
        report += f"| {idx} | {row['关键词数']:.0f} | {row['平均需供比']:.2f} | {row['平均评分数']:,.0f} | {row['平均增长率']:.2%} |\n"

    report += f"""
---

## 六、品类趋势

| 品类 | 关键词数 | 平均需供比 | 平均增长率 | 平均价格 |
|-----|---------|-----------|-----------|---------|
"""
    for _, row in category_analysis.iterrows():
        report += f"| {row['品类']} | {row['关键词数']:.0f} | {row['平均需供比']:.2f} | {row['平均增长率']:.2%} | {row['平均价格']:,.0f} |\n"

    report += """
---

## 七、下一步行动建议

### 优先级 1：立即调研
"""
    # 从综合评分 Top 3 提取行动建议
    for _, row in get_top_n(scored, 3).iterrows():
        report += f"- **{row['关键词翻译']}** — 需供比 {row['需供比']:.0f}，评论仅 {row['评分数']:.0f}\n"

    report += """
### 优先级 2：重点跟踪
"""
    # 从品类分析中提取正增长品类
    growing_cats = category_analysis[category_analysis['平均增长率'] > 0]
    for _, row in growing_cats.head(3).iterrows():
        report += f"- **{row['品类']}** — 增长 {row['平均增长率']:.1%}，需供比 {row['平均需供比']:.1f}\n"

    report += """
### 待办事项
- [ ] 针对 Top 3 候选产品做深度竞品分析
- [ ] 测算各候选产品的利润模型
- [ ] 在 1688/阿里巴巴上调研供应链
- [ ] 制定小批量试单计划

---

## 附录：分析方法说明

### 筛选条件汇总
"""
    report += f"""
| 分析步骤 | 条件 |
|---------|------|
| 趋势筛选 | 月搜索量 > {params['trend_min_search']:,} + 近3月增长率 > {params['trend_min_growth']:.0%} |
| 机会筛选 | 需供比 > {params['opp_min_dsr']} + 评论 < {params['opp_max_reviews']} + 搜索量 > {params['opp_min_search']:,} |
| 利润筛选 | 搜索量 > {params['profit_min_search']:,} + 价格 {params['profit_price_min']}-{params['profit_price_max']} + 评论 < {params['profit_max_reviews']} |
| 综合评分 | 搜索量({params['weight_search']:.0%}) + 需供比({params['weight_dsr']:.0%}) + 增长率({params['weight_growth']:.0%}) + 低竞争({params['weight_competition']:.0%}) |
"""

    report += f"""
### 关键指标说明
- **需供比**：月搜索量 / 商品数，越高表示供不应求
- **SPR**：搜索购买比，反映搜索到购买的转化效率
- **综合评分**：多维加权排序，用于跨品类比较

---

*报告生成时间：{now}*
*分析工具：amazon-product-selection skill*
"""

    return write_report_file(report, output_path)


def generate_aba_report(filepath: str, output_path: str, params: dict) -> str:
    """生成 ABA 数据选品分析报告"""
    # 加载数据
    df = load_aba_data(filepath)
    now = datetime.now().strftime('%Y-%m-%d')

    # 推断站点
    site_info = infer_site(Path(filepath).stem)
    site = site_info['name']
    currency = site_info['currency']
    domain = site_info['domain']

    # 执行分析
    scored = calculate_aba_feasibility(df, site_info['code'])

    # 场景化建议和风险评估
    scenario_recommendations = generate_scenario_recommendations(scored, site_code=site_info['code'])
    risk_summary = generate_risk_summary(scored, site_code=site_info['code'])

    # 分类统计
    type_stats = df['关键词类型'].value_counts()

    # 品类分析（按 Amazon 类目）
    if '所属类目' in df.columns:
        cat_stats = df.groupby('所属类目').agg({
            '关键词': 'count',
            '周搜索量': ['mean', 'max'],
            'SPR': 'mean',
            'PPC价格_num': 'mean',
            '展示量': 'mean'
        }).round(2)
        cat_stats.columns = ['关键词数', '平均搜索量', '最大搜索量', '平均SPR', '平均PPC', '平均展示量']
        cat_stats = cat_stats.sort_values('关键词数', ascending=False)
    else:
        cat_stats = pd.DataFrame()

    n = params.get('top_n', 20)

    # 构建报告
    report = f"""# {now} {site}站 ABA关键词趋势选品分析

> 数据来源：Amazon Brand Analytics (ABA) 关键词趋势
> 分析日期：{now}
> 站点：{site}站 | 数据文件：{Path(filepath).name}
> 分析框架：关键词分类 + 4维度可行性评估

---

## 一、数据概览

| 指标 | 数值 |
|------|------|
| 总关键词数 | {len(df):,} 条 |
| 周搜索量范围 | {df['周搜索量'].min():,.0f} ~ {df['周搜索量'].max():,.0f} |
| 周搜索量中位数 | {df['周搜索量'].median():,.0f} |
| PPC价格范围 | {currency}{df['PPC价格_num'].min():.2f} ~ {currency}{df['PPC价格_num'].max():.2f} |
| SPR范围 | {df['SPR'].min()} ~ {df['SPR'].max()} |

---

## 二、关键词分类统计

| 类型 | 数量 | 占比 | 说明 |
|------|------|------|------|
| 品牌词 | {type_stats.get('品牌词', 0)} | {type_stats.get('品牌词', 0)/len(df)*100:.1f}% | 包含品牌名，除非做配件否则避开 |
| 品类词 | {type_stats.get('品类词', 0)} | {type_stats.get('品类词', 0)/len(df)*100:.1f}% | 通用产品词，**主攻方向** |
| 长尾词 | {type_stats.get('长尾词', 0)} | {type_stats.get('长尾词', 0)/len(df)*100:.1f}% | 场景/人群修饰词，补充机会 |

---

## 三、可行性评分 Top {n}（品类词 + 长尾词）

**评分公式**：需求强度(30%) + 竞争强度(30%) + 市场结构(20%) + 广告效率(20%)

| 排名 | 搜索关键词 | 中文 | 可行性评分 | 需求强度 | 竞争强度 | 市场结构 | 广告效率 | 周搜索量 | PPC | SPR | 参考ASIN | 行动建议 |
|-----|-----------|------|-----------|---------|---------|---------|---------|---------|-----|-----|---------|---------|
"""

    # 取品类词和长尾词中评分最高的
    feasible = scored[scored['关键词类型'].isin(['品类词', '长尾词'])].head(n)

    for i, (_, row) in enumerate(feasible.iterrows(), 1):
        asins = str(row['点击前三ASIN']).split(',')[0].strip() if pd.notna(row.get('点击前三ASIN')) else '-'
        suggestion = get_action_suggestion(row)
        ppc = row['PPC价格_num'] if not pd.isna(row['PPC价格_num']) else 0
        report += f"| {i} | {row['关键词']} | {row['关键词翻译']} | **{row['可行性评分']:.3f}** | {row['需求强度']:.2f} | {row['竞争强度']:.2f} | {row['市场结构']:.2f} | {row['广告效率']:.2f} | {row['周搜索量']:,.0f} | {currency}{ppc:.2f} | {row['SPR']} | {asins} | {suggestion} |\n"

    report += f"""
---

## 四、场景化选品建议

{scenario_recommendations}

---

## 五、风险评估

{risk_summary}

---

## 六、品类词详细分析（按 Amazon 类目）

"""
    if not cat_stats.empty:
        report += """| 类目 | 关键词数 | 平均搜索量 | 最大搜索量 | 平均SPR | 平均PPC | 平均展示量 |
|-----|---------|-----------|-----------|---------|---------|-----------|
"""
        for _, row in cat_stats.head(15).iterrows():
            report += f"| {row.name} | {row['关键词数']:.0f} | {row['平均搜索量']:.0f} | {row['最大搜索量']:.0f} | {row['平均SPR']:.2f} | {currency}{row['平均PPC']:.2f} | {row['平均展示量']:.0f} |\n"
    else:
        report += "*无类目数据*\n"

    # 七、多维选品筛选（6种方法）
    trend_market = filter_trend_market(df)
    potential_market = filter_potential_market(df)
    surge_market = filter_surge_market(df)
    low_competition = filter_low_competition(df)
    ad_cost = filter_ad_cost(df)
    long_tail = filter_long_tail(df)

    report += f"""
---

## 七、多维选品筛选

### 7.1 趋势市场（排名4周增长 > 10,000 且 增长率 > 10%）

**{len(trend_market)} 个关键词**呈上升趋势

| 关键词 | 中文 | 周搜索量 | 4周变化率 | PPC | SPR |
|--------|------|---------|----------|-----|-----|
"""
    for _, row in trend_market.head(n).iterrows():
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | +{row['4周变化率']:.1f}% | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} |\n"

    report += f"""
### 7.2 潜力市场（排名 20,000-100,000 且 近1周增长 > 20%）

**{len(potential_market)} 个关键词**有爆发潜力

| 关键词 | 中文 | 现排名 | 周变化率 | PPC | SPR |
|--------|------|--------|---------|-----|-----|
"""
    for _, row in potential_market.head(n).iterrows():
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['现排名']:,.0f} | +{row['周变化率_lastweek']:.1f}% | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} |\n"

    report += f"""
### 7.3 飙升市场（近1周增长 > 50%）

**{len(surge_market)} 个关键词**搜索量飙升

| 关键词 | 中文 | 周搜索量 | 周变化率 | PPC | SPR |
|--------|------|---------|---------|-----|-----|
"""
    for _, row in surge_market.head(n).iterrows():
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | +{row['周变化率_lastweek']:.1f}% | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} |\n"

    report += f"""
### 7.4 低竞争市场（点击集中度 < 50%）

**{len(low_competition)} 个关键词**竞争分散

| 关键词 | 中文 | 周搜索量 | 点击集中度 | 标题密度 | SPR |
|--------|------|---------|-----------|---------|-----|
"""
    for _, row in low_competition.head(n).iterrows():
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | {row['点击占比_合计']:.1f}% | {row['标题密度']} | {row['SPR']} |\n"

    report += f"""
### 7.5 低广告成本（按 SPR/PPC 效率排序）

**{len(ad_cost)} 个关键词**广告效率高

| 关键词 | 中文 | 周搜索量 | PPC | SPR | 广告效率 |
|--------|------|---------|-----|-----|---------|
"""
    for _, row in ad_cost.head(n).iterrows():
        efficiency = row['SPR'] / row['PPC价格_num'] if row['PPC价格_num'] > 0 else 0
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} | {efficiency:.2f} |\n"

    report += f"""
### 7.6 长尾细分市场（关键词 ≥ 3 词）

**{len(long_tail)} 个关键词**为长尾细分词

| 关键词 | 中文 | 周搜索量 | PPC | SPR | 标题密度 |
|--------|------|---------|-----|-----|---------|
"""
    for _, row in long_tail.head(n).iterrows():
        report += f"| {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} | {row['标题密度']} |\n"

    report += f"""
---

## 八、行动建议

### 优先级 1：立即深入调研
"""
    top3 = feasible.head(3)
    for _, row in top3.iterrows():
        asins = str(row['点击前三ASIN']).split(',')[:3]
        asins_str = ', '.join(a.strip() for a in asins)
        report += f"""- **{row['关键词']}** ({row['关键词翻译']})
  - 可行性评分: {row['可行性评分']:.3f} | 搜索量: {row['周搜索量']:,.0f} | SPR: {row['SPR']}
  - 参考 ASIN: {asins_str}
  - 行动: 在 Amazon.{domain.split('.')[-1]} 搜索 `{row['关键词']}`，分析前 10 名竞品的标题、图片、Review、定价

"""

    report += """### 优先级 2：持续跟踪
"""
    top10 = feasible.head(10).tail(7)
    for _, row in top10.iterrows():
        report += f"- **{row['关键词']}** ({row['关键词翻译']}) — 评分 {row['可行性评分']:.3f}，搜索量 {row['周搜索量']:,.0f}\n"

    report += """
### 前台搜索链接
"""
    for _, row in top3.iterrows():
        kw_encoded = row['关键词'].replace(' ', '+')
        report += f"- 搜索 {row['关键词']}: `https://{domain}/s?k={kw_encoded}`\n"

    report += f"""
### 待办事项
- [ ] 用搜索关键词在 Amazon.{domain.split('.')[-1]} 前台搜索，查看竞品 Listing
- [ ] 点击参考 ASIN，分析竞品的标题、图片、Review、定价策略
- [ ] 记录每个关键词的前 10 名竞品信息
- [ ] 评估是否有差异化空间

---

## 附录：分析方法说明

### 关键词分类规则
| 类型 | 判断规则 | 选品策略 |
|------|---------|---------|
| 品牌词 | 包含已知品牌名（jbl, ugreen, iphone等） | 跳过，不做主攻方向 |
| 品类词 | 通用产品词，不含品牌名 | **主攻方向** |
| 长尾词 | 包含场景/人群修饰词（para deporte, para niños） | 补充机会 |

### 可行性评分维度
| 维度 | 权重 | 评估指标 |
|------|------|---------|
| 需求强度 | 30% | 周搜索量、SPR、展示量 |
| 竞争强度 | 30% | 标题密度、点击集中度、品牌集中度 |
| 市场结构 | 20% | 转化集中度、点击合计 |
| 广告效率 | 20% | PPC价格、PPC/SPR比值 |

### 关键指标说明
- **SPR**：Search Purchase Ratio，每100次搜索产生购买的数量
- **标题密度**：关键词在竞品标题中的出现频率（0-50）
- **点击占比 TOP1**：排名第一的 ASIN 获得的点击占比
- **转化占比 TOP1**：排名第一的 ASIN 获得的转化占比

---

*报告生成时间：{now}*
*分析工具：amazon-product-selection skill*
"""

    return write_report_file(report, output_path)


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='亚马逊选品分析工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # report 子命令（卖家精灵标准数据）
    report_parser = subparsers.add_parser('report', help='生成选品分析报告（卖家精灵标准数据）')
    report_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    report_parser.add_argument('--output', '-o', help='输出报告路径（默认自动生成）')

    # 可选参数
    report_parser.add_argument('--min-search', type=int, help='最低搜索量')
    report_parser.add_argument('--min-growth', type=float, help='最低增长率')
    report_parser.add_argument('--min-dsr', type=float, help='最低需供比')
    report_parser.add_argument('--max-reviews', type=int, help='最高评论数')
    report_parser.add_argument('--price-min', type=float, help='最低价格')
    report_parser.add_argument('--price-max', type=float, help='最高价格')
    report_parser.add_argument('--weight-search', type=float, help='搜索量权重')
    report_parser.add_argument('--weight-dsr', type=float, help='需供比权重')
    report_parser.add_argument('--weight-growth', type=float, help='增长率权重')
    report_parser.add_argument('--weight-competition', type=float, help='低竞争权重')
    report_parser.add_argument('--top-n', type=int, help='每个维度展示前 N 个')
    report_parser.add_argument('--output-dir', help='报告输出目录')

    # aba-report 子命令（ABA 关键词趋势数据）
    aba_parser = subparsers.add_parser('aba-report', help='生成选品分析报告（ABA 关键词趋势数据）')
    aba_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    aba_parser.add_argument('--output', '-o', help='输出报告路径（默认自动生成）')
    aba_parser.add_argument('--top-n', type=int, default=20, help='展示前 N 个关键词')
    aba_parser.add_argument('--output-dir', help='报告输出目录')

    # deep-dive 子命令（深度分析单个关键词）
    dive_parser = subparsers.add_parser('deep-dive', help='深度分析单个关键词')
    dive_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    dive_parser.add_argument('--keyword', '-k', required=True, help='要分析的关键词')
    dive_parser.add_argument('--output', '-o', help='输出报告路径（默认自动生成）')
    dive_parser.add_argument('--output-dir', help='报告输出目录')

    # preprocess 子命令
    preprocess_parser = subparsers.add_parser('preprocess', help='预处理数据并保存')
    preprocess_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    preprocess_parser.add_argument('--output', '-o', help='输出 Excel 路径（默认在输入文件名后加 _cleaned）')
    preprocess_parser.add_argument('--type', choices=['standard', 'aba'], default='standard', help='数据类型：standard=卖家精灵标准数据，aba=ABA关键词趋势数据')

    # 6种选品筛选子命令 (ABA数据)
    for method_name, method_help in [
        ('trend', '趋势市场筛选 (排名4周增长+增长率)'),
        ('potential', '潜力市场筛选 (排名区间+周增长率)'),
        ('surge', '飙升市场筛选 (近1周增长率>50%%)'),
        ('low-competition', '低竞争市场筛选 (点击集中度<50%%)'),
        ('ad-cost', '低广告成本筛选 (按SPR/PPC效率排序)'),
        ('long-tail', '长尾细分市场筛选 (关键词>=3词)'),
    ]:
        m_parser = subparsers.add_parser(method_name, help=method_help)
        m_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
        m_parser.add_argument('--output', '-o', help='输出报告路径 (默认自动生成)')
        m_parser.add_argument('--top-n', type=int, default=20, help='展示前 N 个关键词')
        m_parser.add_argument('--output-dir', help='报告输出目录')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 合并默认参数和用户参数
    params = DEFAULT_PARAMS.copy()
    if hasattr(args, 'min_search') and args.min_search is not None:
        params['trend_min_search'] = args.min_search
    if hasattr(args, 'min_growth') and args.min_growth is not None:
        params['trend_min_growth'] = args.min_growth
    if hasattr(args, 'min_dsr') and args.min_dsr is not None:
        params['opp_min_dsr'] = args.min_dsr
    if hasattr(args, 'max_reviews') and args.max_reviews is not None:
        params['opp_max_reviews'] = args.max_reviews
    if hasattr(args, 'price_min') and args.price_min is not None:
        params['opp_min_price'] = args.price_min
        params['profit_price_min'] = args.price_min
        params['score_min_price'] = args.price_min
    if hasattr(args, 'price_max') and args.price_max is not None:
        params['profit_price_max'] = args.price_max
    if hasattr(args, 'weight_search') and args.weight_search is not None:
        params['weight_search'] = args.weight_search
    if hasattr(args, 'weight_dsr') and args.weight_dsr is not None:
        params['weight_dsr'] = args.weight_dsr
    if hasattr(args, 'weight_growth') and args.weight_growth is not None:
        params['weight_growth'] = args.weight_growth
    if hasattr(args, 'weight_competition') and args.weight_competition is not None:
        params['weight_competition'] = args.weight_competition
    if hasattr(args, 'top_n') and args.top_n is not None:
        params['top_n'] = args.top_n

    if args.command == 'preprocess':
        if args.type == 'aba':
            df = load_aba_data(args.input)
        else:
            df = load_and_preprocess(args.input)

        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.input)
            output_path = str(input_path.parent / f"{input_path.stem}_cleaned.xlsx")

        df.to_excel(output_path, index=False)
        print(f"预处理完成: {len(df)} 行数据")
        print(f"列: {list(df.columns)}")
        print(f"已保存到: {output_path}")

    elif args.command == 'report':
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            output_dir = args.output_dir or params['output_dir']
            now = datetime.now().strftime('%Y-%m-%d')
            filename = Path(args.input).stem
            output_path = str(Path(output_dir) / f"{now} {filename} 选品分析.md")

        print(f"开始分析: {args.input}")
        print(f"输出路径: {output_path}")

        result_path = generate_report(args.input, output_path, params)
        print(f"报告已生成: {result_path}")

    elif args.command == 'aba-report':
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            output_dir = args.output_dir or params['output_dir']
            now = datetime.now().strftime('%Y-%m-%d')
            filename = Path(args.input).stem
            output_path = str(Path(output_dir) / f"{now} {filename} ABA选品分析.md")

        print(f"开始 ABA 分析: {args.input}")
        print(f"输出路径: {output_path}")

        result_path = generate_aba_report(args.input, output_path, params)
        print(f"报告已生成: {result_path}")

    elif args.command == 'deep-dive':
        # 加载数据
        df = load_aba_data(args.input)

        # 推断站点
        site_info = infer_site(Path(args.input).stem)
        currency = site_info['currency']
        domain = site_info['domain']

        # 执行深度分析
        analysis = analyze_keyword_deep_dive(df, args.keyword, site_info['code'])

        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            output_dir = args.output_dir or params['output_dir']
            now = datetime.now().strftime('%Y-%m-%d')
            safe_keyword = args.keyword.replace(' ', '_')[:30]
            output_path = str(Path(output_dir) / f"{now} 深度分析 {safe_keyword}.md")

        print(f"开始深度分析: {args.keyword}")
        print(f"输出路径: {output_path}")

        report = generate_deep_dive_report(analysis, currency, domain)
        write_report_file(report, output_path)
        print(f"深度分析报告已生成: {output_path}")

    # 6种选品筛选方法的独立命令
    elif args.command in ('trend', 'potential', 'surge', 'low-competition', 'ad-cost', 'long-tail'):
        df = load_aba_data(args.input)
        site_info = infer_site(Path(args.input).stem)
        currency = site_info['currency']
        now = datetime.now().strftime('%Y-%m-%d')
        filename = Path(args.input).stem
        n = args.top_n

        # 方法映射
        method_map = {
            'trend': ('趋势市场', filter_trend_market),
            'potential': ('潜力市场', filter_potential_market),
            'surge': ('飙升市场', filter_surge_market),
            'low-competition': ('低竞争市场', filter_low_competition),
            'ad-cost': ('低广告成本', filter_ad_cost),
            'long-tail': ('长尾细分', filter_long_tail),
        }

        label, func = method_map[args.command]
        result = func(df)

        if args.output:
            output_path = args.output
        else:
            output_dir = args.output_dir or params['output_dir']
            output_path = str(Path(output_dir) / f"{now} {filename} {label}筛选.md")

        # 生成简报
        report = f"# {now} {site_info['name']}站 {label}选品筛选\n\n"
        report += f"> 数据文件：{Path(args.input).name}\n"
        report += f"> 筛选结果：{len(result)} 个关键词\n\n---\n\n"
        report += f"| 排名 | 关键词 | 中文 | 周搜索量 | PPC | SPR | 标题密度 |\n"
        report += "|-----|--------|------|---------|-----|-----|----------|\n"
        for i, (_, row) in enumerate(result.head(n).iterrows(), 1):
            report += f"| {i} | {row['关键词']} | {row['关键词翻译']} | {row['周搜索量']:,.0f} | {currency}{row['PPC价格_num']:.2f} | {row['SPR']} | {row['标题密度']} |\n"

        write_report_file(report, output_path)
        print(f"{label}筛选完成: {len(result)} 个关键词")
        print(f"报告已生成: {output_path}")


if __name__ == '__main__':
    main()
