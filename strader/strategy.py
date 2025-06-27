from queue import Queue
from tkinter import messagebox
from typing import List

from bbstrader.btengine.data import DataHandler
from bbstrader.btengine.event import Events
from bbstrader.btengine.strategy import MT5Strategy
from bbstrader.metatrader.account import Account
from bbstrader.metatrader.trade import TradeAction, TradeSignal, TradingMode
from bbstrader.models.nlp import FINANCIAL_LEXICON, SentimentAnalyzer  # noqa: F401


class SentimentTrading(MT5Strategy):
    """
    A sentiment-based trading strategy that generates signals based on
    financial news sentiment scores for specified tickers.

    Inherits from:
        MT5Strategy: Base class for MetaTrader 5-compatible strategies.
    """

    ID = 7950
    NAME = "BBS@STS"
    DESCRIPTION = "Sentiment Trading Strategy"

    def __init__(
        self,
        bars: DataHandler = None,
        events: Queue = None,
        symbol_list: List[str] = None,
        mode: TradingMode = TradingMode.BACKTEST,
        **kwargs,
    ):
        """
        Initialize the SentimentTrading strategy.

        Args:
            bars (DataHandler): Market data handler.
            events (Queue): Queue of events to handle.
            symbol_list (List[str]): List of symbols to trade.
            mode (TradingMode): Mode of execution (LIVE or BACKTEST).
            **kwargs: Additional configuration such as:
                - ID (int): Strategy ID override.
                - threshold (float): Sentiment score threshold for signals.
                - max_positions (int): Maximum open positions allowed.
                - symbols (dict): Mapping of MT5 symbols to external tickers.
        """
        self.bars = bars
        self.events = events
        self.symbol_list = symbol_list or self.bars.symbol_list
        self.mode = mode

        super().__init__(
            events=self.events,
            bars=self.bars,
            symbol_list=self.symbol_list,
            mode=self.mode,
            **kwargs,
        )

        self.ID = kwargs.get("ID", SentimentTrading.ID)
        self.tickers = kwargs.get("symbols")
        self.threshold = kwargs.get("threshold", 0.2)
        self.ext_th = kwargs.get("expected_return", 1.0)
        self.max_positions = kwargs.get("max_positions", len(self.tickers))
        self.analyser = SentimentAnalyzer()
        self._sentiments = {}

    @property
    def sentiments(self):
        """
        Returns the latest sentiment scores per ticker.

        Returns:
            dict: Ticker to sentiment score mapping.
        """
        return self._sentiments

    def _calculate_backtest_signals(self):
        """
        Placeholder for backtest signal calculation.
        To be implemented as needed for historical data simulation.
        """
        ...

    def _ismax_postions(self):
        """
        Checks whether the strategy has reached the maximum allowed open positions.

        Returns:
            bool: True if max_positions limit is reached, False otherwise.
        """
        account = Account(**self.kwargs)
        positions = account.get_positions() or []
        positions = [p for p in positions if p.magic == self.ID]
        return len(positions) >= self.max_positions

    def _get_mt5_equivalent(self, ticker) -> str:
        """
        Maps an external ticker to its corresponding MT5 symbol.

        Args:
            ticker (str): External ticker name.

        Returns:
            str: MT5 symbol.
        """
        return list(self.tickers.keys())[list(self.tickers.values()).index(ticker)]

    def _calculate_live_signals(self):
        """
        Calculates trading signals based on live sentiment scores.

        Returns:
            List[TradeSignal]: List of trade signals based on sentiment thresholds.
        """
        tickers = list(self.tickers.values())
        if len(tickers) == 0:
            return []

        to_show = ", ".join(tickers[:5])
        self.logger.info(f"Fetching sentiments for tickers: {to_show}...")

        try:
            sentiments = self.analyser.get_sentiment_for_tickers(
                tickers, lexicon=FINANCIAL_LEXICON, **self.kwargs
            )
        except Exception as e:
            err_msg = f"Error fetching sentiments: {e}"
            self.logger.error(err_msg)
            messagebox.showerror("Error", err_msg)
            return {}

        self._sentiments = sentiments
        signals: List[TradeSignal] = []

        for ticker, score in sentiments.items():
            symbol = self._get_mt5_equivalent(ticker)

            # Skip if already holding LONG or SHORT for this symbol
            # Or EXIT condition are met
            if self.ispositions(
                symbol, self.ID, 1, 1, one_true=True
            ) or self.ispositions(symbol, self.ID, 0, 1, one_true=True):
                buys = self.get_positions_prices(symbol, self.ID, 0)
                sells = self.get_positions_prices(symbol, self.ID, 1)
                if (
                    self.exit_positions(0, buys, symbol, th=self.ext_th)
                    or score <= -self.threshold / 2
                ):
                    signals.append(
                        TradeSignal(
                            id=self.ID, symbol=symbol, action=TradeAction.EXIT_LONG
                        )
                    )
                if (
                    self.exit_positions(1, sells, symbol, th=self.ext_th)
                    or score >= self.threshold
                ):
                    signals.append(
                        TradeSignal(
                            id=self.ID, symbol=symbol, action=TradeAction.EXIT_SHORT
                        )
                    )
                continue

            # Generate LONG signal
            if score >= self.threshold and not self._ismax_postions():
                self.logger.debug(
                    f"Ticker: {ticker}, Symbol: {symbol}, Sentiment: {score}"
                )
                signal = TradeSignal(id=self.ID, symbol=symbol, action=TradeAction.LONG)
                signals.append(signal)

            # Generate SHORT signal
            if score <= -self.threshold / 2 and not self._ismax_postions():
                self.logger.debug(
                    f"Ticker: {ticker}, Symbol: {symbol}, Sentiment: {score}"
                )
                signal = TradeSignal(
                    id=self.ID, symbol=symbol, action=TradeAction.SHORT
                )
                signals.append(signal)

        return signals

    def calculate_signals(self, event=None):
        if self.mode == TradingMode.BACKTEST and event is not None:
            if event.type == Events.MARKET:
                self._calculate_backtest_signals()
        elif self.mode == TradingMode.LIVE:
            return self._calculate_live_signals()
