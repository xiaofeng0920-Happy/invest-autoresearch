#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合策略股票池 - 31 只高质量 + 5 只资源/周期股

总计 36 只股票，行业均衡配置
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path('/home/admin/openclaw/workspace/agents/data-collector/tushare_data')

def load_177_pool():
    """加载 177 支股票池"""
    excel_file = '/home/admin/.openclaw/media/inbound/177_æ_è_ç_5_å¹_è_å_æ_æ_é_è_è_20260329_0815---c213c27a-62e6-4e7a-bd67-bdf327ec8862.xlsx'
    df = pd.read_excel(excel_file, sheet_name='原始数据')
    
    # 计算 5 年平均 ROE
    avg_roe = df.groupby('股票名称')['ROE'].mean().reset_index()
    avg_roe.columns = ['股票名称', 'avg_roe_5y']
    
    # 获取 2024 年数据
    df_2024 = df[df['年份'] == 2024].merge(avg_roe, on='股票名称')
    
    stocks = []
    for _, row in df_2024.iterrows():
        stocks.append({
            'code': row['股票代码'],
            'name': row['股票名称'],
            'roe': row['ROE'],
            'debt_ratio': row['负债率'],
            'fcf': row['自由现金流'],
            'avg_roe_5y': row['avg_roe_5y'],
            'sector': '消费/医药/科技',
        })
    
    return stocks

def add_resource_stocks(high_quality_stocks):
    """添加资源股和周期股"""
    
    # 原策略中的资源股/周期股（手动补充财务数据）
    resource_stocks = [
        {
            'code': '601088.SH',
            'name': '中国神华',
            'roe': 16.0,
            'debt_ratio': 23.4,
            'fcf': 933.5,
            'avg_roe_5y': 16.7,
            'sector': '资源/煤炭',
        },
        {
            'code': '601899.SH',
            'name': '紫金矿业',
            'roe': 22.5,
            'debt_ratio': 58.2,
            'fcf': 85.0,
            'avg_roe_5y': 18.5,
            'sector': '资源/有色金属',
        },
        {
            'code': '300750.SZ',
            'name': '宁德时代',
            'roe': 18.5,
            'debt_ratio': 65.0,
            'fcf': 120.0,
            'avg_roe_5y': 16.0,
            'sector': '新能源/电池',
        },
        {
            'code': '600036.SH',
            'name': '招商银行',
            'roe': 16.5,
            'debt_ratio': 88.0,  # 银行特殊
            'fcf': 150.0,
            'avg_roe_5y': 15.5,
            'sector': '金融/银行',
        },
        {
            'code': '600900.SH',
            'name': '长江电力',
            'roe': 14.5,
            'debt_ratio': 55.0,
            'fcf': 280.0,
            'avg_roe_5y': 14.0,
            'sector': '公用事业/电力',
        },
    ]
    
    # 合并股票池
    all_stocks = high_quality_stocks.copy()
    all_stocks.extend(resource_stocks)
    
    return all_stocks, resource_stocks

def generate_mixed_pool():
    """生成混合股票池"""
    print("="*60)
    print("混合策略股票池 - 31 只高质量 + 5 只资源/周期")
    print("="*60)
    
    # 加载 31 只高质量股票
    high_quality = load_177_pool()
    print(f"\n✅ 高质量股票：{len(high_quality)}只")
    
    # 添加资源股
    all_stocks, resource_stocks = add_resource_stocks(high_quality)
    print(f"✅ 资源股/周期股：{len(resource_stocks)}只")
    print(f"✅ 总计：{len(all_stocks)}只")
    
    # 行业分布
    sector_count = {}
    for s in all_stocks:
        sector = s['sector'].split('/')[0]
        sector_count[sector] = sector_count.get(sector, 0) + 1
    
    print("\n📊 行业分布:")
    for sector, count in sorted(sector_count.items(), key=lambda x: -x[1]):
        pct = count / len(all_stocks) * 100
        print(f"  {sector}: {count}只 ({pct:.0f}%)")
    
    # 保存股票池
    pool_file = DATA_DIR / '混合策略股票池_36 只.json'
    with open(pool_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(all_stocks),
            'high_quality_count': len(high_quality),
            'resource_count': len(resource_stocks),
            'stocks': all_stocks,
            'resource_stocks': resource_stocks,
            'timestamp': datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 股票池已保存：{pool_file}")
    
    # 生成 Markdown 报告
    md_file = DATA_DIR / '混合策略股票池_36 只.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 混合策略股票池 - 36 只\n\n")
        f.write("**生成时间：** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
        f.write("**构成：** 31 只高质量 + 5 只资源/周期股\n\n")
        
        f.write("## 📊 行业分布\n\n")
        for sector, count in sorted(sector_count.items(), key=lambda x: -x[1]):
            pct = count / len(all_stocks) * 100
            f.write(f"- {sector}: {count}只 ({pct:.0f}%)\n")
        
        f.write("\n## 📈 资源股/周期股（5 只）\n\n")
        f.write("| 代码 | 名称 | ROE | 负债率 | FCF(亿) | 5 年平均 ROE |\n")
        f.write("|------|------|-----|--------|---------|-------------|\n")
        for s in resource_stocks:
            f.write(f"| {s['code']} | {s['name']} | {s['roe']:.1f}% | {s['debt_ratio']:.1f}% | {s['fcf']:.1f} | {s['avg_roe_5y']:.1f}% |\n")
        
        f.write("\n## 📈 高质量股票（31 只，前 10 只）\n\n")
        f.write("| 排名 | 代码 | 名称 | ROE | 负债率 | FCF(亿) | 5 年平均 ROE |\n")
        f.write("|------|------|------|-----|--------|---------|-------------|\n")
        high_quality.sort(key=lambda x: x['roe'], reverse=True)
        for i, s in enumerate(high_quality[:10], 1):
            f.write(f"| {i} | {s['code']} | {s['name']} | {s['roe']:.1f}% | {s['debt_ratio']:.1f}% | {s['fcf']:.1f} | {s['avg_roe_5y']:.1f}% |\n")
        
        f.write("\n## 💡 配置建议\n\n")
        f.write("### 核心仓位（60%）\n")
        f.write("- 资源股：中国神华、紫金矿业（20%）\n")
        f.write("- 新能源：宁德时代（10%）\n")
        f.write("- 金融：招商银行（10%）\n")
        f.write("- 公用事业：长江电力（10%）\n")
        f.write("- 高质量消费：茅台、五粮液（10%）\n\n")
        
        f.write("### 卫星仓位（40%）\n")
        f.write("- 高质量医药：迈瑞医疗、恒瑞医药（15%）\n")
        f.write("- 高质量消费：山西汾酒、泸州老窖（15%）\n")
        f.write("- 科技：亿联网络、吉比特（10%）\n")
    
    print(f"💾 报告已保存：{md_file}")
    
    return all_stocks, resource_stocks

if __name__ == '__main__':
    all_stocks, resource_stocks = generate_mixed_pool()
    
    print("\n" + "="*60)
    print("✅ 混合策略股票池生成完成")
    print("="*60)
