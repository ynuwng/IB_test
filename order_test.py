from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=123)

contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

order = MarketOrder('BUY', 1)
trade = ib.placeOrder(contract, order)
ib.sleep(2)

print("下单状态：", trade.orderStatus.status)
ib.disconnect()
