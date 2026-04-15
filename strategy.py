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
    min_roe: float = 15.0           # 最小 ROE% (V2: 从 7% 提高)
    # min_gross_margin: float = 20.0  # 最小毛利率% (去掉)
    max_debt_ratio: float = 60.0    # 最大负债率% (V2: 从 90% 降低)
    min_revenue_growth: float = -10.0  # 最小营收增长率%
    min_fcf: float = 0.0            # 最小自由现金流（亿）V2 新增
    min_roe_stability: float = 15.0  # 5 年平均 ROE% V2 新增
    
    # === 混合策略配置 ===
    use_mixed_pool: bool = True     # 使用混合股票池（31+5）V3 新增
    resource_stock_count: int = 5   # 资源股/周期股数量 V3 新增
    high_quality_count: int = 15    # 高质量股票数量 V3 新增
    
    # === 仓位配置 ===
    max_single_weight: float = 8.0  # 单只股票最大权重%
    target_position: float = 95.0   # 目标仓位%
    min_cash_ratio: float = 2.0     # 最小现金比例%
    
    # === 止损止盈 ===
    stop_loss: float = -10.0        # 止损线%
    take_profit: float = 40.0       # 止盈线%
    
    # === 调仓频率 ===
    rebalance_days: int = 3         # 调仓间隔（实验 4: 更频繁）
    
    # === 行业配置 ===
    sector_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.sector_weights is None:
            if self.use_mixed_pool:
                # V3 混合策略行业配置
                self.sector_weights = {
                    'resource': 20.0,      # 资源/煤炭/有色
                    'new_energy': 10.0,    # 新能源/电池
                    'finance': 10.0,       # 金融/银行
                    'utilities': 10.0,     # 公用事业/电力
                    'consumer': 25.0,      # 消费/白酒/食品
                    'healthcare': 15.0,    # 医药/器械
                    'tech': 10.0,          # 科技/游戏
                }
            else:
                # 原策略行业配置
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
    生成交易信号 - V3 混合策略
    
    Args:
        stock_data: 股票数据列表，每项包含：
            - code: 股票代码
            - name: 股票名称
            - roe: ROE%
            - debt_ratio: 负债率%
            - fcf: 自由现金流（亿）
            - avg_roe_5y: 5 年平均 ROE%
            - sector: 所属行业
    
    Returns:
        选中的股票代码列表
    """
    signals = []
    resource_stocks = []  # 资源股/周期股
    high_quality_stocks = []  # 高质量股票
    
    for stock in stock_data:
        sector = stock.get('sector', '')
        roe = stock.get('roe', stock.get('ROE', 0))
        debt_ratio = stock.get('debt_ratio', stock.get('资产负债率', 100))
        fcf = stock.get('fcf', stock.get('自由现金流', 0))
        avg_roe_5y = stock.get('avg_roe_5y', roe)
        
        # 判断是否资源股/周期股
        is_resource = sector in ['资源/煤炭', '资源/有色金属', '新能源/电池', '金融/银行', '公用事业/电力']
        
        if is_resource:
            # 资源股/周期股：直接加入（已预先筛选）
            resource_stocks.append(stock)
        else:
            # 高质量股票：多因子筛选
            revenue_growth = stock.get('revenue_growth', stock.get('营收增长率', -100))
            
            if (roe >= CONFIG.min_roe and
                debt_ratio <= CONFIG.max_debt_ratio and
                revenue_growth >= CONFIG.min_revenue_growth and
                fcf >= CONFIG.min_fcf and
                avg_roe_5y >= CONFIG.min_roe_stability):
                high_quality_stocks.append(stock)
    
    # V3 混合策略：资源股 + 高质量股票
    if CONFIG.use_mixed_pool:
        # 资源股全部保留
        for s in resource_stocks:
            signals.append(s['code'])
        
        # 高质量股票按 ROE 排序取前 N 只
        high_quality_stocks.sort(key=lambda x: x['roe'], reverse=True)
        for s in high_quality_stocks[:CONFIG.high_quality_count]:
            signals.append(s['code'])
    else:
        # 原策略：全部符合条件的股票
        for s in high_quality_stocks:
            signals.append(s['code'])
    
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
