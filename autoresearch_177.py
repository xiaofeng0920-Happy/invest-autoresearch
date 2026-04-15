#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
177 支股票池 - 策略优化回测

基于 177 支股票财务数据，优化策略参数
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import time

sys.path.insert(0, '/home/admin/openclaw/workspace')

# Tushare
import tushare as ts
TS_TOKEN = '1dbdfba7c672d47f22db86f586d5aff9730124b321c2ebdda91890d3'
ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 数据目录
DATA_DIR = Path('/home/admin/openclaw/workspace/agents/data-collector/tushare_data')
CACHE_DIR = DATA_DIR / 'backtest_cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EXCEL_FILE = '/home/admin/.openclaw/media/inbound/177_æ_è_ç_5_å¹_è_å_æ_æ_é_è_è_20260329_0815---c213c27a-62e6-4e7a-bd67-bdf327ec8862.xlsx'

def load_177_pool():
    """加载 177 支股票池"""
    df = pd.read_excel(EXCEL_FILE, sheet_name='原始数据')
    
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
        })
    
    print(f"✅ 加载股票池：{len(stocks)} 只")
    return stocks

def select_stocks(stocks, min_roe, max_debt, min_fcf, min_roe_stability):
    """选股"""
    selected = []
    for s in stocks:
        if (s['roe'] > min_roe and 
            s['debt_ratio'] < max_debt and 
            s['fcf'] > min_fcf and 
            s['avg_roe_5y'] > min_roe_stability):
            selected.append(s)
    
    # 按 ROE 排序
    selected.sort(key=lambda x: x['roe'], reverse=True)
    return selected

def get_price_data(codes, start_date, end_date):
    """获取价格数据"""
    cache_file = CACHE_DIR / f'prices_{len(codes)}_{start_date}_{end_date}.json'
    
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    price_data = {}
    for i, code in enumerate(codes):
        try:
            df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                price_data[code] = {
                    'dates': df['trade_date'].tolist(),
                    'closes': df['close'].tolist(),
                }
            
            if (i + 1) % 5 == 0:
                time.sleep(0.1)  # 限流
        except Exception as e:
            print(f"  ❌ {code} 失败：{e}")
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(price_data, f, ensure_ascii=False)
    
    return price_data

def backtest(price_data, initial_capital=10_000_000):
    """回测"""
    if not price_data:
        return None
    
    # 找到共同交易日
    all_dates = set()
    for code, data in price_data.items():
        if all_dates:
            all_dates &= set(data['dates'])
        else:
            all_dates = set(data['dates'])
    
    if len(all_dates) < 252:
        return None
    
    all_dates = sorted(list(all_dates))
    date_idx = {d: i for i, d in enumerate(all_dates)}
    
    # 构建价格矩阵
    n_stocks = len(price_data)
    n_days = len(all_dates)
    
    prices = np.zeros((n_days, n_stocks))
    codes = list(price_data.keys())
    
    for j, code in enumerate(codes):
        data = price_data[code]
        for i, date in enumerate(data['dates']):
            if date in date_idx:
                prices[date_idx[date], j] = data['closes'][i]
    
    # 等权重组合
    weights = np.ones(n_stocks) / n_stocks
    
    # 计算收益
    returns = np.diff(prices, axis=0) / prices[:-1]
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # 绩效指标
    cumulative = np.cumprod(1 + portfolio_returns)
    total_return = cumulative[-1] - 1
    years = n_days / 252
    annual_return = (1 + total_return) ** (1/years) - 1
    volatility = portfolio_returns.std() * np.sqrt(252)
    sharpe = (annual_return - 0.02) / volatility if volatility > 0 else 0
    
    # 回撤
    cum_value = initial_capital * cumulative
    rolling_max = np.maximum.accumulate(cum_value)
    drawdown = (cum_value - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        'n_stocks': n_stocks,
        'n_days': n_days,
        'years': round(years, 2),
        'total_return': total_return,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
    }

def print_results(name, results):
    """打印结果"""
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"{'='*60}")
    print(f"持股数：{results['n_stocks']}只")
    print(f"回测期：{results['years']}年 ({results['n_days']}天)")
    print(f"年化收益：{results['annual_return']*100:.2f}%")
    print(f"夏普比率：{results['sharpe']:.4f}")
    print(f"最大回撤：{results['max_drawdown']*100:.2f}%")
    print(f"波动率：{results['volatility']*100:.2f}%")

def optimize_strategy(stocks):
    """优化策略参数"""
    print("\n" + "="*60)
    print("🔍 策略参数优化")
    print("="*60)
    
    # 参数网格
    roe_params = [15, 20, 25, 30]
    debt_params = [40, 50, 60]
    fcf_params = [0, 50]
    stability_params = [15, 20, 25]
    
    best_result = None
    best_params = None
    all_results = []
    
    # 日期范围（5 年）
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d')
    
    count = 0
    for min_roe in roe_params:
        for max_debt in debt_params:
            for min_fcf in fcf_params:
                for min_stability in stability_params:
                    count += 1
                    print(f"\n[{count}/{len(roe_params)*len(debt_params)*len(fcf_params)*len(stability_params)}] "
                          f"ROE>{min_roe}%, 负债<{max_debt}%, FCF>{min_fcf}亿，稳定>{min_stability}%")
                    
                    # 选股
                    selected = select_stocks(stocks, min_roe, max_debt, min_fcf, min_stability)
                    
                    if len(selected) < 5 or len(selected) > 25:
                        print(f"  ⚠️ 选股数量不合适：{len(selected)}只")
                        continue
                    
                    codes = [s['code'] for s in selected]
                    print(f"  ✅ 选股：{len(selected)}只")
                    
                    # 获取价格
                    price_data = get_price_data(codes, start_date, end_date)
                    
                    if not price_data:
                        print(f"  ❌ 价格数据获取失败")
                        continue
                    
                    # 回测
                    results = backtest(price_data)
                    
                    if results is None:
                        print(f"  ❌ 回测失败")
                        continue
                    
                    print(f"  📈 年化：{results['annual_return']*100:.2f}%, 夏普：{results['sharpe']:.4f}")
                    
                    all_results.append({
                        'params': {
                            'min_roe': min_roe,
                            'max_debt': max_debt,
                            'min_fcf': min_fcf,
                            'min_stability': min_stability,
                        },
                        'results': results,
                        'stocks': len(selected),
                    })
                    
                    # 更新最优
                    if best_result is None or results['sharpe'] > best_result['sharpe']:
                        best_result = results
                        best_params = {
                            'min_roe': min_roe,
                            'max_debt': max_debt,
                            'min_fcf': min_fcf,
                            'min_stability': min_stability,
                        }
    
    # 保存结果
    results_df = pd.DataFrame(all_results)
    results_file = DATA_DIR / '177 股策略优化结果.csv'
    results_df.to_csv(results_file, index=False)
    print(f"\n💾 结果已保存：{results_file}")
    
    # 打印最优
    if best_result:
        print("\n" + "="*60)
        print("🏆 最优策略参数")
        print("="*60)
        print(f"ROE > {best_params['min_roe']}%")
        print(f"负债率 < {best_params['max_debt']}%")
        print(f"FCF > {best_params['min_fcf']}亿")
        print(f"5 年平均 ROE > {best_params['min_stability']}%")
        print_results("最优策略", best_result)
    
    return best_params, best_result, all_results

def main():
    print("="*60)
    print("177 支股票池 - 策略优化回测")
    print("="*60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载股票池
    stocks = load_177_pool()
    
    # 优化策略
    best_params, best_result, all_results = optimize_strategy(stocks)
    
    # 保存最优配置
    if best_params:
        config_file = DATA_DIR / '177 股最优策略配置.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                'params': best_params,
                'results': best_result,
                'timestamp': datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 最优配置已保存：{config_file}")
    
    print("\n" + "="*60)
    print("✅ 优化完成")
    print("="*60)

if __name__ == '__main__':
    main()
