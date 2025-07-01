import backtrader as bt
import pandas as pd

# === 数据读取 ===
df = pd.read_csv('/Users/void4loop/PycharmProjects/IB_test/tsla_signals.csv', index_col=0, parse_dates=True)
df['openinterest'] = 0

# === 策略定义 ===
class VolumeMomentumStrategy(bt.Strategy):
    params = dict(
        vol_period=20,
        vol_ratio_th=1.5,
        short_ma=5,
        mid_ma=10,
        tp_pct=0.05,
        sl_pct=0.03,
        risk_pct= 0.8  # 每笔使用 10% 仓位
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume
        self.vol_avg = bt.indicators.SMA(self.volume, period=self.p.vol_period)
        self.vol_ratio = self.volume / (self.vol_avg + 1e-6)  # 避免除以 0

        self.shortMA = bt.indicators.SMA(self.dataclose, period=self.p.short_ma)
        self.midMA = bt.indicators.SMA(self.dataclose, period=self.p.mid_ma)
        self.crossover = bt.indicators.CrossOver(self.shortMA, self.midMA)

        self.order = None
        self.entry_price = None
        self.entry_datetime = None
        self.entry_size = None
        self.trade_log = []

    def next(self):
        if self.order:
            return

        dt = self.datas[0].datetime.datetime(0)

        if not self.position:
            if self.vol_avg[0] != 0 and self.vol_ratio[0] > self.p.vol_ratio_th and self.crossover[0] > 0:
                self.entry_price = self.dataclose[0]
                self.entry_datetime = dt

                cash = self.broker.getvalue()
                alloc = cash * self.p.risk_pct
                size = int(alloc / self.entry_price)
                self.entry_size = size

                self.order = self.buy(size=size)

        else:
            gain = (self.dataclose[0] - self.entry_price) / self.entry_price
            if gain >= self.p.tp_pct or gain <= -self.p.sl_pct:
                exit_price = self.dataclose[0]
                exit_datetime = dt
                pnl = (exit_price - self.entry_price) * self.entry_size
                ret = pnl / (self.entry_price * self.entry_size)

                self.trade_log.append({
                    'Buy Time': self.entry_datetime,
                    'Buy Price': round(self.entry_price, 2),
                    'Buy Size': self.entry_size,
                    'Sell Time': exit_datetime,
                    'Sell Price': round(exit_price, 2),
                    'Sell Size': self.entry_size,
                    'PnL ($)': round(pnl, 2),
                    'Return (%)': round(ret * 100, 2),
                    '交易金额 ($)': round(self.entry_price * self.entry_size, 2)
                })
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None

# === Backtrader 环境设定 ===
cerebro = bt.Cerebro()
cerebro.addstrategy(VolumeMomentumStrategy)

data = bt.feeds.PandasData(dataname=df)
cerebro.adddata(data)

cerebro.broker.setcash(10000)
cerebro.broker.setcommission(commission=0.0005)

# === 回测执行 ===
print(f"初始资金: {cerebro.broker.getvalue():.2f}")
results = cerebro.run()
strat = results[0]
print(f"最终资金: {cerebro.broker.getvalue():.2f}")

# === 输出交易记录 ===
df_trades = pd.DataFrame(strat.trade_log)
if not df_trades.empty:
    print("\n交易明细:")
    print(df_trades)
    df_trades.to_csv('trade_log.csv', index=False)
else:
    print("⚠️ 没有发生任何交易。")

# === 可视化 ===
cerebro.plot(style='candlestick')
