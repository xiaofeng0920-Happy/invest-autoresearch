#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略配置 v2 - 基于 177 支股票池优化

优化方向：
1. 使用 31 只高质量股票池
2. ROE 阈值提高到 15%（原 7%）
3. 负债率上限降低到 60%（原 90%）
4. 添加 ROE 稳定性要求
5. 添加自由现金流要求
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import json

@dataclass
class StrategyConfig:
    # === 选股条件 ===
    min_roe: float = 15.0           # 最小 ROE%（从 7% 提高到 15%）
    max_debt_ratio: float = 60.0    # 最大负债率%（从 90% 降低到 60%）
    min_revenue_growth: float = -10.0  # 最小营收增长率%
    min_fcf: float = 0.0            # 最小自由现金流（亿）✅ 新增
    min_roe_stability: float = 15.0  # 5 年平均 ROE 最小值 ✅ 新增
    
    # === 仓位配置 ===
    max_single_weight: float = 0.05  # 单只股票最大权重 5%
    max_industry_weight: float = 0.25  # 单行业最大权重 25%
    target_stock_count: int = 20    # 目标持股数量
    
    # === 调仓频率 ===
    rebalance_days: int = 3         # 每 3 天调仓一次
    
    # === 止损/止盈 ===
    stop_loss: float = -0.15        # 止损线 -15%
    take_profit: float = 0.40       # 止盈线 +40%


def generate_signals(stock_data: List[Dict[str, Any]]) -> List[str]:
    """
    生成买入信号
    
    Args:
        stock_data: 股票数据列表，包含代码、名称、ROE、负债率等
    
    Returns:
        选中的股票代码列表
    """
    signals = []
    
    for stock in stock_data:
        # 获取财务指标
        roe = stock.get('roe', stock.get('ROE', 0))
        debt_ratio = stock.get('debt_ratio', stock.get('负债率', 100))
        revenue_growth = stock.get('revenue_growth', stock.get('营收增长率', -100))
        fcf = stock.get('fcf', stock.get('自由现金流', 0))
        avg_roe_5y = stock.get('avg_roe_5y', roe)  # 5 年平均 ROE
        
        # 核心筛选条件
        if (roe >= CONFIG.min_roe and
            debt_ratio <= CONFIG.max_debt_ratio and
            revenue_growth >= CONFIG.min_revenue_growth and
            fcf >= CONFIG.min_fcf and
            avg_roe_5y >= CONFIG.min_roe_stability):
            signals.append(stock['code'])
    
    # 限制股票数量
    if len(signals) > CONFIG.target_stock_count:
        # 按 ROE 排序，取前 N 只
        stock_map = {s['code']: s for s in stock_data}
        signals.sort(key=lambda x: stock_map[x].get('roe', 0), reverse=True)
        signals = signals[:CONFIG.target_stock_count]
    
    return signals


# 全局配置实例
CONFIG = StrategyConfig()


if __name__ == '__main__':
    # 测试配置
    print("策略配置 v2 - 基于 177 支股票池")
    print("="*50)
    print(f"ROE 阈值：> {CONFIG.min_roe}%")
    print(f"负债率上限：< {CONFIG.max_debt_ratio}%")
    print(f"5 年平均 ROE: > {CONFIG.min_roe_stability}%")
    print(f"自由现金流：> {CONFIG.min_fcf}亿")
    print(f"目标持股数：{CONFIG.target_stock_count}只")
    print(f"单只上限：{CONFIG.max_single_weight*100}%")
    print(f"行业上限：{CONFIG.max_industry_weight*100}%")
