from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print("连接成功：", ib.isConnected())
ib.disconnect()
