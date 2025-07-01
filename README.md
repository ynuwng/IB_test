# IB_test

该仓库包含若干示例脚本，演示如何通过 [ib_insync](https://github.com/erdewit/ib_insync) 与 [Backtrader](https://www.backtrader.com/) 使用 Interactive Brokers 提供的行情数据进行简单的量化交易策略开发、回测以及下单操作。代码主要用于学习和测试用途。

## 环境要求

- Python 3.8 及以上
- [Interactive Brokers TWS](https://www.interactivebrokers.com/) 或 IB Gateway 运行在本地 `7497` 端口
- 依赖库：`ib_insync`、`backtrader`、`pandas`、`apscheduler` 等

可通过 `pip install -r requirements.txt`（如有）或手动安装以上依赖。

## 目录说明

- `newbt.py`：使用 Backtrader 实现的回测脚本，策略为量价动量模型，示例数据存储在 `tsla_signals.csv`。
- `mom_test.py`：通过 IB 接口实时获取数据，计算技术指标并生成信号，可将结果保存为 CSV。
- `pt_test.py`：异步自动交易示例，利用 APScheduler 每分钟运行一次策略，触发信号后通过 IB 下单，并设置止盈止损。
- `order_test.py`：最基础的下单测试脚本。
- `test.py`：简单的连接测试。
- `*.csv`：示例数据及交易记录，包括 `trade_log.csv` 等。

## 快速开始

1. 确保 TWS 或 IB Gateway 已登陆并监听本地 `7497` 端口。
2. 根据需要修改脚本中的合约符号及参数。
3. 运行回测示例：
   ```bash
   python newbt.py
   ```
4. 查看终端输出的资金变化和 `trade_log.csv` 中记录的交易明细。

> 以上脚本仅用于学习示例，实际交易需注意风险并自行承担责任。

## 许可证

本项目采用 [MIT License](LICENSE)。
