import backtrader as bt
import datetime
import pandas as pd
from ib_insync import *


# =============================================================================
#  1. 数据获取模块 (与之前相同)
# =============================================================================
def fetch_ib_data(symbol='NVDA', timeframe='1 day', duration='3 Y'):
    # ... (此部分代码保持不变)
    ib = None
    try:
        ib = IB();
        ib.connect('127.0.0.1', 7497, clientId=10)  # 建议更换clientId
        contract = Stock(symbol, 'SMART', 'USD');
        ib.qualifyContracts(contract)
        print(f"正在从IB获取 {symbol} 的 {duration} {timeframe} 数据...")
        bars = ib.reqHistoricalData(
            contract, endDateTime='', durationStr=duration, barSizeSetting=timeframe,
            whatToShow='TRADES', useRTH=True, formatDate=1
        )
        if not bars: print(f"⚠️ 没有收到 {symbol} 的历史数据"); return None
        df = util.df(bars);
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'},
                  inplace=True)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        print("数据获取并处理成功！")
        return df
    finally:
        if ib and ib.isConnected(): print("断开与IB的连接。"); ib.disconnect()


# =============================================================================
#  2. Backtrader 策略定义 (已修复)
# =============================================================================
class ProTrendStrategy(bt.Strategy):
    params = (
        ('longMA_Len', 50), ('shortMA_Len', 10), ('midMA_Len', 20),
        ('atrPeriod', 14), ('atrStopMult', 2.0), ('riskRewardTP1', 1.5),
        ('useTrailing', True), ('atrTrailMult', 3.0),
        ('percent_sizer', 20.0), ('printlog', False),
    )

    def __init__(self):
        # === 【关键修复】: 为所有需要的数据线创建类属性 ===
        # 这样在整个类的任何方法中都可以通过 self.xxx 访问
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # --- Indicators ---
        self.longMA = bt.indicators.EMA(self.dataclose, period=self.p.longMA_Len)
        self.shortMA = bt.indicators.EMA(self.dataclose, period=self.p.shortMA_Len)
        self.midMA = bt.indicators.EMA(self.dataclose, period=self.p.midMA_Len)
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.atrPeriod)
        self.crossover_signal = bt.indicators.CrossOver(self.dataclose, self.shortMA)

        # --- State Management ---
        self.entry_price = 0;
        self.tp1_price = 0;
        self.tp1_hit = False
        self.trailing_stop_active = False;
        self.exit_orders = []

    # log, notify_order, notify_trade 方法保持不变
    def log(self, txt, dt=None, doprint=False):
        # ...
        pass

    def notify_order(self, order):
        # ...
        pass

    def notify_trade(self, trade):
        # ...
        pass

    # next 方法现在可以正常工作
    def next(self):
        if self.position:
            # 在场内的逻辑保持不变
            if self.tp1_hit and not self.trailing_stop_active:
                self.log('--- ENTERING STAGE 2: TRAILING STOP ---')
                for o in self.exit_orders: self.cancel(o)
                self.exit_orders = []
                breakeven_price = self.entry_price
                if self.p.useTrailing:
                    stop_order = self.sell(exectype=bt.Order.StopTrail, trailamount=self.atr[0] * self.p.atrTrailMult)
                else:
                    stop_order = self.sell(exectype=bt.Order.Stop, price=breakeven_price)
                self.exit_orders.append(stop_order);
                self.trailing_stop_active = True
        else:
            # 重置状态
            self.tp1_hit = False
            self.trailing_stop_active = False
            self.exit_orders = []

            # --- 【最终逻辑 V3.1】: 融合两种入场模式 ---
            # 1. 趋势过滤器 (共同的前提)
            trend_filter = self.dataclose[0] > self.longMA[0] and self.shortMA[0] > self.midMA[0]

            if trend_filter:
                # 模式A: "鱼叉捕鱼" (单K线日内V形反转)
                pattern_A = self.datalow[0] < self.shortMA[0] and self.dataclose[0] > self.midMA[0]

                # 模式B: "浮漂钓鱼" (回调-确认序列)
                in_pullback_zone = self.dataclose[-1] < self.shortMA[-1] and self.dataclose[-1] > self.midMA[-1]
                recovery_signal = self.crossover_signal[0] > 0
                pattern_B = in_pullback_zone and recovery_signal

                # 只要满足任意一个模式，就入场
                if pattern_A or pattern_B:
                    self.log(f'BUY CREATE (V3.1 Logic), Pattern A: {pattern_A}, Pattern B: {pattern_B}')
                    # 后续的风险管理逻辑完全复用，保持不变
                    initial_stop_price = self.dataclose[0] - self.atr[0] * self.p.atrStopMult
                    initial_risk = self.dataclose[0] - initial_stop_price
                    self.tp1_price = self.dataclose[0] + initial_risk * self.p.riskRewardTP1
                    self.buy()
                    pos_size = self.getsizer().getsizing(self.data, isbuy=True)
                    tp1_order = self.sell(exectype=bt.Order.Limit, price=self.tp1_price, size=pos_size / 2)
                    initial_stop_order = self.sell(exectype=bt.Order.Stop, price=initial_stop_price)
                    self.exit_orders.extend([tp1_order, initial_stop_order])


# =============================================================================
#  3. Backtesting Engine Setup & Execution (与之前相同)
# =============================================================================
if __name__ == '__main__':
    # ... (此部分代码保持不变, 只是运行和分析)
    symbol_to_test = 'TSLA'
    dataframe = fetch_ib_data(symbol=symbol_to_test, timeframe='4 hours', duration='1 Y')
    if dataframe is None: print("无法进行回测，因为数据获取失败。"); exit()
    # ... 后续cerebro设置、运行和分析代码完全保持不变 ...
    cerebro = bt.Cerebro()
    cerebro.addstrategy(ProTrendStrategy)
    data = bt.feeds.PandasData(dataname=dataframe);
    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0);
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=ProTrendStrategy.params.percent_sizer)
    # 修复SharpeRatio的timeframe，对于小时级别数据，年化因子需要调整
    # 假设一年约252个交易日，每个交易日约6.5小时，4小时bar一天约2个
    # 更简单的做法是先不进行年化，或者使用 bt.TimeFrame.NoTimeFrame
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.NoTimeFrame)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    print('开始回测，初始资金: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run();
    strat = results[0]
    print('回测结束，最终资金: %.2f' % cerebro.broker.getvalue())
    # ... 后续的分析和CSV保存代码完全保持不变 ...
    print("\n正在生成并保存分析报告...")
    trade_analysis = strat.analyzers.trade_analyzer.get_analysis();
    returns_analysis = strat.analyzers.returns.get_analysis();
    sharpe_analysis = strat.analyzers.sharpe_ratio.get_analysis();
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    summary_report = {};
    if trade_analysis and 'total' in trade_analysis and trade_analysis.total.get('closed', 0) > 0:
        gross_pnl = trade_analysis.won.pnl.get('total', 0.0);
        gross_loss = abs(trade_analysis.lost.pnl.get('total', 0.0))
        summary_report = {
            '净利润': f"{trade_analysis.pnl.net.total:.2f}",
            '盈利因子': f"{gross_pnl / gross_loss if gross_loss != 0 else 'inf'}",
            '总交易次数': trade_analysis.total.closed, '盈利次数': trade_analysis.won.get('total', 0),
            '亏损次数': trade_analysis.lost.get('total', 0),
            '胜率 (%)': f"{trade_analysis.won.get('total', 0) / trade_analysis.total.closed * 100:.2f}",
            '平均盈利': f"{trade_analysis.won.pnl.get('average', 0.0):.2f}",
            '平均亏损': f"{trade_analysis.lost.pnl.get('average', 0.0):.2f}",
            '最大回撤 (%)': f"{drawdown_analysis.max.drawdown:.2f}",
            '夏普比率': f"{sharpe_analysis.get('sharperatio', 'N/A')}",
            '年化收益率 (%)': f"{returns_analysis.get('rann', 0.0) * 100:.2f}",
        }
        if 'trades' in trade_analysis and trade_analysis.trades:
            trades_df = pd.DataFrame([t for t in trade_analysis.trades.values() if isinstance(t, dict)])
            if not trades_df.empty:
                column_mapping = {'ref': '交易ID', 'ticker': '代码', 'dtopen': '开仓日期', 'priceopen': '开仓价',
                                  'dtclose': '平仓日期', 'priceclose': '平仓价', 'len': '持仓天数', 'pnl': '毛利润',
                                  'pnlnet': '净利润', 'size': '数量', 'value': '价值'}
                trades_df.rename(columns={k: v for k, v in column_mapping.items() if k in trades_df.columns},
                                 inplace=True)
                if '开仓日期' in trades_df.columns: trades_df['开仓日期'] = pd.to_datetime(
                    trades_df['开仓日期']).dt.strftime('%Y-%m-%d %H:%M:%S')
                if '平仓日期' in trades_df.columns: trades_df['平仓日期'] = pd.to_datetime(
                    trades_df['平仓日期']).dt.strftime('%Y-%m-%d %H:%M:%S')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S");
    summary_filename = f'report_summary_{symbol_to_test}_{timestamp}.csv';
    trades_filename = f'report_trades_{symbol_to_test}_{timestamp}.csv'
    if summary_report:
        summary_df = pd.DataFrame.from_dict(summary_report, orient='index', columns=['Value']);
        summary_df.index.name = 'Metric'
        summary_df.to_csv(summary_filename, encoding='utf-8-sig');
        print(f"✅ 摘要报告已保存到: {summary_filename}")
    if 'trades_df' in locals() and not trades_df.empty:
        trades_df.to_csv(trades_filename, index=False, encoding='utf-8-sig');
        print(f"✅ 逐笔交易详情已保存到: {trades_filename}")
    if not summary_report: print("回测期间没有发生交易，未生成报告文件。")
    cerebro.plot(style='candlestick', iplot=False)