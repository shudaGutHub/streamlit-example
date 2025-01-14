import pandas as pd
import numpy as np
import dataclasses
import datetime as datetime
from dataclasses import dataclass





@dataclass
class OptionMarketModel(object):
    OptionTicker: str
    Symbol: str
    OptPC: str
    Expiry: pd.datetime
    Strike: float
    Symbol : str
    yTicker : yf.Ticker()
def __repr__(self):
        return self.OptionTicker
@dataclass
class OptionContract:
    """
    A class to represent an option contract
    """
    
    strike: float
    expiry: datetime.datetime
    option_type: str
    exchange: str = "SMART"
    multiplier: int = 100
    currency: str = "USD"
    option_exercise_type: str = "A"

    def __post_init__(self):
        self.option = Option(

            strike=self.strike,
            expiry=self.expiry,
            option_type=self.option_type,
            exchange=self.exchange,
            multiplier=self.multiplier,
            currency=self.currency,
            option_exercise_type=self.option_exercise_type
        )

    def price(self):
        pass