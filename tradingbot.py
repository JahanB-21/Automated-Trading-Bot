# Import Lumibot trading libraries
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from alpaca_trade_api import REST

# Import datetime library
from datetime import datetime, timedelta

# Alpaca credentials
API_KEY = "PK0BTBJGGMK0CM12T39K"
API_SECRET = "oqoRslfod91HKyTAMkvYYJixFNco8dxPFslAGQ5j"
BASE_URL = "https://paper-api.alpaca.markets/v2"

# Alpaca dictionary 
ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "BASE_URL": BASE_URL,
    "PAPER": True
}

# Strategy Framework (backbone of trading bot)
class MLTrader(Strategy):
    # Create method
    def initialize(self, symbol: str = "SPY", cash_at_risk: float = 0.5):  # creating parameter for SPY index
        self.symbol = symbol
        self.sleeptime = "24H"  # Dictates how frequently we will trade
        self.last_trade = None  # Captures what the last trade was in case we want to undo buys
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self):
        cash = self.get_cash()  # Extract cash from account
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)  # Units per risked amount
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_news(self):
        today, three_days_prior = self.get_dates()  # Get date
        news = self.api.get_news(symbol=self.symbol,  # Get news
                                 start=three_days_prior, 
                                 end=today)
        news = [event.__dict__["_raw"]["headline"] for event in news]  # Format news
        return news

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        if cash > last_price:  # Checks purchases occurring only when cash is available
            if self.last_trade is None:
                news = self.get_news()
                print(news)
                order = self.create_order(  # Create order
                    self.symbol,    
                    quantity,
                    "buy",  # Type of order
                    type="bracket",  # Order type
                    take_profit_price=last_price * 1.20,  # Book profits at 20%
                    stop_loss_price=last_price * 0.95 
                )
                self.submit_order(order)
                self.last_trade = "buy"

start_date = datetime(2024, 6, 1)
end_date = datetime(2024, 6, 30)
broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name="mlstrat", broker=broker, 
                    parameters={"symbol": "SPY", 
                                "cash_at_risk": 0.5})

# Set up backtesting: evaluate how well the bot runs
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol": "SPY", "cash_at_risk": 0.5}
)
