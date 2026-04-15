#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测 v2 - 基于 177 支股票池

对比：
- 原策略（9 只）：ROE>7%, 负债<90%
- 新策略（20 只）：ROE>15%, 负债<60%, FCF>0, 5 年平均 ROE>15%
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Dict

sys.path.insert(0, '/home/admin/openclaw/workspace')

# Tushare
import tushare as ts
TS_TOKEN = '1dbdfba7c672d47f22db86f586d5aff9730124b321c2ebdda91890d3'
ts.set_token(TS_TOKEN)
pro = ts.pro_api()

DATA_DIR = Path('/home/admin/openclaw/workspace/agents/data-collector/tushare_data')

def load_177_stock_pool():
    """加载 177 支股票池"""
    excel_file = '/home/admin/.openclaw/media/inbound/177_æ_è_ç_5_å¹_è_å_æ_æ_é_è_è_20260329_0815---c213c27a-62e6-4e7a-bd67-bdf327ec8862.xlsx'
    df = pd.read_excel(excel_file, sheet_name='原始数据')
    
    # 计算 5 年平均 ROE
    avg_roe = df.groupby('股票名称')['ROE'].mean().reset_index()
    avg_roe.columns = ['股票名称', 'avg_roe_5y']
    
    # 获取 2024 年数据
    df_2024 = df[df['年份'] == 2024].merge(avg_roe, on='股票名称')
    
    # 转换格式
    stocks = []
    for _, row in df_2024.iterrows():
        stocks.append({
            'code': row['股票代码'],
            'name': row['股票名称'],
            'roe': row['ROE'],
            'debt_ratio': row['负债率'],
            'revenue_growth': 0,  # 简化
            'fcf': row['自由现金流'],
            'avg_roe_5y': row['avg_roe_5y'],
        })
    
    print(f"✅ 加载股票池：{len(stocks)} 只")
    return stocks

def select_stocks_old_strategy(stocks):
    """原策略选股（ROE>7%, 负债<90%）"""
    selected = []
    for s in stocks:
        if s['roe'] > 7 and s['debt_ratio'] < 90:
            selected.append(s)
    return selected[:9]  # 限制 9 只

def select_stocks_new_strategy(stocks):
    """新策略选股（ROE>15%, 负债<60%, FCF>0, 5 年平均 ROE>15%）"""
    selected = []
    for s in stocks:
        if (s['roe'] > 15 and 
            s['debt_ratio'] < 60 and 
            s['fcf'] > 0 and 
            s['avg_roe_5y'] > 15):
            selected.append(s)
    
    # 按 ROE 排序取前 20
    selected.sort(key=lambda x: x['roe'], reverse=True)
    return selected[:20]

def get_price_data(codes: List[str], start: str, end: str) -> Dict:
    """获取价格数据"""
    print(f"📈 获取 {len(codes)} 只股票价格数据...")
    
    price_data = {}
    for code in codes:
        try:
            df = pro.daily(ts_code=code, start_date=start, end_date=end)
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date')
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.set_index('trade_date')
                price_data[code] = df['close']
        except:
            pass
    
    return price_data

def backtest_portfolio(price_data: Dict, initial_capital: float = 10_000_000):
    """回测组合收益"""
    if not price_data:
        return None
    
    # 对齐日期
    prices_df = pd.DataFrame(price_data)
    prices_df = prices_df.dropna(thresh=int(len(prices_df)*0.7))
    prices_df = prices_df.dropna()
    
    if len(prices_df) < 252:
        print(f"⚠️ 数据不足：{len(prices_df)}天")
        return None
    
    # 等权重组合
    n = len(prices_df.columns)
    weights = np.array([1.0/n] * n)
    
    # 计算收益
    returns = prices_df.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # 绩效指标
    cumulative = (1 + portfolio_returns).cumprod()
    total_return = cumulative.iloc[-1] - 1
    years = len(prices_df) / 252
    annual_return = (1 + total_return) ** (1/years) - 1
    volatility = portfolio_returns.std() * np.sqrt(252)
    sharpe = (annual_return - 0.02) / volatility
    
    # 回撤
    cum_value = initial_capital * cumulative
    rolling_max = cum_value.cummax()
    drawdown = (cum_value - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        'n_stocks': n,
        'n_days': len(prices_df),
        'years': round(years, 2),
        'total_return': total_return,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
    }

def print_results(name: str, results: Dict):
    """打印回测结果"""
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"{'='*60}")
    print(f"持股数：{results['n_stocks']}只")
    print(f"回测期：{results['years']}年 ({results['n_days']}天)")
    print(f"年化收益：{results['annual_return']*100:.2f}%")
    print(f"夏普比率：{results['sharpe']:.4f}")
    print(f"最大回撤：{results['max_drawdown']*100:.2f}%")
    print(f"波动率：{results['volatility']*100:.2f}%")

def main():
    print("="*60)
    print("策略对比回测 - 177 支股票池")
    print("="*60)
    
    # 加载股票池
    stocks = load_177_stock_pool()
    
    # 选股
    print("\n📋 原策略选股（ROE>7%, 负债<90%）:")
    old_stocks = select_stocks_old_strategy(stocks)
    for s in old_stocks:
        print(f"  {s['code']} {s['name']} ROE:{s['roe']:.1f}% 负债:{s['debt_ratio']:.1f}%")
    
    print("\n📋 新策略选股（ROE>15%, 负债<60%, FCF>0）:")
    new_stocks = select_stocks_new_strategy(stocks)
    for s in new_stocks:
        print(f"  {s['code']} {s['name']} ROE:{s['roe']:.1f}% 负债:{s['debt_ratio']:.1f}% 5 年平均:{s['avg_roe_5y']:.1f}%")
    
    # 获取价格数据（5 年）
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - pd.Timedelta(days=365*5)).strftime('%Y%m%d')
    
    old_codes = [s['code'] for s in old_stocks]
    new_codes = [s['code'] for s in new_stocks]
    
    old_prices = get_price_data(old_codes, start_date, end_date)
    new_prices = get_price_data(new_codes, start_date, end_date)
    
    # 回测
    old_results = backtest_portfolio(old_prices)
    new_results = backtest_portfolio(new_prices)
    
    # 对比
    if old_results and new_results:
        print_results("原策略（9 只）", old_results)
        print_results("新策略（20 只）", new_results)
        
        print(f"\n{'='*60}")
        print("📈 策略对比")
        print(f"{'='*60}")
        print(f"年化提升：{(new_results['annual_return']-old_results['annual_return'])*100:+.2f}%")
        print(f"夏普提升：{new_results['sharpe']-old_results['sharpe']:+.4f}")
        print(f"回撤改善：{(new_results['max_drawdown']-old_results['max_drawdown'])*100:+.2f}%")

if __name__ == '__main__':
    main()
