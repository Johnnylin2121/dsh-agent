#!/usr/bin/env python3
"""
亚马逊广告分析脚本
基于广告报告数据，执行词根分析、否定词生成、关键词覆盖分析。

用法:
    # 词根分析
    python analysis.py roots --input search_terms.xlsx --output roots.xlsx

    # 否定词清单
    python analysis.py negations --input search_terms.xlsx --output negations.xlsx

    # 关键词覆盖分析
    python analysis.py coverage --input search_terms.xlsx --listing listing.json --output coverage.xlsx

    # 数据清洗
    python analysis.py clean --input raw.xlsx --output cleaned.xlsx

依赖:
    pip install pandas openpyxl
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import json
from collections import defaultdict


# ============================================================
# 停用词列表（英文 + 常见西班牙语）
# ============================================================

STOP_WORDS = {
    # 英文停用词
    'a', 'an', 'the', 'for', 'with', 'and', 'or', 'to', 'in', 'on', 'at',
    'by', 'of', 'is', 'it', 'its', 'my', 'your', 'his', 'her', 'our',
    'their', 'this', 'that', 'am', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'need', 'dare',
    'ought', 'used', 'from', 'as', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'between', 'out', 'off', 'over', 'under',
    'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
    'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'because', 'but', 'if', 'while',
    'about', 'against', 'up', 'down', 'you', 'he', 'she', 'we', 'they',
    'me', 'him', 'her', 'us', 'them', 'what', 'which', 'who', 'whom',
    'these', 'those', 'i',
    # 西班牙语停用词
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'es', 'se', 'del', 'los',
    'las', 'un', 'una', 'por', 'con', 'no', 'para', 'al', 'lo', 'como',
    'su', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'fue', 'este', 'ha',
    'si', 'porque', 'esta', 'son', 'entre', 'cuando', 'muy', 'sin',
    'sobre', 'ser', 'también', 'me', 'hasta', 'hay', 'donde', 'quien',
    'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni',
    'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto',
    'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro', 'otras',
    'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada',
    'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas',
    'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu', 'tus',
    'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'mío', 'mía',
    'míos', 'mías', 'tuyo', 'tuya', 'tuyos', 'tuyas', 'suyo', 'suya',
    'suyos', 'suyas', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
    'vuestro', 'vuestra', 'vuestros', 'vuestras', 'esos', 'esas',
    'estoy', 'estás', 'está', 'estamos', 'estáis', 'están', 'esté',
    'estés', 'estemos', 'estéis', 'estén', 'estaré', 'estarás', 'estará',
    'estaremos', 'estaréis', 'estarán', 'estaría', 'estarías', 'estaríamos',
    'estaríais', 'estarían', 'estaba', 'estabas', 'estábamos', 'estabais',
    'estaban', 'estuve', 'estuviste', 'estuvo', 'estuvimos', 'estuvisteis',
    'estuvieron',
}

# ============================================================
# 品类配置（可扩展）
# ============================================================

# 默认组合词根（通用品类）
DEFAULT_COMPOUND_ROOTS = [
    'usb hub', 'usb 3.0 hub', 'usb 2.0 hub', 'powered usb hub',
    'usb hub powered', 'usb splitter', 'usb port', 'usb extender',
    'usb charger', 'usb adapter', 'usb cable', 'usb drive',
    'usb c hub', 'usb c adapter', 'usb c cable',
    '4 port', '5 port', '7 port', '10 port', '4-port', '5-port',
    'aluminum', 'portable', 'individual switch',
]

# 品类配置
CATEGORY_CONFIGS = {
    'usb_hub': {
        'compound_roots': DEFAULT_COMPOUND_ROOTS,
        'category_name': 'USB Hub',
    },
    'electronics': {
        'compound_roots': [
            'wireless charger', 'fast charger', 'wall charger', 'car charger',
            'phone case', 'screen protector', 'earbuds', 'headphones',
            'bluetooth speaker', 'power bank', 'portable charger',
            'lightning cable', 'usb c cable', 'hdmi cable',
            'phone holder', 'car mount', 'wireless earbuds',
        ],
        'category_name': 'Electronics',
    },
    'home': {
        'compound_roots': [
            'air purifier', 'humidifier', 'dehumidifier', 'space heater',
            'electric kettle', 'coffee maker', 'blender', 'food processor',
            'vacuum cleaner', 'robot vacuum', 'steam mop',
            'bed sheets', 'pillow case', 'comforter', 'mattress pad',
            'curtains', 'blackout curtains', 'shower curtain',
        ],
        'category_name': 'Home & Kitchen',
    },
    'custom': {
        'compound_roots': [],  # 用户自定义
        'category_name': 'Custom',
    },
}


# ============================================================
# 数据清洗
# ============================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗广告数据"""
    df_clean = df.copy()

    # 替换特殊值
    df_clean = df_clean.replace('--', 0)
    df_clean = df_clean.replace('0%', 0)
    df_clean = df_clean.replace('有花费无销售额', 0)
    df_clean = df_clean.replace('有花费无订单', 0)
    df_clean = df_clean.replace('', np.nan)
    df_clean = df_clean.replace('nan', np.nan)

    # 百分比转小数
    for col in df_clean.columns:
        if df_clean[col].dtype == object:
            # 检查是否是百分比格式
            sample = df_clean[col].dropna().head(20)
            if sample.apply(lambda x: isinstance(x, str) and '%' in str(x)).any():
                df_clean[col] = df_clean[col].apply(
                    lambda x: float(str(x).replace('%', '')) / 100
                    if isinstance(x, str) and '%' in str(x) else x
                )

    # 数值列转换
    numeric_cols = ['展示量', '点击量', '点击', '花费', '7天总销售额', '7天总订单数(#)',
                    '销售额', '订单量', '销量', '广告花费', '广告销售']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

    return df_clean


def generate_quality_report(df: pd.DataFrame) -> dict:
    """生成数据质量报告"""
    report = {
        'total_rows': len(df),
        'columns': list(df.columns),
        'missing_values': {},
        'anomalies': {},
    }

    # 缺失值统计
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0:
            report['missing_values'][col] = {
                'count': int(missing),
                'percentage': round(missing / len(df) * 100, 2)
            }

    # 异常值检测
    if 'ACoS' in df.columns or 'ACOS' in df.columns:
        acos_col = 'ACoS' if 'ACoS' in df.columns else 'ACOS'
        acos_values = pd.to_numeric(df[acos_col], errors='coerce').dropna()
        high_acos = acos_values[acos_values > 1.0]  # >100%
        if len(high_acos) > 0:
            report['anomalies']['high_acos'] = {
                'count': len(high_acos),
                'threshold': '>100%',
                'examples': high_acos.head(5).tolist()
            }

    if 'CPC' in df.columns:
        cpc_values = pd.to_numeric(df['CPC'], errors='coerce').dropna()
        high_cpc = cpc_values[cpc_values > 5.0]
        if len(high_cpc) > 0:
            report['anomalies']['high_cpc'] = {
                'count': len(high_cpc),
                'threshold': '>$5',
                'examples': high_cpc.head(5).tolist()
            }

    return report


# ============================================================
# 词根分析
# ============================================================

def extract_keyword_roots(search_term: str, compound_roots: list = None) -> set:
    """从搜索词中提取词根（可重叠）"""
    if compound_roots is None:
        compound_roots = DEFAULT_COMPOUND_ROOTS

    term = str(search_term).lower().strip()
    roots = set()

    # 1. 提取ASIN（10位字母数字）
    asins = re.findall(r'[a-z0-9]{10}', term)
    roots.update(asins)

    # 2. 匹配组合词根
    for compound in compound_roots:
        if compound.lower() in term:
            roots.add(compound.lower())

    # 3. 提取单个词根
    words = re.findall(r'[a-z0-9]+', term)
    for word in words:
        if word not in STOP_WORDS and len(word) > 1:
            roots.add(word)

    # 4. 生成2-gram组合词根
    for i in range(len(words) - 1):
        if words[i] not in STOP_WORDS and words[i + 1] not in STOP_WORDS:
            bigram = f"{words[i]} {words[i + 1]}"
            if len(bigram) > 3:
                roots.add(bigram)

    return roots


def aggregate_by_roots(search_df: pd.DataFrame, compound_roots: list = None) -> pd.DataFrame:
    """按词根聚合搜索词表现数据"""
    # 自动检测列名
    col_map = detect_columns(search_df)

    root_stats = defaultdict(lambda: {
        'search_terms': set(), 'impressions': 0, 'clicks': 0,
        'spend': 0, 'orders': 0, 'sales': 0
    })

    for _, row in search_df.iterrows():
        term = str(row[col_map['search_term']])
        roots = extract_keyword_roots(term, compound_roots)

        for root in roots:
            stats = root_stats[root]
            stats['search_terms'].add(term)
            stats['impressions'] += row.get(col_map['impressions'], 0)
            stats['clicks'] += row.get(col_map['clicks'], 0)
            stats['spend'] += row.get(col_map['spend'], 0)
            stats['orders'] += row.get(col_map['orders'], 0)
            stats['sales'] += row.get(col_map['sales'], 0)

    # 转换为DataFrame
    result = []
    for root, stats in root_stats.items():
        cvr = stats['orders'] / stats['clicks'] * 100 if stats['clicks'] > 0 else 0
        acos = stats['spend'] / stats['sales'] * 100 if stats['sales'] > 0 else 0

        # 执行建议
        suggestion = get_root_suggestion(acos, stats['orders'], stats['spend'])

        result.append({
            '词根': root,
            '搜索词数': len(stats['search_terms']),
            '展示量': stats['impressions'],
            '点击量': stats['clicks'],
            '花费': round(stats['spend'], 2),
            '订单': stats['orders'],
            '销售额': round(stats['sales'], 2),
            'CVR': round(cvr, 2),
            'ACOS': round(acos, 2),
            '执行建议': suggestion
        })

    return pd.DataFrame(result).sort_values('ACOS')


def get_root_suggestion(acos: float, orders: int, spend: float) -> str:
    """根据词根表现生成执行建议"""
    if acos > 100 and spend > 10:
        return '优先否定'
    elif acos > 50 and orders >= 3:
        return '降低出价或否定'
    elif acos > 30 and orders >= 3:
        return '优化匹配或降出价'
    elif acos < 20 and orders >= 3:
        return '核心词，加大投放'
    elif acos < 30 and orders >= 3:
        return '稳定词，维持'
    elif orders == 0 and spend > 5:
        return '无订单，建议否定'
    else:
        return '监控'


# ============================================================
# 否定词清单生成
# ============================================================

def generate_negation_list(root_df: pd.DataFrame) -> pd.DataFrame:
    """生成否定词执行清单"""
    negations = []

    for _, row in root_df.iterrows():
        root = row['词根']
        acos = row['ACOS']
        spend = row['花费']
        orders = row['订单']
        clicks = row['点击量']

        neg_type = '词组' if len(str(root).split()) > 1 else '精确'

        # P0-紧急：ACOS>150% 且 花费>$20
        if acos > 150 and spend > 20:
            negations.append({
                '否定词根': root,
                '否定类型': neg_type,
                '命中搜索词': f'包含"{root}"的搜索词',
                '点击量': clicks,
                '花费': spend,
                '订单': orders,
                '优先级': 'P0-紧急',
                '否定理由': f'{root} ACOS {acos:.1f}%，花费${spend:.2f}仅{orders}单，严重亏损'
            })
        # P1-高：ACOS>100% 且 花费>$10
        elif acos > 100 and spend > 10:
            negations.append({
                '否定词根': root,
                '否定类型': neg_type,
                '命中搜索词': f'包含"{root}"的搜索词',
                '点击量': clicks,
                '花费': spend,
                '订单': orders,
                '优先级': 'P1-高',
                '否定理由': f'{root} ACOS {acos:.1f}%，花费${spend:.2f}仅{orders}单'
            })
        # P2-中：有花费无订单 且 花费>$5
        elif orders == 0 and spend > 5:
            negations.append({
                '否定词根': root,
                '否定类型': neg_type,
                '命中搜索词': f'包含"{root}"的搜索词',
                '点击量': clicks,
                '花费': spend,
                '订单': 0,
                '优先级': 'P2-中',
                '否定理由': f'{root} 花费${spend:.2f}，{clicks}次点击，0订单'
            })

    result = pd.DataFrame(negations)
    if len(result) > 0:
        # 按优先级排序
        priority_order = {'P0-紧急': 0, 'P1-高': 1, 'P2-中': 2, 'P3-低': 3}
        result['排序键'] = result['优先级'].map(priority_order)
        result = result.sort_values('排序键').drop(columns=['排序键'])

    return result


# ============================================================
# 关键词覆盖分析
# ============================================================

def extract_listing_keywords(listing_text: str) -> set:
    """从 Listing 文本中提取关键词集合"""
    if not listing_text:
        return set()
    text = str(listing_text).lower()
    words = re.findall(r'[a-z0-9]+', text)
    keywords = set()
    # 1-gram
    for w in words:
        if w not in STOP_WORDS and len(w) > 1:
            keywords.add(w)
    # 2-gram
    for i in range(len(words) - 1):
        if words[i] not in STOP_WORDS and words[i + 1] not in STOP_WORDS:
            bigram = f"{words[i]} {words[i + 1]}"
            if len(bigram) > 3:
                keywords.add(bigram)
    return keywords


def analyze_keyword_coverage(root_df: pd.DataFrame, listing_data: dict) -> pd.DataFrame:
    """分析搜索词根与前台 Listing 的覆盖关系"""
    # 提取各区块的关键词
    title_kw = extract_listing_keywords(listing_data.get('title', ''))
    bullets_kw = extract_listing_keywords(' '.join(listing_data.get('bullets', [])))
    aplus_kw = extract_listing_keywords(listing_data.get('aplus', ''))
    desc_kw = extract_listing_keywords(listing_data.get('description', ''))

    results = []
    for _, row in root_df.iterrows():
        root = str(row['词根']).lower()
        acos = row['ACOS']
        orders = row['订单']
        spend = row['花费']

        # 检查覆盖情况
        root_words = set(root.split())

        if root in title_kw or root_words.issubset(title_kw):
            coverage = '✅'
            position = '标题'
            weight = '高'
        elif root in bullets_kw or root_words.issubset(bullets_kw):
            coverage = '✅'
            position = '五点'
            weight = '高'
        elif root in aplus_kw or root_words.issubset(aplus_kw):
            coverage = '✅'
            position = 'A+'
            weight = '中'
        elif root in desc_kw or root_words.issubset(desc_kw):
            coverage = '✅'
            position = '描述'
            weight = '低'
        elif root_words & (title_kw | bullets_kw | aplus_kw | desc_kw):
            coverage = '部分'
            position = '部分区块'
            weight = '中'
        else:
            coverage = '❌'
            position = '无'
            weight = '-'

        # 生成优化建议
        suggestion, reason = get_coverage_suggestion(
            coverage, position, acos, orders, root
        )

        results.append({
            '词根': row['词根'],
            '搜索词ACOS': acos,
            '订单': orders,
            '花费': spend,
            '前台覆盖': coverage,
            '匹配位置': position,
            '权重': weight,
            '优化建议': suggestion,
            '原因': reason
        })

    return pd.DataFrame(results)


def get_coverage_suggestion(coverage: str, position: str, acos: float,
                            orders: int, root: str) -> tuple:
    """根据覆盖状态和搜索词表现生成优化建议"""
    if coverage == '❌' and acos < 25 and orders >= 3:
        return '建议加入标题或五点', f'{root} 是核心盈利词根(ACOS {acos:.1f}%)，但未出现在前台Listing中'
    elif coverage == '✅' and position == '描述' and acos < 25 and orders >= 3:
        return '建议提升到标题或五点', f'{root} 当前仅在描述中，应提升到更高权重位置'
    elif coverage == '✅' and position in ['标题', '五点'] and acos < 25:
        return '维持现状', f'{root} 已在{position}中覆盖，表现良好'
    elif coverage == '✅' and position == '标题' and acos > 50:
        return '评估是否替换', f'{root} 在标题中但ACOS高达{acos:.1f}%'
    else:
        return '监控', '-'


# ============================================================
# 列名自动检测
# ============================================================

def detect_columns(df: pd.DataFrame) -> dict:
    """自动检测 DataFrame 中的列名映射"""
    col_map = {}

    # 搜索词列
    for pattern in ['客户搜索词', '搜索词', 'Search Term', 'Customer Search Term']:
        if pattern in df.columns:
            col_map['search_term'] = pattern
            break

    # 展示量列
    for pattern in ['展示量', 'Impressions', '曝光量']:
        if pattern in df.columns:
            col_map['impressions'] = pattern
            break

    # 点击量列
    for pattern in ['点击量', 'Clicks', '点击']:
        if pattern in df.columns:
            col_map['clicks'] = pattern
            break

    # 花费列
    for pattern in ['花费', 'Spend', '广告花费']:
        if pattern in df.columns:
            col_map['spend'] = pattern
            break

    # 订单列
    for pattern in ['7天总订单数(#)', '订单数', 'Orders', '7天总订单数']:
        if pattern in df.columns:
            col_map['orders'] = pattern
            break

    # 销售额列
    for pattern in ['7天总销售额', '销售额', 'Sales', '7天总销售额($)']:
        if pattern in df.columns:
            col_map['sales'] = pattern
            break

    # ASIN列
    for pattern in ['ASIN', 'asin']:
        if pattern in df.columns:
            col_map['asin'] = pattern
            break

    # 广告活动列
    for pattern in ['广告活动', '广告活动名称', 'Campaign', 'Campaign Name']:
        if pattern in df.columns:
            col_map['campaign'] = pattern
            break

    # 验证必需列
    required = ['search_term', 'clicks', 'spend']
    missing = [k for k in required if k not in col_map]
    if missing:
        raise ValueError(f"缺少必需列: {missing}。当前列: {list(df.columns)}")

    return col_map


# ============================================================
# 数据验证
# ============================================================

def validate_data(df: pd.DataFrame, data_type: str = 'search_terms') -> dict:
    """验证数据完整性"""
    issues = []

    if data_type == 'search_terms':
        col_map = detect_columns(df)
        required_cols = ['search_term', 'impressions', 'clicks', 'spend', 'orders', 'sales']
        for col_key in required_cols:
            if col_key not in col_map:
                issues.append(f"缺少列: {col_key}")

        # 检查数据量
        if len(df) < 10:
            issues.append(f"数据量过少: {len(df)} 行，建议至少 100 行")

        # 检查空值比例
        for col_key in ['search_term', 'clicks', 'spend']:
            if col_key in col_map:
                null_pct = df[col_map[col_key]].isna().mean()
                if null_pct > 0.5:
                    issues.append(f"列 {col_map[col_key]} 空值比例过高: {null_pct:.1%}")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'row_count': len(df),
    }


# ============================================================
# ASIN 匹配
# ============================================================

def extract_asin_from_campaign(campaign_name: str) -> str:
    """从广告活动名称中提取 ASIN"""
    name = str(campaign_name)
    # ASIN 格式：10位字母数字
    match = re.search(r'([A-Z0-9]{10})', name.upper())
    return match.group(1) if match else None


def classify_asin(asin: str, store_asins: list) -> str:
    """分类 ASIN 为自家或竞品"""
    if not asin:
        return '未知'
    return '自家' if asin.upper() in [a.upper() for a in store_asins] else '竞品'


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='亚马逊广告分析工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # clean 子命令
    clean_parser = subparsers.add_parser('clean', help='数据清洗')
    clean_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    clean_parser.add_argument('--output', '-o', help='输出文件路径')
    clean_parser.add_argument('--report', action='store_true', help='输出数据质量报告')

    # roots 子命令
    roots_parser = subparsers.add_parser('roots', help='词根分析')
    roots_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    roots_parser.add_argument('--output', '-o', help='输出文件路径')
    roots_parser.add_argument('--category', '-c', default='usb_hub',
                              choices=list(CATEGORY_CONFIGS.keys()),
                              help='产品品类（用于组合词根配置）')
    roots_parser.add_argument('--top-n', type=int, default=50, help='展示前 N 个词根')

    # negations 子命令
    neg_parser = subparsers.add_parser('negations', help='生成否定词清单')
    neg_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    neg_parser.add_argument('--output', '-o', help='输出文件路径')
    neg_parser.add_argument('--category', '-c', default='usb_hub',
                            choices=list(CATEGORY_CONFIGS.keys()),
                            help='产品品类')

    # coverage 子命令
    cov_parser = subparsers.add_parser('coverage', help='关键词覆盖分析')
    cov_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    cov_parser.add_argument('--listing', '-l', required=True, help='Listing JSON 文件')
    cov_parser.add_argument('--output', '-o', help='输出文件路径')
    cov_parser.add_argument('--category', '-c', default='usb_hub',
                            choices=list(CATEGORY_CONFIGS.keys()),
                            help='产品品类')

    # validate 子命令
    val_parser = subparsers.add_parser('validate', help='数据验证')
    val_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行命令
    if args.command == 'clean':
        df = pd.read_excel(args.input)
        df_clean = clean_data(df)

        if args.output:
            df_clean.to_excel(args.output, index=False)
            print(f"清洗完成: {len(df_clean)} 行，已保存到 {args.output}")
        else:
            output_path = str(Path(args.input).parent / f"{Path(args.input).stem}_cleaned.xlsx")
            df_clean.to_excel(output_path, index=False)
            print(f"清洗完成: {len(df_clean)} 行，已保存到 {output_path}")

        if args.report:
            report = generate_quality_report(df_clean)
            print(f"\n数据质量报告:")
            print(f"  总行数: {report['total_rows']}")
            print(f"  列数: {len(report['columns'])}")
            if report['missing_values']:
                print(f"  缺失值列: {list(report['missing_values'].keys())}")
            if report['anomalies']:
                print(f"  异常值: {list(report['anomalies'].keys())}")

    elif args.command == 'roots':
        df = pd.read_excel(args.input)
        df = clean_data(df)

        compound_roots = CATEGORY_CONFIGS[args.category]['compound_roots']
        roots_df = aggregate_by_roots(df, compound_roots)

        if args.output:
            roots_df.head(args.top_n).to_excel(args.output, index=False)
        else:
            output_path = str(Path(args.input).parent / f"{Path(args.input).stem}_roots.xlsx")
            roots_df.head(args.top_n).to_excel(output_path, index=False)

        # 打印摘要
        print(f"词根分析完成: {len(roots_df)} 个词根")
        print(f"\n高效词根 (ACOS<25%, 订单>=3):")
        good = roots_df[(roots_df['ACOS'] < 25) & (roots_df['订单'] >= 3)]
        for _, row in good.head(10).iterrows():
            print(f"  {row['词根']}: ACOS={row['ACOS']}%, 订单={row['订单']}, 花费=${row['花费']}")

        print(f"\n低效词根 (ACOS>50% 或 无订单):")
        bad = roots_df[(roots_df['ACOS'] > 50) | ((roots_df['订单'] == 0) & (roots_df['花费'] > 5))]
        for _, row in bad.head(10).iterrows():
            print(f"  {row['词根']}: ACOS={row['ACOS']}%, 订单={row['订单']}, 花费=${row['花费']}")

    elif args.command == 'negations':
        df = pd.read_excel(args.input)
        df = clean_data(df)

        compound_roots = CATEGORY_CONFIGS[args.category]['compound_roots']
        roots_df = aggregate_by_roots(df, compound_roots)
        neg_df = generate_negation_list(roots_df)

        if args.output:
            neg_df.to_excel(args.output, index=False)
        else:
            output_path = str(Path(args.input).parent / f"{Path(args.input).stem}_negations.xlsx")
            neg_df.to_excel(output_path, index=False)

        print(f"否定词清单生成完成: {len(neg_df)} 个词根")
        for _, row in neg_df.head(10).iterrows():
            print(f"  [{row['优先级']}] {row['否定词根']}: {row['否定理由']}")

    elif args.command == 'coverage':
        df = pd.read_excel(args.input)
        df = clean_data(df)

        with open(args.listing, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)

        compound_roots = CATEGORY_CONFIGS[args.category]['compound_roots']
        roots_df = aggregate_by_roots(df, compound_roots)
        coverage_df = analyze_keyword_coverage(roots_df, listing_data)

        if args.output:
            coverage_df.to_excel(args.output, index=False)
        else:
            output_path = str(Path(args.input).parent / f"{Path(args.input).stem}_coverage.xlsx")
            coverage_df.to_excel(output_path, index=False)

        # 打印摘要
        covered = len(coverage_df[coverage_df['前台覆盖'] == '✅'])
        partial = len(coverage_df[coverage_df['前台覆盖'] == '部分'])
        uncovered = len(coverage_df[coverage_df['前台覆盖'] == '❌'])
        total = len(coverage_df)

        print(f"关键词覆盖分析完成:")
        print(f"  已覆盖: {covered}/{total} ({covered / total * 100:.1f}%)")
        print(f"  部分覆盖: {partial}/{total} ({partial / total * 100:.1f}%)")
        print(f"  未覆盖: {uncovered}/{total} ({uncovered / total * 100:.1f}%)")

        # 需要加入前台的高效词根
        need_add = coverage_df[
            (coverage_df['前台覆盖'] == '❌') &
            (coverage_df['搜索词ACOS'] < 25) &
            (coverage_df['订单'] >= 3)
            ]
        if len(need_add) > 0:
            print(f"\n需加入前台的高效词根:")
            for _, row in need_add.head(5).iterrows():
                print(f"  {row['词根']}: ACOS={row['搜索词ACOS']}%, 建议{row['优化建议']}")

    elif args.command == 'validate':
        df = pd.read_excel(args.input)
        result = validate_data(df)

        if result['valid']:
            print(f"数据验证通过: {result['row_count']} 行")
        else:
            print(f"数据验证失败:")
            for issue in result['issues']:
                print(f"  - {issue}")


if __name__ == '__main__':
    main()
