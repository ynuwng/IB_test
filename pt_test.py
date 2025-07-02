import asyncio
from ib_insync import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pandas as pd
from datetime import datetime, timedelta
import os

# === IB API 初始化 ===
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# === 策略参数 ===
VOL_PERIOD = 20
VOL_RATIO_TH = 1.45
SHORT_MA = 5
MID_MA = 10
ATR_PERIOD = 14
TP_ATR = 2.5
SL_ATR = 1.5
RISK_PCT = 0.5
SYMBOL = 'BMNR'
EXCHANGE = 'SMART'
CURRENCY = 'USD'

# === 获取实时数据并构建 DataFrame ===
async def fetch_data():
    contract = Stock(SYMBOL, EXCHANGE, CURRENCY)
    end_time = ''  # 当前时刻
    bars = await ib.reqHistoricalDataAsync(
        contract,
        endDateTime=end_time,
        durationStr='2 D',
        barSizeSetting='1 min',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1,
        keepUpToDate=False
    )
    df = util.df(bars)
    df.set_index('date', inplace=True)
    return df

# === 策略逻辑 ===
def apply_strategy(df):
    df['vol_avg'] = df['volume'].rolling(VOL_PERIOD).mean()
    df['vol_ratio'] = df['volume'] / df['vol_avg']
    df['shortMA'] = df['close'].rolling(SHORT_MA).mean()
    df['midMA'] = df['close'].rolling(MID_MA).mean()
    df['atr'] = (df['high'] - df['low']).rolling(ATR_PERIOD).mean()

    df['signal'] = (df['vol_ratio'] > VOL_RATIO_TH) & (df['shortMA'] > df['midMA'])
    return df

# === 执行交易逻辑 ===
async def run_strategy():
    print(f"\n📈 Running strategy at {datetime.now()}")
    try:
        df = await fetch_data()
        df = apply_strategy(df)

        last_row = df.iloc[-1]
        if last_row['signal']:
            price = last_row['close']
            atr = last_row['atr']
            cash = ib.accountSummary().loc['NetLiquidation', 'value']
            alloc = float(cash) * RISK_PCT
            quantity = int(alloc / price)

            # === 创建下单合约 ===
            contract = Stock(SYMBOL, EXCHANGE, CURRENCY)
            order = MarketOrder('BUY', quantity)
            trade = ib.placeOrder(contract, order)

            print(f"✅ 触发信号，买入 {quantity} 股，价格约为 {price:.2f}")

            # === 设置追踪止盈止损 ===
            tp_price = price + TP_ATR * atr
            sl_price = price - SL_ATR * atr

            bracket = ib.bracketOrder(
                'SELL', quantity,
                limitPrice=tp_price,
                stopPrice=sl_price,
            )
            for o in bracket:
                ib.placeOrder(contract, o)

            log_trade({
                'Datetime': datetime.now(),
                'Signal': True,
                'Price': price,
                'Size': quantity,
                'TP': tp_price,
                'SL': sl_price
            })
        else:
            print(f"⛔ 当前无信号。最后价格：{last_row['close']:.2f}")
    except Exception as e:
        print(f"⚠️ 错误：{e}")

# === 日志保存 ===
def log_trade(info):
    path = 'live_trade_log.csv'
    df_log = pd.DataFrame([info])
    if os.path.exists(path):
        df_log.to_csv(path, mode='a', index=False, header=False)
    else:
        df_log.to_csv(path, index=False)

# === 定时执行 ===
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_strategy, 'interval', minutes=1)
    scheduler.start()
    print("✅ 自动交易已启动，每分钟运行一次策略。按 Ctrl+C 终止。")
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("⛔ 自动交易已终止。")

if __name__ == '__main__':
    asyncio.run(main())
