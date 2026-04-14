# 投资版 Autoresearch - 自主策略优化系统

## 🎯 核心理念

**参考 karpathy/autoresearch 设计，应用于量化投资：**

- AI Agent 自主修改交易策略
- 每次回测固定时间预算（1 个交易日数据）
- 评估指标：夏普比率/收益率（越高越好）
- 人类只修改 `program.md`（投资约束）

---

## 📁 项目结构

```
invest-autoresearch/
├── program.md          # AI Agent 指令（人类修改）
├── strategy.py         # 交易策略代码（AI 修改）⭐
├── backtest.py         # 回测引擎（固定）
├── data.py             # 数据加载（固定）
├── results.tsv         # 实验结果记录
└── logs/               # 实验日志
```

---

## 🔧 核心文件设计

### 1. strategy.py（AI 修改）

```python
#!/usr/bin/env python3
"""
交易策略 - AI Agent 自主修改

可修改内容：
- 选股条件（ROE、毛利率、负债率阈值）
- 仓位配置（单只股票权重）
- 止损/止盈阈值
- 调仓频率
- 行业配置比例
"""

# === AI 可修改的参数 ===
STRATEGY_CONFIG = {
    # 选股条件
    'min_roe': 10.0,           # 最小 ROE%
    'min_gross_margin': 20.0,  # 最小毛利率%
    'max_debt_ratio': 60.0,    # 最大负债率%
    
    # 仓位配置
    'max_single_weight': 8.0,  # 单只股票最大权重%
    'target_position': 95.0,   # 目标仓位%
    
    # 止损止盈
    'stop_loss': -10.0,        # 止损线%
    'take_profit': 40.0,       # 止盈线%
    
    # 调仓频率
    'rebalance_days': 5,       # 调仓间隔（交易日）
    
    # 行业配置
    'sector_weights': {
        'energy': 22.0,
        'finance': 11.0,
        'consumer': 11.0,
        'healthcare': 9.0,
        'new_energy': 10.0,
        'utilities': 5.0,
    }
}

def generate_signals(data):
    """生成交易信号 - AI 可修改逻辑"""
    # AI 可以修改这里的选股逻辑
    signals = []
    for stock in data:
        if (stock['roe'] > STRATEGY_CONFIG['min_roe'] and
            stock['gross_margin'] > STRATEGY_CONFIG['min_gross_margin'] and
            stock['debt_ratio'] < STRATEGY_CONFIG['max_debt_ratio']):
            signals.append(stock['code'])
    return signals

def calculate_weights(signals, config):
    """计算仓位权重 - AI 可修改逻辑"""
    # AI 可以修改这里的权重分配逻辑
    n = len(signals)
    base_weight = STRATEGY_CONFIG['target_position'] / n
    weights = {code: base_weight for code in signals}
    return weights
```

---

### 2. backtest.py（固定）

```python
#!/usr/bin/env python3
"""
回测引擎 - 固定不变

功能：
1. 加载历史数据
2. 调用 strategy.py 生成信号
3. 模拟交易执行
4. 计算绩效指标
5. 输出结果
"""

import strategy
from data import load_data, get_price_data

def run_backtest(start_date, end_date, initial_capital=10_000_000):
    """运行回测"""
    
    # 加载数据
    data = load_data(start_date, end_date)
    
    # 初始化
    cash = initial_capital
    positions = {}
    daily_values = []
    
    # 按交易日循环
    for date in get_trading_dates(start_date, end_date):
        # 获取当日数据
        day_data = get_price_data(date)
        
        # 生成交易信号
        signals = strategy.generate_signals(day_data)
        
        # 计算权重
        weights = strategy.calculate_weights(signals, strategy.STRATEGY_CONFIG)
        
        # 执行调仓
        positions, cash = rebalance(positions, cash, weights, day_data)
        
        # 计算当日市值
        total_value = cash + sum(
            positions.get(code, 0) * day_data[code]['price']
            for code in positions
        )
        daily_values.append(total_value)
    
    # 计算绩效指标
    returns = calculate_returns(daily_values)
    sharpe = calculate_sharpe(returns)
    max_drawdown = calculate_max_drawdown(daily_values)
    total_return = (daily_values[-1] - initial_capital) / initial_capital
    
    return {
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'total_return': total_return,
        'final_value': daily_values[-1],
    }

if __name__ == '__main__':
    result = run_backtest('2025-01-01', '2026-04-14')
    print(f"sharpe: {result['sharpe']:.4f}")
    print(f"max_drawdown: {result['max_drawdown']:.4f}")
    print(f"total_return: {result['total_return']:.4f}")
    print(f"final_value: {result['final_value']:.2f}")
```

---

### 3. program.md（人类修改）

```markdown
# 投资版 Autoresearch - AI Agent 指令

## 目标

自主优化交易策略，最大化**夏普比率**（风险调整后收益）。

## 约束条件

### 不可修改
- `backtest.py` - 回测引擎固定
- `data.py` - 数据加载固定
- 初始资金：10,000,000 CNY
- 回测周期：2025-01-01 至 2026-04-14

### 可以修改
- `strategy.py` - 唯一可修改文件
- 选股条件（ROE、毛利率、负债率阈值）
- 仓位配置（权重分配逻辑）
- 止损/止盈阈值
- 调仓频率

### 禁止行为
- 使用未来函数（不能使用当日收盘价决定当日交易）
- 过度拟合（参数调整需有逻辑支撑）
- 单只股票权重超过 10%

## 实验流程

### 1. 基线实验
首次运行使用当前策略参数，建立基准：
- 夏普比率：___
- 总收益率：___
- 最大回撤：___

### 2. 迭代优化
每次实验尝试一个改进方向：
1. 修改 `strategy.py` 中的一个参数或逻辑
2. 运行回测：`python3 backtest.py`
3. 记录结果到 `results.tsv`
4. 如果夏普比率提升 → 保留修改
5. 如果夏普比率下降 → 撤销修改

### 3. 实验记录
格式（TSV）：
```
commit	sharpe	total_return	max_dd	status	description
a1b2c3d	1.2345	0.0487	-0.0823	keep	baseline
b2c3d4e	1.2567	0.0512	-0.0798	keep	提高 ROE 阈值到 15%
c3d4e5f	1.2123	0.0445	-0.0856	discard	降低仓位到 80%
```

## 优化方向建议

### 选股条件
- 调整 ROE 阈值（当前 10%）
- 调整毛利率阈值（当前 20%）
- 调整负债率阈值（当前 60%）
- 添加新的筛选条件（如营收增长率）

### 仓位配置
- 调整单只股票最大权重（当前 8%）
- 调整目标仓位（当前 95%）
- 修改权重分配逻辑（等权 vs 市值加权）

### 止损止盈
- 调整止损线（当前 -10%）
- 调整止盈线（当前 +40%）
- 添加动态止损逻辑

### 调仓频率
- 调整调仓间隔（当前 5 天）
- 添加条件触发调仓

## 评估标准

**主要指标：** 夏普比率（越高越好）
**次要指标：** 总收益率、最大回撤

**简单性原则：** 同等表现下，选择更简单的策略。
```

---

## 🔄 实验循环

```
LOOP FOREVER:
1. 查看当前 git 状态
2. 修改 strategy.py（一个实验想法）
3. git commit
4. 运行回测：python3 backtest.py > run.log 2>&1
5. 读取结果：grep "^sharpe:" run.log
6. 如果结果为空 → 运行失败，查看错误日志
7. 记录结果到 results.tsv
8. 如果夏普比率提升 → 保留 commit
9. 如果夏普比率下降 → git reset 回退
```

---

## 📊 预期效果

**假设每轮实验 10 分钟：**
- 1 小时：6 次实验
- 一晚（8 小时）：48 次实验
- 一周：336 次实验

**预期优化空间：**
- 基线夏普比率：1.2-1.5
- 优化后目标：1.5-2.0
- 年化收益提升：5-10%

---

## 🚀 快速开始

```bash
# 1. 创建项目
mkdir invest-autoresearch
cd invest-autoresearch

# 2. 创建文件
# - strategy.py（策略代码）
# - backtest.py（回测引擎）
# - data.py（数据加载）
# - program.md（AI 指令）

# 3. 初始化 git
git init
git add .
git commit -m "initial commit"

# 4. 创建实验分支
git checkout -b invest-autoresearch/apr14

# 5. 运行基线实验
python3 backtest.py

# 6. 开始自主优化
# AI Agent 根据 program.md 自主迭代
```

---

## 💡 与 karpathy/autoresearch 对比

| 维度 | karpathy | 投资版 |
|------|----------|--------|
| **实验对象** | LLM 训练 | 交易策略 |
| **时间预算** | 5 分钟/次 | 10 分钟/次 |
| **评估指标** | val_bpb（越低越好） | 夏普比率（越高越好） |
| **修改文件** | train.py | strategy.py |
| **人类指令** | program.md | program.md |
| **预期迭代** | 100 次/晚 | 48 次/晚 |

---

*设计完成时间：2026-04-14*
*参考：karpathy/autoresearch*
