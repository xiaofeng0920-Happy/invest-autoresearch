#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 - 固定不变

功能：
1. 加载历史数据
2. 调用 strategy.py 生成信号
3. 模拟交易执行
4. 计算绩效指标
5. 输出结果

=== 不可修改 ===
"""

import sys
sys.path.insert(0, '/home/admin/openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

# 导入策略模块（AI 会修改这个文件）
import strategy

# 数据目录
DATA_DIR = Path('/home/admin/openclaw/workspace/agents/data-collector/tushare_data')

def load_stock_data() -> list:
    """加载股票财务数据"""
    # 读取最新的财报数据
    json_files = list(DATA_DIR.glob('财报数据_*.json'))
    if not json_files:
        print("⚠️ 未找到财报数据，运行 financial_report_tushare.py 获取")
        return []
    
    latest_file = sorted(json_files)[-1]
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def load_price_history(code: str, days: int = 252) -> pd.DataFrame:
    """加载历史股价数据（简化版，实际应从数据源获取）"""
    # 这里用模拟数据，实际应从数据库或 API 获取
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    np.random.seed(hash(code) % 2**32)
    
    # 生成随机股价走势（简化）
    base_price = np.random.uniform(10, 500)
    returns = np.random.normal(0.0005, 0.02, days)  # 年化收益 12.5%，波动 32%
    prices = base_price * np.cumprod(1 + returns)
    
    return pd.DataFrame({
        'date': dates,
        'close': prices,
        'code': code
    })

def run_backtest(start_date: str = '2025-01-01', 
                 end_date: str = '2026-04-14',
                 initial_capital: float = 10_000_000) -> dict:
    """
    运行回测
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
    
    Returns:
        回测结果字典
    """
    print("="*70)
    print("投资回测引擎")
    print("="*70)
    print(f"回测区间：{start_date} 至 {end_date}")
    print(f"初始资金：{initial_capital:,.2f} CNY")
    print("="*70)
    
    # 加载股票数据
    print("\n📊 加载股票数据...")
    stock_data = load_stock_data()
    if not stock_data:
        print("⚠️ 无股票数据，使用模拟数据")
        # 创建模拟数据
        stock_data = [
            {'code': '600938.SH', 'name': '中国海油', 'roe': 18.87, 'gross_margin': 53.63, 
             'debt_ratio': 29.05, 'revenue_growth': 0.94, 'sector': 'energy'},
            {'code': '601088.SH', 'name': '中国神华', 'roe': 14.39, 'gross_margin': 34.04,
             'debt_ratio': 23.42, 'revenue_growth': -1.37, 'sector': 'energy'},
            {'code': '601899.SH', 'name': '紫金矿业', 'roe': 25.63, 'gross_margin': 20.37,
             'debt_ratio': 55.19, 'revenue_growth': 3.49, 'sector': 'resources'},
            {'code': '300750.SZ', 'name': '宁德时代', 'roe': 20.24, 'gross_margin': 24.44,
             'debt_ratio': 65.24, 'revenue_growth': -9.70, 'sector': 'new_energy'},
            {'code': '002460.SZ', 'name': '赣锋锂业', 'roe': -2.00, 'gross_margin': 10.82,
             'debt_ratio': 52.80, 'revenue_growth': -42.66, 'sector': 'new_energy'},
            {'code': '600036.SH', 'name': '招商银行', 'roe': 12.86, 'gross_margin': 0,
             'debt_ratio': 89.85, 'revenue_growth': -0.48, 'sector': 'finance'},
            {'code': '601398.SH', 'name': '工商银行', 'roe': 9.43, 'gross_margin': 0,
             'debt_ratio': 91.83, 'revenue_growth': -2.52, 'sector': 'finance'},
            {'code': '600900.SH', 'name': '长江电力', 'roe': 15.79, 'gross_margin': 59.13,
             'debt_ratio': 60.79, 'revenue_growth': 8.12, 'sector': 'utilities'},
            {'code': '000858.SZ', 'name': '五粮液', 'roe': 24.15, 'gross_margin': 77.05,
             'debt_ratio': 27.55, 'revenue_growth': 7.09, 'sector': 'consumer'},
            {'code': '000333.SZ', 'name': '美的集团', 'roe': 18.83, 'gross_margin': 26.42,
             'debt_ratio': 62.33, 'revenue_growth': 9.44, 'sector': 'consumer'},
            {'code': '300760.SZ', 'name': '迈瑞医疗', 'roe': 33.19, 'gross_margin': 63.11,
             'debt_ratio': 28.04, 'revenue_growth': 5.14, 'sector': 'healthcare'},
            {'code': '603259.SH', 'name': '药明康德', 'roe': 17.56, 'gross_margin': 41.48,
             'debt_ratio': 26.44, 'revenue_growth': -2.73, 'sector': 'healthcare'},
        ]
    
    print(f"✓ 加载 {len(stock_data)} 只股票")
    
    # 生成交易日期
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    print(f"✓ 回测天数：{len(dates)} 交易日")
    
    # 初始化
    cash = initial_capital
    positions = {}  # {code: shares}
    daily_values = []
    last_rebalance_date = None
    days_since_rebalance = 0
    
    print("\n📈 开始回测...")
    
    for i, date in enumerate(dates):
        date_str = date.strftime('%Y-%m-%d')
        
        # 判断是否需要调仓
        if last_rebalance_date is None or days_since_rebalance >= strategy.CONFIG.rebalance_days:
            # 生成交易信号
            signals = strategy.generate_signals(stock_data)
            
            if signals:
                # 计算权重
                weights = strategy.calculate_weights(signals, stock_data)
                
                # 执行调仓（简化：假设按收盘价成交）
                # 实际应获取当日收盘价
                positions = {}
                total_weight = sum(weights.values())
                
                for code, weight in weights.items():
                    # 找到股票数据
                    stock = next((s for s in stock_data if s['code'] == code), None)
                    if stock:
                        # 简化：使用固定价格模拟
                        price = np.random.uniform(50, 500)
                        target_value = cash * (weight / 100)
                        shares = int(target_value / price)
                        if shares > 0:
                            positions[code] = shares
                            cash -= shares * price
                
                last_rebalance_date = date
                days_since_rebalance = 0
        
        days_since_rebalance += 1
        
        # 计算当日市值（简化：随机波动）
        portfolio_value = cash
        for code, shares in positions.items():
            # 简化：使用随机价格模拟
            np.random.seed(hash(code + date_str) % 2**32)
            price = np.random.uniform(50, 500)
            portfolio_value += shares * price
        
        daily_values.append(portfolio_value)
        
        # 进度显示
        if (i + 1) % 50 == 0:
            print(f"  进度：{i+1}/{len(dates)} 天，当前市值：{portfolio_value:,.2f}")
    
    # 计算绩效指标
    print("\n📊 计算绩效指标...")
    
    final_value = daily_values[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # 计算日收益率
    daily_returns = np.diff(daily_values) / daily_values[:-1]
    
    # 夏普比率（假设无风险利率 3%）
    risk_free_rate = 0.03 / 252
    excess_returns = daily_returns - risk_free_rate
    if len(excess_returns) > 0 and np.std(excess_returns) > 0:
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    else:
        sharpe = 0
    
    # 最大回撤
    peak = np.maximum.accumulate(daily_values)
    drawdown = (daily_values - peak) / peak
    max_drawdown = np.min(drawdown)
    
    # 年化收益率
    years = len(dates) / 252
    annual_return = (final_value / initial_capital) ** (1 / years) - 1
    
    # 胜率
    winning_days = sum(1 for r in daily_returns if r > 0)
    win_rate = winning_days / len(daily_returns) if len(daily_returns) > 0 else 0
    
    results = {
        'sharpe': sharpe,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'final_value': final_value,
        'win_rate': win_rate,
        'trading_days': len(dates),
    }
    
    # 输出结果
    print("\n" + "="*70)
    print("📊 回测结果")
    print("="*70)
    print(f"最终市值：    {final_value:>15,.2f} CNY")
    print(f"总收益率：    {total_return:>15.2%}")
    print(f"年化收益率：  {annual_return:>15.2%}")
    print(f"夏普比率：    {sharpe:>15.4f}")
    print(f"最大回撤：    {max_drawdown:>15.2%}")
    print(f"胜率：        {win_rate:>15.2%}")
    print(f"交易天数：    {len(dates):>15} 天")
    print("="*70)
    
    # 输出为机器可读格式
    print("\n---")
    print(f"sharpe: {sharpe:.4f}")
    print(f"total_return: {total_return:.4f}")
    print(f"max_drawdown: {max_drawdown:.4f}")
    print(f"final_value: {final_value:.2f}")
    
    return results

if __name__ == '__main__':
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        start = sys.argv[1]
        end = sys.argv[2] if len(sys.argv) > 2 else '2026-04-14'
    else:
        start = '2025-01-01'
        end = '2026-04-14'
    
    results = run_backtest(start, end)
