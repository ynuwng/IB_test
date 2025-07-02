from ib_insync import *
import pandas as pd
import numpy as np

# === 连接 IBKR TWS ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# === 合约定义 ===
contract = Stock('BMNR', 'SMART', 'USD')
ib.qualifyContracts(contract)

# === 获取历史数据（最近5天 × 1分钟K线 × 常规交易时间）===
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='2 D',
    barSizeSetting='1 min',
    whatToShow='TRADES',
    useRTH=True,               # ✅ 只要常规交易时间内数据（9:30–16:00）
    formatDate=1
)

# === 错误处理 ===
if not bars:
    print("⚠️ 没有收到历史数据")
    ib.disconnect()
    exit()

# === 转换为 pandas DataFrame ===
df = util.df(bars)
df.set_index('date', inplace=True)

# === 技术指标计算 ===
lenVol = 20
volRatioTh = 1.5
shortMA_Len = 5
midMA_Len = 10

df['vol_avg'] = df['volume'].rolling(lenVol).mean()
df['vol_ratio'] = df['volume'] / df['vol_avg']
df['shortMA'] = df['close'].rolling(shortMA_Len).mean()
df['midMA'] = df['close'].rolling(midMA_Len).mean()

# === 买入信号判断 ===
df['vol_spike'] = df['volume'] > 1.5 * df['vol_avg']
df['crossover'] = (df['shortMA'] > df['midMA']) & (df['shortMA'].shift(1) <= df['midMA'].shift(1))

df['signal'] = (df['vol_ratio'] > volRatioTh) & df['vol_spike'] & df['crossover']

# === 打印最近信号 ===
latest_bar = df.iloc[-1]
if latest_bar['signal']:
    print(f"✅ 触发买入信号！时间：{latest_bar.name}, 价格：{latest_bar['close']:.2f}")
else:
    print(f"⛔ 当前无信号。最后价格：{latest_bar['close']:.2f}")


# === 输出历史触发过的买入信号（最近10个） ===
signal_bars = df[df['signal']]
print("\n📈 最近历史买入信号（最多10条）:")
print(signal_bars[['close', 'vol_ratio', 'shortMA', 'midMA']].tail(10))


# === 可选：保存数据输出 ===
df.to_csv('tsla_signals.csv')

ib.disconnect()
