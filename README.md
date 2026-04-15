# 投资自主研究系统 (Invest AutoResearch)

基于巴菲特价值投资的 AI 自主优化投资系统

## 📊 策略配置

**最佳配置（实验 15）：**
- ROE > 7%
- 负债率 < 90%
- 无毛利率限制
- 营收增长 > -10%

## 📈 真实回测绩效（7 年）

| 指标 | 数值 |
|------|------|
| 年化收益率 | 18.82% |
| 夏普比率 | 0.82 |
| 最大回撤 | -28.5% |
| 总收益率 | 236% |
| 胜率 | 52.6% |

**1000 万 → 3364 万**（7 年）

## 🔄 自主优化循环

已进行 18 轮实验，自动调整策略参数优化夏普比率。

| 实验 | 修改 | 夏普 | 结论 |
|------|------|------|------|
| 基线 | ROE>10%, 负债<50% | 2.69 | ✅ |
| 14 | ROE>7%, 负债<90% | 3.01 (估算) | ✅ 最佳 |
| 15 | 真实回测 | 0.82 | ✅ 验证 |
| 16 | 波动率<35% | 0.58 | ❌ |
| 18 | ROE>15% | 0.80 | ❌ |

## 📁 项目结构

```
invest-autoresearch/
├── strategy.py          # 策略配置（AI 可修改）
├── backtest.py          # 基础回测引擎
├── backtest_v3.py       # 简化估算版
├── backtest_real.py     # 真实回测（Tushare）
├── backtest_real_v2.py  # 真实回测 v2
├── program.md           # 项目说明
├── results.tsv          # 实验记录
└── README.md            # 本文件
```

## 🚀 使用方法

### 1. 安装依赖

```bash
pip install tushare pandas numpy
```

### 2. 配置 Tushare Token

编辑 `backtest_real.py`，设置你的 Tushare Token：

```python
TS_TOKEN = 'your_token_here'
```

### 3. 运行回测

```bash
# 简化估算版
python backtest_v3.py

# 真实回测（推荐）
python backtest_real_v2.py
```

### 4. 修改策略

编辑 `strategy.py` 中的 `StrategyConfig` 类：

```python
@dataclass
class StrategyConfig:
    min_roe: float = 7.0           # 最小 ROE%
    max_debt_ratio: float = 90.0   # 最大负债率%
    min_revenue_growth: float = -10.0  # 最小营收增长率%
```

## 📋 选中股票（9 只）

- 中国神华 (601088.SH)
- 紫金矿业 (601899.SH)
- 宁德时代 (300750.SZ)
- 招商银行 (600036.SH)
- 长江电力 (600900.SH)
- 五粮液 (000858.SZ)
- 美的集团 (000333.SZ)
- 迈瑞医疗 (300760.SZ)
- 药明康德 (603259.SH)

## 📊 对比基准

| 指标 | 本策略 | 沪深 300 | 超额 |
|------|--------|---------|------|
| 年化 | 18.82% | ~6% | +12% ✅ |
| 夏普 | 0.82 | ~0.3 | +0.5 ✅ |
| 回撤 | -28.5% | -46% | 更优 ✅ |

## ⚠️ 风险提示

1. 历史回测不代表未来表现
2. 数据来源于 Tushare，可能存在延迟或误差
3. 未考虑交易成本和滑点
4. 投资有风险，入市需谨慎

## 📄 License

MIT License

## 👤 Author

GitHub: [@xiaofeng0920-Happy](https://github.com/xiaofeng0920-Happy)

---

*最后更新：2026-04-15*
