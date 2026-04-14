#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易策略 - AI Agent 自主修改

=== AI 可修改内容 ===
- 选股条件（ROE、毛利率、负债率阈值）
- 仓位配置（单只股票权重）
- 止损/止盈阈值
- 调仓频率
- 行业配置比例

=== 不可修改 ===
- 文件结构和接口
- backtest.py 调用方式
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class StrategyConfig:
    """策略配置 - AI 可修改"""
    
    # === 选股条件 ===
    min_roe: float = 10.0           # 最小 ROE%
    min_gross_margin: float = 20.0  # 最小毛利率%
    max_debt_ratio: float = 50.0    # 最大负债率% (实验：更稳健)
    min_revenue_growth: float = -20.0  # 最小营收增长率%
    
    # === 仓位配置 ===
    max_single_weight: float = 8.0  # 单只股票最大权重%
    target_position: float = 95.0   # 目标仓位%
    min_cash_ratio: float = 2.0     # 最小现金比例%
    
    # === 止损止盈 ===
    stop_loss: float = -10.0        # 止损线%
    take_profit: float = 40.0       # 止盈线%
    
    # === 调仓频率 ===
    rebalance_days: int = 5         # 调仓间隔（交易日）
    
    # === 行业配置 ===
    sector_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.sector_weights is None:
            self.sector_weights = {
                'energy': 22.0,
                'finance': 11.0,
                'consumer': 11.0,
                'healthcare': 9.0,
                'new_energy': 10.0,
                'utilities': 5.0,
            }

# 全局配置实例
CONFIG = StrategyConfig()

def generate_signals(stock_data: List[Dict]) -> List[str]:
    """
    生成交易信号
    
    Args:
        stock_data: 股票数据列表，每项包含：
            - code: 股票代码
            - name: 股票名称
            - roe: ROE%
            - gross_margin: 毛利率%
            - debt_ratio: 负债率%
            - revenue_growth: 营收增长率%
            - price: 当前价格
            - sector: 所属行业
    
    Returns:
        选中的股票代码列表
    """
    signals = []
    
    for stock in stock_data:
        # 巴菲特标准筛选
        if (stock.get('roe', 0) >= CONFIG.min_roe and
            stock.get('gross_margin', 0) >= CONFIG.min_gross_margin and
            stock.get('debt_ratio', 100) <= CONFIG.max_debt_ratio and
            stock.get('revenue_growth', -100) >= CONFIG.min_revenue_growth):
            signals.append(stock['code'])
    
    return signals

def calculate_weights(signals: List[str], stock_data: List[Dict]) -> Dict[str, float]:
    """
    计算仓位权重
    
    Args:
        signals: 选中的股票代码列表
        stock_data: 股票数据列表
    
    Returns:
        权重字典 {code: weight%}
    """
    if not signals:
        return {}
    
    n = len(signals)
    # 等权重分配
    base_weight = CONFIG.target_position / n
    
    weights = {}
    for code in signals:
        # 确保不超过单只股票最大权重
        weight = min(base_weight, CONFIG.max_single_weight)
        weights[code] = weight
    
    return weights

def should_stop_loss(current_return: float) -> bool:
    """判断是否止损"""
    return current_return <= CONFIG.stop_loss

def should_take_profit(current_return: float) -> bool:
    """判断是否止盈"""
    return current_return >= CONFIG.take_profit

def should_rebalance(days_since_last_rebalance: int) -> bool:
    """判断是否调仓"""
    return days_since_last_rebalance >= CONFIG.rebalance_days
