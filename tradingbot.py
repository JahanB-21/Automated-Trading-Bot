from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime, timedelta
from alpaca_trade_api import REST
from utils import estimate_sentiment
import yfinance as yf

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

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()  # Get date
        news = self.api.get_news(symbol=self.symbol,  # Get news
                                 start=three_days_prior, 
                                 end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]  # Format news
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment() 

        if cash > last_price:  # Checks purchases occurring only when cash is available
            if sentiment == "positive" and probability > 0.999:
                if self.last_trade == "sell":
                    self.sell_all()
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
            elif sentiment == "negative" and probability > 0.999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(  # Create order
                    self.symbol,     
                    quantity,
                    "sell",  # Type of order
                    type="bracket",  # Order type
                    take_profit_price=last_price * 0.8,  # Book profits at 20%
                    stop_loss_price=last_price * 1.05 
                )
                self.submit_order(order)
                self.last_trade = "sell"

    def get_risk_free_rate(self):
        # Fetch the risk-free rate using yfinance with a valid period
        try:
            irx = yf.Ticker("^IRX")
            irx_history = irx.history(period="1mo")  # Change '7d' to '1mo'
            if not irx_history.empty:
                risk_free_rate = irx_history['Close'].iloc[-1] / 100  # Convert to a decimal
                return risk_free_rate
            else:
                raise ValueError("IRX history is empty")
        except Exception as e:
            self.log(f"Error getting the risk free rate: {e}", level="error")
            return 0.01  # Return a default value if there's an error

start_date = datetime(2020, 1, 1)
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
