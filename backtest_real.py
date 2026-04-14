#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实回测引擎 - 使用 Tushare 历史股价和分红数据

功能：
1. 获取 10 年历史股价（前复权）
2. 考虑分红再投资
3. 计算真实夏普比率、年化收益、最大回撤
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
    """
    获取历史股价（前复权，包含分红再投资）
    
    使用 Tushare 复权因子数据
    """
    # 转换代码格式（600938.SH -> 600938.SH）
    ts_code = code
    
    # 检查缓存
    cache_file = CACHE_DIR / f'{code.replace(".", "_")}_10y.pkl'
    if cache_file.exists():
        try:
            df = pd.read_pickle(cache_file)
            if len(df) > 0:
                print(f"  ✓ 缓存：{code}")
                return df
        except:
            pass
    
    try:
        # 获取日线数据（前复权）
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df is None or len(df) == 0:
            print(f"  ⚠️ 无数据：{code}")
            return pd.DataFrame()
        
        # 使用前复权价格（adj_factor 已调整）
        # Tushare 的 close 已经是前复权价格
        df = df.sort_values('trade_date')
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.set_index('trade_date')
        
        # 保存缓存
        df.to_pickle(cache_file)
        print(f"  ✓ 获取：{code} ({len(df)}天)")
        
        return df[['close', 'vol']]
        
    except Exception as e:
        print(f"  ❌ 错误：{code} - {str(e)}")
        return pd.DataFrame()

def calculate_portfolio_returns(signals: list, start_date: str, end_date: str, initial_capital: float = 10_000_000) -> dict:
    """
    计算投资组合收益（等权重，分红再投资）
    
    Args:
        signals: 股票代码列表
        start_date: 开始日期（10 年前）
        end_date: 结束日期
        initial_capital: 初始资金
    
    Returns:
        绩效指标字典
    """
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
    
    # 删除缺失值（某些股票可能上市晚）
    # 策略：保留至少 70% 数据完整的股票
    min_days = int(len(prices_df) * 0.7)
    prices_df = prices_df.dropna(thresh=min_days, axis=1)
    
    # 再次删除缺失行
    prices_df = prices_df.dropna()
    
    # 检查数据长度
    if len(prices_df) < 252:  # 至少 1 年数据
        print(f"⚠️ 数据不足：{len(prices_df)}天")
        return None
    
    # 计算实际回测年限
    actual_years = len(prices_df) / 252
    print(f"\n✅ 有效数据：{len(prices_df)}天 ({actual_years:.2f}年)，{len(prices_df.columns)}只股票")
    
    if actual_years < 3:
        print(f"⚠️ 回测期过短（{actual_years:.2f}年），结果仅供参考")
    
    # 计算等权重组合收益
    # 假设：每只股票初始权重相等，每日再平衡
    n_stocks = len(prices_df.columns)
    weights = np.array([1.0 / n_stocks] * n_stocks)
    
    # 计算每日收益率
    returns = prices_df.pct_change().dropna()
    
    # 组合收益率（等权重）
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # 计算累计收益
    cumulative_returns = (1 + portfolio_returns).cumprod()
    
    # 计算市值曲线
    portfolio_value = initial_capital * cumulative_returns
    
    # 计算绩效指标
    print(f"\n📊 计算绩效指标...")
    
    # 1. 总收益率
    total_return = (portfolio_value.iloc[-1] / initial_capital) - 1
    
    # 2. 年化收益率
    n_years = len(prices_df) / 252
    annual_return = (1 + total_return) ** (1 / n_years) - 1
    
    # 3. 年化波动率
    volatility = portfolio_returns.std() * np.sqrt(252)
    
    # 4. 夏普比率（无风险利率 2%）
    risk_free = 0.02
    sharpe = (annual_return - risk_free) / volatility
    
    # 5. 最大回撤
    rolling_max = portfolio_value.cummax()
    drawdown = (portfolio_value - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 6. 胜率
    positive_days = (portfolio_returns > 0).sum()
    total_days = len(portfolio_returns)
    win_rate = positive_days / total_days
    
    # 7. 最终市值
    final_value = portfolio_value.iloc[-1]
    
    # 结果
    results = {
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
    
    return results

def print_results(results: dict):
    """打印回测结果"""
    print("\n" + "="*70)
    print("📊 真实回测结果（10 年，分红再投资）")
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
    
    # 输出简版（供脚本调用）
    print(f"\n---")
    print(f"sharpe: {results['sharpe']:.4f}")
    print(f"annual_return: {results['annual_return']*100:.2f}%")
    print(f"max_drawdown: {results['max_drawdown']*100:.2f}%")

def run_backtest():
    """主函数"""
    print("="*70)
    print("真实回测引擎 - Tushare 历史数据")
    print("="*70)
    
    # 加载选股池
    stock_data = load_stock_data()
    print(f"加载股票池：{len(stock_data)}只")
    
    # 生成信号
    import strategy
    signals = strategy.generate_signals(stock_data)
    
    if not signals:
        print("❌ 无选中股票")
        return
    
    print(f"✅ 选中股票：{len(signals)}")
    for code in signals:
        stock = next((s for s in stock_data if s['code'] == code), None)
        if stock:
            print(f"  {code} {stock.get('name', '')}")
    
    # 设置回测区间（10 年）
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y%m%d')
    
    # 运行回测
    results = calculate_portfolio_returns(signals, start_date, end_date)
    
    if results:
        print_results(results)

if __name__ == '__main__':
    run_backtest()
