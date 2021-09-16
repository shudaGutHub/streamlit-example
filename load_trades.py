import pandas as pd
import numpy as np
import pathlib
import scipy.stats as stats
import pathlib as pathlib
from mibian import BS
import yfinance as yf
from BDFunds import *
DIR_DATA = pathlib.Path('C:\\Users\\salee\\projects\\streamlit-example')

filename_holdings_start="BDIN_HOLDINGS_2020.xlsx"
filename_tickers="tickers.csv"

filename_attribution_ytd = "BDIN_Security_YTD.xlsx"
filename_attribution_ltd = "BDIN_Security_LTMONTH.xlsx"
filename_holdings_end="BDIN__HOLDINGS_2021_Aug.xlsx"
filename_trades = 'BDIN_Trades_YTD.xlsx'
filename_NAV = 'BDIN_NAV.xlsx'
get_fp = lambda fname: pathlib.Path(DIR_DATA,fname)


class EquityModel(object):
	def __init__(self, sym, ISIN):
		self.sym = sym
		self.ISIN = ISIN
		self.data = pd.DataFrame

	def load(self, data):
		self.data = data

	def price(self, value_date):
		return self.data.loc[value_date]

	def __repr__(self):
		return self.sym


class OptionModel(object):
	def __init__(self, value_date, sym, spot, sigma, optPC, strike, expiry, frate, qrate, bdfunds_ticker=None):
		"""optPC:"C", sym:"CRM", strike:227, expiry"""
		print("Sym: {}".format(sym))
		self.value_date = value_date
		self.sym = sym
		self.spot = spot
		self.sigma = sigma
		self.optPC = optPC
		self.strike = strike
		self.expiry = expiry
		self.frate = frate
		self.qrate = qrate
		self.EXPIRY_YF = self.expiry - (pd.Timedelta(1, 'DAYS'))
		self.bdfunds_ticker = bdfunds_ticker
		self.option_ticker = "_".join([optPC, sym, str(strike), expiry.strftime("%Y%m%d")])
		self.underlying_ticker = yf.Ticker(self.sym)
		self.data_s3 = None
		self.yahoodata = self.get_yahoo()
		self.impliedVol = self.yahoodata['impliedVolatility']

	def add_underlying(self, bdpos):
		self.underlying = yf.Ticker(self.sym)

	# self.underlying = BDEquity(sym, start)
	def load_s3(self):
		pass
		#self.data_s3 = load_s3_options(self.sym).query(
		#'ExpirationYYYYMMDD==@self.expiry & strike==@self.strike & pc==@self.OptPC')

	def term_in_years(self):
		return (self.expiry - self.value_date).days / 365.0

	def get_yahoo(self):
		test_expiry = self.EXPIRY_YF.strftime("%Y-%m-%d")
		# test_expiry not in self.underlying_ticker.option_chain(test_expiry).calls.query("strike==@self.strike") #.strftime("%Y-%m-%d")- (pd.Timedelta(1, 'DAYS'))

		try:
			if self.optPC == "C":
				return self.underlying_ticker.option_chain(test_expiry).calls.query("strike==@self.strike")
			if self.optPC == "P":
				return self.underlying_ticker.option_chain(test_expiry).puts.query("strike==@self.strike")
			else:
				print("Not P or C")
				return None
		except:
			test_expiry = self.expiry.date().strftime("%Y-%m-%d")
			if self.optPC == "C":
				return self.underlying_ticker.option_chain(test_expiry).calls.query("strike==@self.strike")
			if self.optPC == "P":
				return self.underlying_ticker.option_chain(test_expiry).puts.query("strike==@self.strike")
			else:
				print("Not P or C")
				return None

	@staticmethod
	def bsm_price(option_type, sigma, s, k, r, T, q):
		# calculate the bsm price of European call and put options

		sigma = float(sigma)
		d1 = (np.log(s / k) + (r - q + sigma ** 2 * 0.5) * T) / (sigma * np.sqrt(T))
		d2 = d1 - sigma * np.sqrt(T)
		if option_type == 'C':
			price = np.exp(-r * T) * (s * np.exp((r - q) * T) * stats.norm.cdf(d1) - k * stats.norm.cdf(d2))
			return price
		elif option_type == 'P':
			price = np.exp(-r * T) * (k * stats.norm.cdf(-d2) - s * np.exp((r - q) * T) * stats.norm.cdf(-d1))
			return price
		else:
			print('No such option type %s') % option_type

	# Sharpe Ratio

	def theo_price(self):

		return self.bsm_price(option_type=self.optPC,
							  sigma=self.sigma,
							  s=self.spot,
							  k=self.strike,
							  r=self.frate,
							  T=self.term_in_years(),
							  q=self.qrate)

	def delta(self, S, K, T, r, optPC, q=0, sigma=.3):
		"""BSM delta formulaa"""
		d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
		result = 0
		if optPC == 'C':
			result = stats.norm.cdf(d1, 0.0, 1.0)
		elif optPC == 'P':
			result = stats.norm.cdf(d1, 0.0, 1.0) - 1

		return result

	def __repr__(self):
		return self.option_ticker


def get_equities(df):
	options = {}
	for row in df.itertuples():
		assert row.AssetClass == "Equity"
		options[row.ISIN] = EquityModel(
			sym=row.SymbolBLK,
			ISIN=row.ISIN)

	return options


def load_prices_underlyings(dft, start_date='2017-01-01', end_date='2021-09-13'):
	"""Load price data"""
	symbols_options = list(dft.query('AssetClass==["Option","Equity"]')['Symbol'].unique())
	prices = yf.download(symbols_options, start_date, end_date)
	return prices

def get_returns_from_prices(prices):
	return qs.utils.to_log_returns(prices)


def get_volatilities_from_returns(returns):
	return qs.stats.volatility(returns)

def test_load_trades(filename):
	df = pd.read_excel(
	io = get_fp(filename),
	engine = 'openpyxl',
	sheet_name = 'Trades',
	skiprows = 0,  # TODO Process from raw file requires stripping top row
	usecols = 'A:M',
	parse_dates = ['TradeData', 'EffectiveDate'],

	)

	dfeq =  df.query("AssetClass==['Equity','Option']").copy()
	dfeq['Symbol'] = dfeq['Ticker'].str.split(" ").map(lambda x:x[0])

	option_tickers_raw = dfeq.query('AssetClass == "Option"')['Ticker'].unique()
	options_split = {ticker: dict(zip(["Symbol","Currency","ExpiryDate","PCStrike"],ticker.split(" "))) for ticker in option_tickers_raw}
	options_split_Expiry = {ticker: pd.to_datetime(opt.get('ExpiryDate')) for ticker,opt in options_split.items()}

	options_split_PutCall = {ticker:opt.get('PCStrike')[0] for ticker,opt in options_split.items()}
	options_split_Strike = {ticker: float(opt.get('PCStrike')[1:]) for ticker, opt in options_split.items()}

	dfeq['OptPC'] = dfeq['Ticker'].map(lambda x:options_split_PutCall.get(x,"C"))


	dfeq['STRIKE'] = dfeq['Ticker'].map(lambda x: options_split_Strike.get(x, .01)) #StrikePrice or 1 cent for equities
	dfeq['EXPIRY_DATE'] = dfeq['Ticker'].map(lambda x: options_split_Expiry.get(x,pd.to_datetime('2050-01-01'))) #Expiry or some date far in the future for Equity
	dfeq['TERM_DAYS'] = (dfeq['EXPIRY_DATE'] - dfeq['TradeData']).map(lambda x: max(x.days, 0)) #Number of days in Term
	dfeq['TERM_YEARS'] = dfeq['TERM_DAYS']/365.0
	dfeq['RATE'] = .01
	dfeq['RATE_Q'] =.0
	dfeq['X8VOL'] = .25
	dfeq['BSVOL'] = dfeq['X8VOL']*100
	dfeq['Date'] = dfeq['TradeData'].values



	dfeq = dfeq.set_index(['Date','Ticker'])
	return dfeq

def test_load_holdings_start(filename):
	df = pd.read_excel(
		io=get_fp(filename),
		engine='openpyxl',
		sheet_name='Sheet1',
		skiprows=0,
		usecols='A:W',


	)
	df.columns =[c.replace("/","").strip().replace(" ","").replace("%","PctOf") for c in df.columns]

	return df
def test_load_attribution(filename):
	df = pd.read_excel(
		io=get_fp(filename),
		engine='openpyxl',
		sheet_name='Sheet1',
		skiprows=0,
		usecols='A:I'

	)
	df.columns =[c.replace("/","").strip().replace(" ","").replace("%","PctOf") for c in df.columns]

	return df
def test_load_NAV(filename):
	df = pd.read_excel(
		io=get_fp(filename),
		engine='openpyxl',
		sheet_name='Sheet1',
		skiprows=0,
		usecols='A:I'

	)
	df.columns =[c.replace("/","").strip().replace(" ","").replace("%","PctOf") for c in df.columns]

	return df

from datetime import date


import dataclasses
from dataclasses import dataclass
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt




def merge_underlyings(dft, prices, vols, col='Close'):
	dfcloses = pd.DataFrame(prices['Close'].stack(), columns=['Close'])
	dfcloses.index.names=['TradeData','Symbol']

	dfm = dft.set_index(['TradeData','Symbol']).join(dfcloses, lsuffix="_t").reset_index()
	vols =pd.Series(vols.stack(),name='HVOL')
	vols.index.names=['TradeData','Ticker']

	dfv = pd.merge(dfm, pd.DataFrame(vols.reset_index()), left_index=True, right_index=True)
	return dfv






def get_options(df, start='2017-01-01', end='2021-09-14'):
	impliedVols = {}
	syms = list(df['Symbol'].unique())
	#prices = yf.download(syms,start,end)
	mibianBS={}
	dftemp = df.copy()

	for row in dftemp.itertuples():
		assert row.AssetClass == "Option"
		sym= row.Symbol
		sigma= row.HVOL

		spot= row.Close

		number_of_days=row.TERM_DAYS
		expiry=row.EXPIRY_DATE
		strike=row.STRIKE
		frate=row.RATE
		qrate=row.RATE_Q
		optPC=row.OptPC
		bdfunds_ticker=None
		value_date=row.TradeData

		bsdata = [spot, strike, frate*100, number_of_days]
		print([sym, spot, strike,number_of_days,sigma])
		idx_val_trade = (row.TradeData,row.Ticker)
		if optPC =="P":

			df[idx_val_trade] = mibian.BS(bsdata, putPrice=row.PriceBase).impliedVolatility
			impliedVols[idx_val_trade] = mibian.BS(bsdata, putPrice=row.PriceBase).impliedVolatility
			mibianBS[idx_val_trade] = mibian.BS(bsdata,volatility=sigma*100)
		elif optPC =="C":

			df[idx_val_trade] = mibian.BS(bsdata, callPrice=row.PriceBase).impliedVolatility
			impliedVols[idx_val_trade] = mibian.BS(bsdata, callPrice=row.PriceBase).impliedVolatility
			mibianBS[idx_val_trade] = mibian.BS(bsdata, volatility = sigma * 100)

		else:
			mibianBS[idx_val_trade] = None
	df= df.set_index(['TradeData','Ticker'])
	df['IVOL_TRADE'] = df.index.map(lambda idx:impliedVols.get(idx))
	dictbs = {idx: model.__dict__ for idx, model in mibianBS.items()}
	dfbs = pd.DataFrame.from_dict(dictbs, orient='index').reset_index().rename(columns={'level_0':'TradeData', 'level_1':'Ticker'})

	return df,dfbs


def add_option_risk_historical(df):
	model_params, prices_hvol = get_options(df)
	grp_class_putcall = df.groupby(["AssetClass","OptPC"])

	dfputs  = grp_class_putcall.get_group(('Option','P')).copy()
	dfputs['putDelta'] = dfputs.set_index(prices_hvol.index).map(lambda idx: prices_hvol.get(idx).putDelta)


	return dfputs


dftrades = test_load_trades(filename_trades)
prices = load_prices_underlyings(dftrades)
dfprices = prices['Close'].stack().reset_index().drop_duplicates()
dfprices.columns = ['Date','Symbol','Close']
dfmerge_price = pd.merge(dfprices, dftrades.reset_index(), how='right', on=['Date','Symbol'])

dfholdings = test_load_holdings_start(filename_holdings_start)
dfattribution_ytd = test_load_attribution(filename_attribution_ytd)
dfattribution_ltd = test_load_attribution(filename_attribution_ltd)
dfnav = test_load_NAV(filename_NAV)





returns = get_returns(prices['Adj Close'])
vols = get_volatility(returns)
dfvols = vols.stack().reset_index()


dfvols.columns = ['Date','Symbol','HVOL']
dfmerge_vols  =pd.merge(dfvols,dfmerge_price, how='right', on=['Date','Symbol'])
dfmerge_vols['HVOL'] = dfmerge_vols['HVOL'].fillna(.3)


df_final = dfmerge_vols.query('TERM_DAYS>0')
df_final
import mibian
dfoptions, dfbs = get_options(df_final.query('AssetClass=="Option"'))
dfbs = dfbs.rename(columns={'exerciceProbability':'probCall'})
#dfoptions =pd.merge(dfoption_vol.reset_index(),dfoption_prices,on=['TradeData','Ticker'])
#dfoptions = pd.DataFrame.from_dict(orient='index',data={idx:model.__dict__ for idx,model in prices_hvol.items()}).rename(columns={'exerciceProbability':'probExercise'})

# '''Black-Scholes
# Used for pricing European options on stocks without dividends
#
# BS([underlyingPrice, strikePrice, interestRate, daysToExpiration], \
# 		volatility=x, callPrice=y, putPrice=z)
#
# eg:
# 	c = mibian.BS([1.4565, 1.45, 1, 30], volatility=20)
# 	c.callPrice				# Returns the call price
# 	c.putPrice				# Returns the put price
# 	c.callDelta				# Returns the call delta
# 	c.putDelta				# Returns the put delta
# 	c.callDelta2			# Returns the call dual delta
# 	c.putDelta2				# Returns the put dual delta
# 	c.callTheta				# Returns the call theta
# 	c.putTheta				# Returns the put theta
# 	c.callRho				# Returns the call rho
# 	c.putRho				# Returns the put rho
# 	c.vega					# Returns the option vega
# 	c.gamma					# Returns the option gamma
#
# 	c = mibian.BS([1.4565, 1.45, 1, 30], callPrice=0.0359)
# 	c.impliedVolatility		# Returns the implied volatility from the call price
#
# 	c = mibian.BS([1.4565, 1.45, 1, 30], putPrice=0.0306)
# 	c.impliedVolatility		# Returns the implied volatility from the put price
#
# 	c = mibian.BS([1.4565, 1.45, 1, 30], callPrice=0.0359, putPrice=0.0306)
# 	c.putCallParity			# Returns the put-call parity
# 	'''
#
#
# def __init__(self, args, volatility=None, callPrice=None, putPrice=None, \
# 			 performance=None):
# 	self.underlyingPrice = float(args[0])
# 	self.strikePrice = float(args[1])
# 	self.interestRate = float(args[2]) / 100
# 	self.daysToExpiration = float(args[3]) / 365
#
# 	for i in ['callPrice', 'putPrice', 'callDelta', 'putDelta', \
# 			  'callDelta2', 'putDelta2', 'callTheta', 'putTheta', \
# 			  'callRho', 'putRho', 'vega', 'gamma', 'impliedVolatility', \
# 			  'putCallParity']:
# 		self.__dict__[i] = None
#
# 	if volatility:
# 		self.volatility = float(volatility) / 100
#
# 		self._a_ = self.volatility * self.daysToExpiration ** 0.5
# 		self._d1_ = (log(self.underlyingPrice / self.strikePrice) + \
# 					 (self.interestRate + (self.volatility ** 2) / 2) * \
# 					 self.daysToExpiration) / self._a_
# 		self._d2_ = self._d1_ - self._a_
# 		if performance:
# 			[self.callPrice, self.putPrice] = self._price()
# 		else:
# 			[self.callPrice, self.putPrice] = self._price()
# 			[self.callDelta, self.putDelta] = self._delta()
# 			[self.callDelta2, self.putDelta2] = self._delta2()
# 			[self.callTheta, self.putTheta] = self._theta()
# 			[self.callRho, self.putRho] = self._rho()
# 			self.vega = self._vega()
# 			self.gamma = self._gamma()
# 			self.exerciceProbability = norm.cdf(self._d2_)
# 	if callPrice:
# 		self.callPrice = round(float(callPrice), 6)
# 		self.impliedVolatility = impliedVolatility( \
# 			self.__class__.__name__, args, callPrice=self.callPrice)
# 	if putPrice and not callPrice:
# 		self.putPrice = round(float(putPrice), 6)
# 		self.impliedVolatility = impliedVolatility( \
# 			self.__class__.__name__, args, putPrice=self.putPrice)
# 	if callPrice and putPrice:
# 		self.callPrice = float(callPrice)
# 		self.putPrice = float(putPrice)
# 		self.putCallParity = self._parity()
