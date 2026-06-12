from core.bot import TradingBot, setup_logging

if __name__ == "__main__":
    setup_logging()
    TradingBot().run()
