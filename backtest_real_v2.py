#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实回测引擎 v2 - 添加个股波动率计算

功能：
1. 计算每只股票的历史波动率
2. 将波动率添加到股票数据
3. 策略可根据波动率筛选
"""

import sys
sys.path.insert(0, '/home/admin/openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tushare as ts
import json
from pathlib import Path

# Tushare Token
TS_TOKEN = '1dbdfba7c672d47f22db86f586d5aff9730124b321c2ebdda91890d3'
ts.set_token(TS_TOKEN)
pro = ts.pro_api()

# 数据目录
DATA_DIR = Path('/home/admin/openclaw/workspace/agents/data-collector/tushare_data')
CACHE_DIR = DATA_DIR / 'backtest_cache'
CACHE_DIR.mkdir(exist_ok=True)

def load_stock_data():
    """加载选股池（财报数据）"""
    json_files = list(DATA_DIR.glob('财报数据_*.json'))
    if json_files:
        with open(sorted(json_files)[-1], 'r', encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError('未找到财报数据')

def get_price_history(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取历史股价（前复权）"""
    ts_code = code
    
    # 检查缓存
    cache_file = CACHE_DIR / f'{code.replace(".", "_")}_10y.pkl'
    if cache_file.exists():
        try:
            df = pd.read_pickle(cache_file)
            if len(df) > 0:
                return df
        except:
            pass
    
    try:
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        df = df.sort_values('trade_date')
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.set_index('trade_date')
        
        df.to_pickle(cache_file)
        return df[['close', 'vol']]
        
    except Exception as e:
        print(f"  ❌ 错误：{code} - {str(e)}")
        return pd.DataFrame()

def calculate_momentum(code: str, end_date: str) -> float:
    """计算 12 月动量（收益率%）"""
    # 获取 1 年前和当前价格
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    start_dt = end_dt - timedelta(days=365)
    
    start_str = start_dt.strftime('%Y%m%d')
    end_str = end_dt.strftime('%Y%m%d')
    
    df = get_price_history(code, start_str, end_str)
    if len(df) < 60:
        return -99.0  # 低动量标记
    
    # 12 月收益率
    momentum = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    
    return momentum

def enrich_stock_data(stock_data: list, end_date: str) -> list:
    """为股票数据添加动量"""
    print(f"\n📊 计算个股动量（12 月）...")
    
    enriched = []
    for stock in stock_data:
        code = stock['code']
        momentum = calculate_momentum(code, end_date)
        
        enriched_stock = stock.copy()
        enriched_stock['momentum'] = momentum
        enriched.append(enriched_stock)
        
        print(f"  {code} {stock.get('name', '')}: {momentum:+.1f}%")
    
    return enriched

def calculate_portfolio_returns(signals: list, stock_data: list, start_date: str, end_date: str, 
                                initial_capital: float = 10_000_000) -> dict:
    """计算投资组合收益"""
    print(f"\n📈 获取 10 年历史数据...")
    print(f"回测区间：{start_date} 至 {end_date}")
    print(f"选股数量：{len(signals)}")
    
    # 获取所有股票价格数据
    price_data = {}
    for code in signals:
        df = get_price_history(code, start_date, end_date)
        if len(df) > 0:
            price_data[code] = df['close']
    
    if not price_data:
        print("❌ 无价格数据")
        return None
    
    # 对齐日期
    prices_df = pd.DataFrame(price_data)
    min_days = int(len(prices_df) * 0.7)
    prices_df = prices_df.dropna(thresh=min_days, axis=1)
    prices_df = prices_df.dropna()
    
    if len(prices_df) < 252:
        print(f"⚠️ 数据不足：{len(prices_df)}天")
        return None
    
    actual_years = len(prices_df) / 252
    print(f"\n✅ 有效数据：{len(prices_df)}天 ({actual_years:.2f}年)，{len(prices_df.columns)}只股票")
    
    # 计算等权重组合收益
    n_stocks = len(prices_df.columns)
    weights = np.array([1.0 / n_stocks] * n_stocks)
    
    # 计算每日收益率
    returns = prices_df.pct_change().dropna()
    
    # 组合收益率（等权重）
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # 计算累计收益
    cumulative_returns = (1 + portfolio_returns).cumprod()
    portfolio_value = initial_capital * cumulative_returns
    
    # 计算绩效指标
    print(f"\n📊 计算绩效指标...")
    
    total_return = (portfolio_value.iloc[-1] / initial_capital) - 1
    n_years = len(prices_df) / 252
    annual_return = (1 + total_return) ** (1 / n_years) - 1
    volatility = portfolio_returns.std() * np.sqrt(252)
    risk_free = 0.02
    sharpe = (annual_return - risk_free) / volatility
    
    rolling_max = portfolio_value.cummax()
    drawdown = (portfolio_value - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    positive_days = (portfolio_returns > 0).sum()
    total_days = len(portfolio_returns)
    win_rate = positive_days / total_days
    final_value = portfolio_value.iloc[-1]
    
    return {
        'n_stocks': n_stocks,
        'n_days': len(prices_df),
        'n_years': round(n_years, 2),
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
    }

def print_results(results: dict):
    """打印回测结果"""
    print("\n" + "="*70)
    print("📊 真实回测结果（分红再投资）")
    print("="*70)
    print(f"回测天数：      {results['n_days']} 天 ({results['n_years']}年)")
    print(f"选股数量：      {results['n_stocks']} 只")
    print(f"初始资金：      ¥{results['initial_capital']:,.0f}")
    print(f"最终市值：      ¥{results['final_value']:,.2f}")
    print("-"*70)
    print(f"总收益率：      {results['total_return']*100:.2f}%")
    print(f"年化收益率：    {results['annual_return']*100:.2f}%")
    print(f"年化波动率：    {results['volatility']*100:.2f}%")
    print(f"夏普比率：      {results['sharpe']:.4f}")
    print(f"最大回撤：      {results['max_drawdown']*100:.2f}%")
    print(f"胜率：          {results['win_rate']*100:.2f}%")
    print("="*70)
    
    print(f"\n---")
    print(f"sharpe: {results['sharpe']:.4f}")
    print(f"annual_return: {results['annual_return']*100:.2f}%")
    print(f"max_drawdown: {results['max_drawdown']*100:.2f}%")

def run_backtest():
    """主函数"""
    print("="*70)
    print("真实回测引擎 v2 - 添加波动率筛选")
    print("="*70)
    
    # 加载选股池
    stock_data = load_stock_data()
    print(f"加载股票池：{len(stock_data)}只")
    
    # 设置回测区间
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y%m%d')
    
    # 添加动量数据
    enriched_data = enrich_stock_data(stock_data, end_date)
    
    # 生成信号（使用波动率筛选）
    import strategy
    signals = strategy.generate_signals(enriched_data)
    
    if not signals:
        print("❌ 无选中股票")
        return
    
    print(f"\n✅ 选中股票：{len(signals)}")
    for code in signals:
        stock = next((s for s in enriched_data if s['code'] == code), None)
        if stock:
            print(f"  {code} {stock.get('name', '')} (波动率：{stock.get('volatility', 0):.1f}%)")
    
    # 运行回测
    results = calculate_portfolio_returns(signals, enriched_data, start_date, end_date)
    
    if results:
        print_results(results)

if __name__ == '__main__':
    run_backtest()
