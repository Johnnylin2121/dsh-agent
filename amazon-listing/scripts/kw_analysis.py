#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Amazon listing 竞品关键词词频分析 (amazon-listing skill Step 1)

用法:
  python kw_analysis.py -i competitors.txt
      # 单文件:每竞品 = 标题行 + 跟随的五点行,竞品之间用空行分隔
  python kw_analysis.py -t titles.txt -b bullets.txt
      # 双文件:每行一条

评分规则(与 SKILL.md 一致):
  标题词 1-gram ×3,五点词 ×1;2-gram 同权;@ 保留以把 8K@60Hz 当整体词。
输出: Top N 的 1-gram 与 2-gram 得分排名,agent 再按品类身份人工筛选 Top10。
"""
import argparse
import collections
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')


def norm(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9@]+', ' ', s)  # 保留 @ → 8K@60Hz 为一整体词
    return s.split()


def ngrams(toks, n):
    return [' '.join(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '--input', help='单文件:标题行+五点行,竞品间空行')
    ap.add_argument('-t', '--titles', help='标题文件(每行一条)')
    ap.add_argument('-b', '--bullets', help='五点文件(每行一条)')
    ap.add_argument('-n', '--top', type=int, default=30)
    args = ap.parse_args()

    titles, bullets = [], []
    if args.input:
        cur = None
        for line in open(args.input, encoding='utf-8'):
            line = line.strip()
            if not line:
                cur = None
                continue
            if cur is None:
                titles.append(line)
                cur = 't'
            else:
                bullets.append(line)
    else:
        titles = [l.strip() for l in open(args.titles, encoding='utf-8') if l.strip()]
        if args.bullets:
            bullets = [l.strip() for l in open(args.bullets, encoding='utf-8') if l.strip()]

    if not titles:
        sys.exit('无输入数据')

    c1, c2 = collections.Counter(), collections.Counter()
    for t in titles:
        toks = norm(t)
        for w in toks:
            c1[w] += 3
        for g in ngrams(toks, 2):
            c2[g] += 3
    for b in bullets:
        toks = norm(b)
        for w in toks:
            c1[w] += 1
        for g in ngrams(toks, 2):
            c2[g] += 1

    print(f'# 竞品标题 {len(titles)} 条,五点 {len(bullets)} 条;标题词×3 / 五点词×1')
    print(f'\n== Top {args.top} 1-gram ==')
    for w, s in c1.most_common(args.top):
        print(f'{s:4d}  {w}')
    print(f'\n== Top {args.top} 2-gram ==')
    for w, s in c2.most_common(args.top):
        print(f'{s:4d}  {w}')


if __name__ == '__main__':
    main()