#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产出规格校验器 (output-spec v2.0)

用途
----
校验 amazon-ad-analysis 生成的 Excel 工作簿是否符合 references/output-spec.md v2.0。
解决历史问题：vault 内 19 个历史 workbook 存在「规范版 / 中文变体 / 残缺版」三套
sheet 结构并存，人工无法察觉漂移。

用法
----
    python validate_output.py --input "分析数据.xlsx"
    python validate_output.py --input a.xlsx --input b.xlsx --json result.json

退出码：0 = 全部通过；1 = 存在不符合项（详情打印 / 写 json）；2 = 用法或读取错误。

依赖：openpyxl（本机 Python312 已装）。Windows 下强制 UTF-8 输出。
"""

from __future__ import annotations

import argparse
import json
import sys

try:  # Windows 控制台中文安全
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

SCHEMA_VERSION = "2.0"

# ---- 契约（与 references/output-spec.md 第四节一致；改这里必须同时升 SCHEMA_VERSION）----
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "_Meta": [
        "schema_version", "generated_at", "data_range_start", "data_range_end",
        "stores", "source_files", "data_level", "degradations", "analysis_date", "spec_ref",
    ],
    "Decisions": [
        "priority", "action", "target", "metric_basis", "expected",
        "verify_date", "rollback", "difficulty",
    ],
    "ASIN_Matrix": [
        "asin", "store", "price", "rating", "reviews", "units", "revenue", "orders",
        "sessions", "cvr", "ad_spend", "acos", "tacos", "roas",
        "natural_order_share", "ad_order_share", "new_customer_share",
        "new_customer_verdict", "lifecycle_stage", "position_tier", "potential",
        "campaign_count", "top1_ratio", "hhi_ratio", "concentration_flag", "action_group",
    ],
    "Weekly_Trend": [
        "asin", "week", "units", "revenue", "orders", "sessions", "cvr",
        "ad_spend", "acos", "tacos", "roas", "natural_orders", "natural_order_share",
    ],
    "Ad_Structure": [
        "asin", "campaign", "type", "spend_28d", "spend_share", "cum_share",
        "orders_28d", "acos_28d", "trend",
    ],
    "Paid_Natural": [
        "asin", "keyword", "ad_clicks", "ad_click_share", "ad_spend", "ad_orders",
        "quadrant", "ad_spend_w3", "ad_spend_w4", "natural_orders_w3", "natural_orders_w4",
        "traffic_source", "contribution_share", "organic_rank", "word_state", "verdict", "action",
    ],
    "Root_Words": [
        "root", "root_type", "demand_type", "search_term_count", "spend", "orders",
        "sales", "cvr", "acos", "w1_acos", "w2_acos", "w3_acos", "w4_acos",
        "trend", "word_state", "action",
    ],
    "Negations": [
        "priority", "root", "negate_type", "sample_term", "clicks", "spend", "orders", "reason",
    ],
    "Coverage": [
        "root", "demand_type", "acos", "orders", "spend",
        "front_covered", "position", "weight", "action",
    ],
}

SHEET_ORDER = list(REQUIRED_COLUMNS.keys())

# 允许存在但不在契约内且不报警的附加 sheet（留扩展位）
ALLOWED_EXTRA: set[str] = set()


def _norm(value) -> str:
    return str(value).strip().lower().replace(" ", "_") if value is not None else ""


def check_workbook(path: str) -> dict:
    result: dict = {"file": path, "ok": False, "missing_sheets": [], "extra_sheets": [],
                    "missing_columns": {}, "meta_errors": [], "errors": []}
    try:
        import openpyxl
    except ImportError:
        result["errors"].append("openpyxl 未安装：pip install openpyxl")
        return result

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"无法读取工作簿：{exc}")
        return result

    names = list(wb.sheetnames)
    result["sheets_found"] = names

    # 1) sheet 存在性
    result["missing_sheets"] = [s for s in SHEET_ORDER if s not in names]
    result["extra_sheets"] = [s for s in names if s not in SHEET_ORDER and s not in ALLOWED_EXTRA]

    # 2) 必需列
    for sheet, required in REQUIRED_COLUMNS.items():
        if sheet not in names:
            continue
        ws = wb[sheet]
        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        found = {_norm(c) for c in header if c is not None}
        missing = [c for c in required if c not in found]
        if missing:
            result["missing_columns"][sheet] = missing

    # 3) _Meta 内容
    if "_Meta" in names:
        ws = wb["_Meta"]
        rows = list(ws.iter_rows(values_only=True))
        meta: dict[str, str] = {}
        if rows:
            header_norm = [_norm(c) for c in rows[0]]
            if "schema_version" in header_norm:
                # 列式布局：首行 = 字段名，第二行 = 取值
                values = rows[1] if len(rows) > 1 else ()
                for i, key in enumerate(header_norm):
                    if key:
                        val = values[i] if i < len(values) else None
                        meta[key] = "" if val is None else str(val).strip()
            else:
                # 键值式布局：首列 = 键，第二列 = 值
                for row in rows:
                    if row and row[0] is not None:
                        key = _norm(row[0])
                        val = row[1] if len(row) > 1 else None
                        meta[key] = "" if val is None else str(val).strip()
        ver = meta.get("schema_version", "")
        if ver != SCHEMA_VERSION:
            result["meta_errors"].append(
                f"schema_version = '{ver}'，契约要求 '{SCHEMA_VERSION}'"
            )
        if meta.get("data_level", "").strip().upper() not in {"A", "B", "C"}:
            result["meta_errors"].append(
                f"data_level = '{meta.get('data_level', '')}'，应为 A/B/C"
            )
        if not meta.get("degradations", "").strip():
            result["meta_errors"].append("degradations 为空；无降级时须显式填 'none'")
        result["meta"] = meta
    wb.close()

    result["ok"] = not (
        result["missing_sheets"] or result["missing_columns"]
        or result["meta_errors"] or result["errors"]
    )
    return result


def report(result: dict) -> None:
    print("=" * 72)
    print(f"文件：{result['file']}")
    if result.get("sheets_found") is not None:
        print(f"实际 sheet（{len(result['sheets_found'])}）：{', '.join(result['sheets_found'])}")
    for err in result["errors"]:
        print(f"  [错误] {err}")
    if result["missing_sheets"]:
        print(f"  [缺 sheet] {', '.join(result['missing_sheets'])}")
    for sheet, cols in result["missing_columns"].items():
        print(f"  [缺列] {sheet}: {', '.join(cols)}")
    for err in result["meta_errors"]:
        print(f"  [Meta] {err}")
    if result["extra_sheets"]:
        print(f"  [额外 sheet·提示] {', '.join(result['extra_sheets'])}")
    print("  结果：" + ("✅ PASS（符合 output-spec v2.0）" if result["ok"] else "❌ FAIL（不符合契约）"))


def main() -> int:
    parser = argparse.ArgumentParser(description="校验分析产出是否符合 output-spec v2.0")
    parser.add_argument("--input", action="append", required=True, help="待校验 xlsx（可多次）")
    parser.add_argument("--json", help="把结果写入该 JSON 文件")
    args = parser.parse_args()

    results = [check_workbook(p) for p in args.input]
    for r in results:
        report(r)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON 已写入：{args.json}")

    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
