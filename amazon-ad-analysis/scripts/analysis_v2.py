#!/usr/bin/env python3
"""
亚马逊广告分析脚本 v2.0
改进版：修复数据清洗bug，增强列名自动检测，支持配置外部化

用法:
    # 完整分析
    python analysis_v2.py run --product product.xlsx --ad ad.xlsx --search search.xlsx --brand brand.xlsx

    # 仅数据清洗
    python analysis_v2.py clean --input raw.xlsx --output cleaned.xlsx --report

    # 仅词根分析
    python analysis_v2.py roots --input search.xlsx --category usb_hub --top-n 50

    # 仅否定词生成
    python analysis_v2.py negations --input search.xlsx --category usb_hub

    # 仅关键词覆盖分析
    python analysis_v2.py coverage --input search.xlsx --listing listing.json --category usb_hub

    # 数据验证
    python analysis_v2.py validate --input product.xlsx

    # 生成配置文件模板
    python analysis_v2.py init-config --output ./config/analysis_config.yaml

依赖:
    pip install pandas openpyxl pyyaml
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import json
from collections import defaultdict
import os
import sys
import time
import pickle
from typing import Dict, List, Optional, Tuple, Any

# ============================================================
# 配置加载器
# ============================================================

class ConfigLoader:
    """配置加载器"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'analysis_config.yaml'
    
    def __init__(self, config_path=None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            import yaml
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                print(f"警告: 配置文件不存在: {self.config_path}")
                return self._default_config()
        except ImportError:
            print("警告: 未安装pyyaml，使用默认配置")
            return self._default_config()
    
    def _default_config(self):
        """默认配置"""
        return {
            'thresholds': {
                'acos': {'good': 0.20, 'acceptable': 0.35, 'needs_optimization': 0.50},
                'cvr': {'good': 0.15, 'average': 0.10}
            },
            'output': {
                'directory': './output',
                'save_checkpoints': True
            }
        }
    
    def get(self, key, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_threshold(self, metric, level):
        """获取阈值"""
        return self.get(f'thresholds.{metric}.{level}')
    
    def get_column_mapping(self, file_type):
        """获取列名映射"""
        return self.get(f'column_mapping.{file_type}', {})
    
    def get_category_config(self, category):
        """获取品类配置"""
        return self.get(f'categories.{category}', {})


# ============================================================
# 列名自动检测
# ============================================================

class ColumnMapper:
    """列名自动检测和映射"""
    
    # 默认列名映射规则（优先级从高到低）
    DEFAULT_COLUMN_PATTERNS = {
        'asin': ['ASIN', 'asin', 'Asin'],
        'sales': ['销量', 'Sales', 'sales'],
        'revenue': ['销售额', 'Revenue', 'revenue', 'Sales Amount'],
        'orders': ['订单量', 'Orders', 'orders', 'Order Count'],
        'sessions': ['Sessions-Total', 'Sessions', 'sessions'],
        'cvr': ['CVR', 'cvr', 'Conversion Rate'],
        'acos': ['ACOS', 'ACoS', 'acos', 'Advertising Cost of Sales'],
        'tacos': ['TACOS', 'TACoS', 'tacos', 'Total ACOS'],
        'roas': ['ROAS', 'Roas', 'roas', 'Return on Ad Spend'],
        'ad_spend': ['广告花费', 'Ad Spend', 'ad_spend', 'Spend'],
        'ad_sales': ['广告销售额', 'Ad Sales', 'ad_sales'],
        'natural_orders': ['自然订单量', 'Natural Orders', 'natural_orders'],
        'impressions': ['展示量', 'Impressions', 'impressions', '曝光量'],
        'clicks': ['点击量', 'Clicks', 'clicks', '点击'],
        'cpc': ['CPC', 'cpc', 'Cost Per Click'],
        'ctr': ['CTR', 'ctr', 'Click Through Rate'],
        'search_term': ['客户搜索词', '搜索词', 'Search Term', 'Customer Search Term'],
        'campaign': ['广告活动', '广告活动名称', 'Campaign', 'Campaign Name'],
        'ad_group': ['广告组', '广告组名称', 'Ad Group', 'Ad Group Name'],
        'date': ['日期', 'Date', 'date', '报告日期'],
        'brand': ['品牌', 'Brand', 'brand'],
        # ===== 搜索词文件特有列（聚合必需）=====
        'spend': ['花费', 'Spend', 'Ad Spend', '广告花费'],
        'sales_7d': ['7天总销售额', '7天总销售额($)', '7d Sales', 'Sales'],
        'orders_7d': ['7天总订单数(#)', '7天总订单数', '7d Orders', 'Orders'],
        'product_name': ['品名', 'Product Name', 'product_name', '标题'],
        'price': ['售价', 'Price', 'price', '售价(总价)'],
        'start_date': ['开始日期', 'Start Date', 'start_date'],
        'end_date': ['结束日期', 'End Date', 'end_date'],
    }
    
    def __init__(self, df, config=None, file_type='product'):
        self.df = df
        self.columns = list(df.columns)
        self.mapping = {}
        
        # 从配置加载列名映射（按文件类型：product / ad / search / brand）
        if config:
            self.config_patterns = config.get_column_mapping(file_type)
        else:
            self.config_patterns = {}
        
        self._detect_all()
    
    def _detect_all(self):
        """自动检测所有列"""
        # 首先使用配置中的映射
        for col_type, patterns in self.config_patterns.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    if pattern in self.columns:
                        self.mapping[col_type] = pattern
                        break
        
        # 然后使用默认映射（补充未检测到的列）
        for col_type, patterns in self.DEFAULT_COLUMN_PATTERNS.items():
            if col_type not in self.mapping:
                for pattern in patterns:
                    if pattern in self.columns:
                        self.mapping[col_type] = pattern
                        break
    
    def get(self, col_type, default=None):
        """获取列名"""
        return self.mapping.get(col_type, default)
    
    def get_column(self, col_type):
        """获取列数据"""
        col_name = self.get(col_type)
        if col_name:
            return self.df[col_name]
        return None
    
    def validate_required(self, required_cols):
        """验证必需列是否存在"""
        missing = []
        for col_type in required_cols:
            if col_type not in self.mapping:
                missing.append(col_type)
        return missing
    
    def print_mapping(self):
        """打印映射结果"""
        print("列名映射结果:")
        for col_type, col_name in self.mapping.items():
            print(f"  {col_type}: {col_name}")


# ============================================================
# 数据清洗（改进版）
# ============================================================

def smart_percentage_convert(value):
    """
    智能百分比转换，处理多种格式：
    - "21.90%" → 0.219
    - 0.219 → 0.219（已经是小数）
    - "21.90" → 0.219（假设是百分比）
    - "0.219" → 0.219（已经是小数）
    - "--" → 0
    - "0%" → 0
    """
    if pd.isna(value):
        return np.nan
    
    if isinstance(value, (int, float)):
        # 已经是数值
        if value > 1:
            # 可能是百分比形式（如21.90表示21.90%）
            return value / 100
        return value
    
    if isinstance(value, str):
        value = value.strip()
        
        # 特殊值处理
        if value in ['--', '-', 'N/A', 'nan', '']:
            return 0
        
        # 带%的字符串
        if '%' in value:
            try:
                return float(value.replace('%', '')) / 100
            except ValueError:
                return np.nan
        
        # 纯数字字符串
        try:
            num = float(value)
            if num > 1:
                # 可能是百分比形式
                return num / 100
            return num
        except ValueError:
            return np.nan
    
    return np.nan


def clean_percentage_columns(df, columns):
    """批量清洗百分比列"""
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(smart_percentage_convert)
            
            # 验证转换结果
            valid_count = df_clean[col].notna().sum()
            if valid_count == 0:
                print(f"警告: 列 {col} 转换后全部为NaN")
    
    return df_clean


def clean_currency_columns(df, columns):
    """清洗货币列，移除符号并转换为数值"""
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            if df_clean[col].dtype == object:
                # 移除货币符号、逗号等
                df_clean[col] = df_clean[col].astype(str).str.replace('$', '').str.replace(',', '').str.replace('--', '0')
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    return df_clean


def clean_dataframe(df, file_type='product', config=None):
    """
    清洗单个DataFrame（改进版）
    
    Args:
        df: 原始DataFrame
        file_type: 文件类型 ('product', 'ad', 'search', 'brand')
        config: 配置对象
    
    Returns:
        清洗后的DataFrame
    """
    df_clean = df.copy()
    
    # 1. 替换特殊值
    df_clean = df_clean.replace(['--', '-', 'N/A', 'nan', ''], np.nan)
    
    # 2. 创建列名映射器
    mapper = ColumnMapper(df_clean, config)
    
    # 3. 根据文件类型确定需要清洗的列
    percentage_cols = []
    numeric_cols = []
    
    if file_type == 'product':
        percentage_cols = ['cvr', 'acos', 'tacos', 'roas', 'ctr']
        numeric_cols = ['sales', 'revenue', 'orders', 'ad_spend', 'impressions', 'clicks', 'natural_orders']
    elif file_type == 'ad':
        percentage_cols = ['acos', 'roas', 'ctr', 'cvr']
        numeric_cols = ['impressions', 'clicks', 'spend', 'sales', 'orders']
    elif file_type == 'search':
        percentage_cols = ['ctr', 'cvr', 'acos']
        numeric_cols = ['impressions', 'clicks', 'spend', 'sales', 'orders']
    elif file_type == 'brand':
        percentage_cols = []  # 品牌广告归因文件中的百分比列需要特殊处理
        numeric_cols = ['sales_14d', 'orders_14d', 'units_14d', 'new_customer_sales', 'new_customer_orders', 'new_customer_units']
    
    # 4. 清洗百分比列
    for col_type in percentage_cols:
        col_name = mapper.get(col_type)
        if col_name:
            df_clean[col_name] = df_clean[col_name].apply(smart_percentage_convert)
    
    # 5. 清洗数值列
    for col_type in numeric_cols:
        col_name = mapper.get(col_type)
        if col_name:
            df_clean[col_name] = pd.to_numeric(df_clean[col_name], errors='coerce').fillna(0)
    
    # 6. 日期处理
    date_col = mapper.get('date')
    if date_col:
        df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors='coerce')
    
    return df_clean


# ============================================================
# 搜索词日期处理
# ============================================================

def detect_search_term_format(df):
    """
    检测搜索词报告的日期格式
    返回: 'single_date', 'date_range', 'unknown'
    """
    columns = list(df.columns)
    
    # 检查是否有开始日期和结束日期列
    has_start_date = any('开始日期' in col or 'Start Date' in col for col in columns)
    has_end_date = any('结束日期' in col or 'End Date' in col for col in columns)
    
    if has_start_date and has_end_date:
        return 'date_range'
    
    # 检查是否有单个日期列
    has_date = any('日期' in col or 'Date' in col for col in columns)
    if has_date:
        return 'single_date'
    
    return 'unknown'


def filter_single_day_rows(df, date_format='auto'):
    """
    过滤搜索词报告中的单日行
    
    Args:
        df: 搜索词数据
        date_format: 'auto', 'single_date', 'date_range'
    
    Returns:
        过滤后的DataFrame（仅包含单日行）
    """
    if date_format == 'auto':
        date_format = detect_search_term_format(df)
    
    if date_format == 'single_date':
        # 只有单个日期列，假设都是单日行
        return df.copy()
    
    elif date_format == 'date_range':
        # 有开始日期和结束日期列
        mapper = ColumnMapper(df)
        start_date_col = mapper.get('start_date')
        end_date_col = mapper.get('end_date')
        
        if start_date_col and end_date_col:
            # 过滤单日行：开始日期 == 结束日期
            mask = df[start_date_col] == df[end_date_col]
            single_day_df = df[mask].copy()
            
            print(f"搜索词行类型统计:")
            print(f"  总行数: {len(df)}")
            print(f"  单日行: {len(single_day_df)}")
            print(f"  多日行: {len(df) - len(single_day_df)}")
            
            return single_day_df
    
    # 默认返回原数据
    return df.copy()


# ============================================================
# 数据验证
# ============================================================

def validate_data(df, file_type='product', config=None):
    """
    验证数据完整性
    
    Args:
        df: DataFrame
        file_type: 文件类型
        config: 配置对象
    
    Returns:
        dict: {'valid': bool, 'issues': list, 'row_count': int}
    """
    issues = []
    
    # 获取必需列配置
    if config:
        required_cols = config.get(f'validation.required_columns.{file_type}', [])
    else:
        # 默认必需列
        required_cols_map = {
            'product': ['asin', 'sales', 'revenue'],
            'ad': ['campaign', 'impressions', 'clicks', 'spend'],
            'search': ['search_term', 'impressions', 'clicks', 'spend'],
            'brand': ['asin']
        }
        required_cols = required_cols_map.get(file_type, [])
    
    # 检查必需列
    mapper = ColumnMapper(df, config)
    missing = mapper.validate_required(required_cols)
    if missing:
        issues.append(f"缺少必需列: {missing}")
    
    # 检查数据量
    min_rows = config.get('validation.min_rows', 10) if config else 10
    if len(df) < min_rows:
        issues.append(f"数据量过少: {len(df)} 行，建议至少 {min_rows} 行")
    
    # 检查空值比例
    max_null_pct = config.get('validation.max_null_percentage', 0.5) if config else 0.5
    for col_type in required_cols:
        col_name = mapper.get(col_type)
        if col_name:
            null_pct = df[col_name].isna().mean()
            if null_pct > max_null_pct:
                issues.append(f"列 {col_name} 空值比例过高: {null_pct:.1%}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'row_count': len(df),
    }


# ============================================================
# 词根分析
# ============================================================

# 停用词列表
STOP_WORDS = {
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
}


def extract_keyword_roots(search_term, compound_roots=None):
    """从搜索词中提取词根（可重叠）"""
    if compound_roots is None:
        compound_roots = []
    
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


def aggregate_by_roots(search_df, compound_roots=None, config=None):
    """按词根聚合搜索词表现数据"""
    # 自动检测列名（file_type='search'，映射见 config column_mapping.search 与 DEFAULT 补充）
    mapper = ColumnMapper(search_df, config, file_type='search')
    
    root_stats = defaultdict(lambda: {
        'search_terms': set(), 'impressions': 0, 'clicks': 0,
        'spend': 0, 'orders': 0, 'sales': 0
    })
    
    for _, row in search_df.iterrows():
        term = str(row[mapper.get('search_term', '')])
        roots = extract_keyword_roots(term, compound_roots)
        
        for root in roots:
            stats = root_stats[root]
            stats['search_terms'].add(term)
            
            impressions = mapper.get('impressions')
            if impressions:
                stats['impressions'] += row.get(impressions, 0)
            
            clicks = mapper.get('clicks')
            if clicks:
                stats['clicks'] += row.get(clicks, 0)
            
            spend = mapper.get('spend')
            if spend:
                stats['spend'] += row.get(spend, 0)
            
            orders = mapper.get('orders') or mapper.get('orders_7d')
            if orders:
                stats['orders'] += row.get(orders, 0)
            
            sales = mapper.get('sales') or mapper.get('sales_7d')
            if sales:
                stats['sales'] += row.get(sales, 0)
    
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


def get_root_suggestion(acos, orders, spend):
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

def generate_negation_list(root_df):
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

def extract_listing_keywords(listing_text):
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


def analyze_keyword_coverage(root_df, listing_data):
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


def get_coverage_suggestion(coverage, position, acos, orders, root):
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
# 数据质量报告
# ============================================================

def generate_quality_report(df):
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
    mapper = ColumnMapper(df)
    
    acos_col = mapper.get('acos')
    if acos_col:
        acos_values = pd.to_numeric(df[acos_col], errors='coerce').dropna()
        high_acos = acos_values[acos_values > 1.0]  # >100%
        if len(high_acos) > 0:
            report['anomalies']['high_acos'] = {
                'count': len(high_acos),
                'threshold': '>100%',
                'examples': high_acos.head(5).tolist()
            }
    
    cpc_col = mapper.get('cpc')
    if cpc_col:
        cpc_values = pd.to_numeric(df[cpc_col], errors='coerce').dropna()
        high_cpc = cpc_values[cpc_values > 5.0]
        if len(high_cpc) > 0:
            report['anomalies']['high_cpc'] = {
                'count': len(high_cpc),
                'threshold': '>$5',
                'examples': high_cpc.head(5).tolist()
            }
    
    return report


# ============================================================
# CLI 入口
# ============================================================

def main():
    # Windows GBK 控制台下中文列名/emoji 输出乱码或崩溃：强制 UTF-8
    if os.name == 'nt':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description='亚马逊广告分析工具 v2.0')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # clean 子命令
    clean_parser = subparsers.add_parser('clean', help='数据清洗')
    clean_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    clean_parser.add_argument('--output', '-o', help='输出文件路径')
    clean_parser.add_argument('--report', action='store_true', help='输出数据质量报告')
    clean_parser.add_argument('--config', '-c', help='配置文件路径')
    
    # roots 子命令
    roots_parser = subparsers.add_parser('roots', help='词根分析')
    roots_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    roots_parser.add_argument('--output', '-o', help='输出文件路径')
    roots_parser.add_argument('--category', '-c', default='usb_hub',
                              choices=['usb_hub', 'electronics', 'home', 'custom'],
                              help='产品品类（用于组合词根配置）')
    roots_parser.add_argument('--top-n', type=int, default=50, help='展示前 N 个词根')
    roots_parser.add_argument('--config', help='配置文件路径')
    
    # negations 子命令
    neg_parser = subparsers.add_parser('negations', help='生成否定词清单')
    neg_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    neg_parser.add_argument('--output', '-o', help='输出文件路径')
    neg_parser.add_argument('--category', '-c', default='usb_hub',
                            choices=['usb_hub', 'electronics', 'home', 'custom'],
                            help='产品品类')
    neg_parser.add_argument('--config', help='配置文件路径')
    
    # coverage 子命令
    cov_parser = subparsers.add_parser('coverage', help='关键词覆盖分析')
    cov_parser.add_argument('--input', '-i', required=True, help='输入搜索词 Excel')
    cov_parser.add_argument('--listing', '-l', required=True, help='Listing JSON 文件')
    cov_parser.add_argument('--output', '-o', help='输出文件路径')
    cov_parser.add_argument('--category', '-c', default='usb_hub',
                            choices=['usb_hub', 'electronics', 'home', 'custom'],
                            help='产品品类')
    cov_parser.add_argument('--config', help='配置文件路径')
    
    # validate 子命令
    val_parser = subparsers.add_parser('validate', help='数据验证')
    val_parser.add_argument('--input', '-i', required=True, help='输入 Excel 文件路径')
    val_parser.add_argument('--type', '-t', default='product',
                           choices=['product', 'ad', 'search', 'brand'],
                           help='数据类型')
    val_parser.add_argument('--config', help='配置文件路径')
    
    # run 子命令（完整分析）
    run_parser = subparsers.add_parser('run', help='完整分析')
    run_parser.add_argument('--product', help='产品表现文件路径')
    run_parser.add_argument('--ad', help='广告表现文件路径')
    run_parser.add_argument('--search', help='搜索词文件路径')
    run_parser.add_argument('--brand', help='品牌广告归因文件路径')
    run_parser.add_argument('--output', '-o', default='./output', help='输出目录')
    run_parser.add_argument('--config', '-c', help='配置文件路径')
    
    # init-config 子命令
    init_parser = subparsers.add_parser('init-config', help='生成配置文件模板')
    init_parser.add_argument('--output', '-o', default='./config/analysis_config.yaml', help='输出路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 加载配置
    config = None
    if hasattr(args, 'config') and args.config:
        config = ConfigLoader(args.config)
    else:
        config = ConfigLoader()
    
    # 执行命令
    if args.command == 'clean':
        df = pd.read_excel(args.input)
        df_clean = clean_dataframe(df, 'product', config)
        
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
        df = clean_dataframe(df, 'search', config)
        
        # 获取品类配置
        category_config = config.get_category_config(args.category)
        compound_roots = category_config.get('compound_roots', [])
        
        roots_df = aggregate_by_roots(df, compound_roots, config)
        
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
        df = clean_dataframe(df, 'search', config)
        
        # 获取品类配置
        category_config = config.get_category_config(args.category)
        compound_roots = category_config.get('compound_roots', [])
        
        roots_df = aggregate_by_roots(df, compound_roots, config)
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
        df = clean_dataframe(df, 'search', config)
        
        with open(args.listing, 'r', encoding='utf-8') as f:
            listing_data = json.load(f)
        
        # 获取品类配置
        category_config = config.get_category_config(args.category)
        compound_roots = category_config.get('compound_roots', [])
        
        roots_df = aggregate_by_roots(df, compound_roots, config)
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
        result = validate_data(df, args.type, config)
        
        if result['valid']:
            print(f"数据验证通过: {result['row_count']} 行")
        else:
            print(f"数据验证失败:")
            for issue in result['issues']:
                print(f"  - {issue}")
    
    elif args.command == 'run':
        print("run 完整流程尚未实现；请用子命令组合执行：")
        print("  1) clean    --input <产品表现.xlsx> --report   # 数据清洗+质量报告")
        print("  2) roots    --input <搜索词.xlsx> --category usb_hub")
        print("  3) negations --input <搜索词.xlsx> --category usb_hub")
        print("  4) coverage --input <搜索词.xlsx> --listing listing.json")
        print("  5) validate --input <产品表现.xlsx> --type product")
    
    elif args.command == 'init-config':
        # 生成配置文件模板
        config_template = ConfigLoader._default_config(None)
        
        import yaml
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(config_template, f, allow_unicode=True, default_flow_style=False)
        
        print(f"配置文件模板已生成: {args.output}")


if __name__ == '__main__':
    main()