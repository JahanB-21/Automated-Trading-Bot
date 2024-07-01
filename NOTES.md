class MLTrader strategy notes:
* Life cycle method
    * When the bot starts, the initialize method will run once 
    and the on-trading method will run every time we get new data from source

Position sizing:
* Using cash at risk
    * How much of our cash balance do we want to risk at every trade
    * Higher the number, the more cash per trade and vice versa
* 