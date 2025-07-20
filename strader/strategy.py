from queue import Queue
from tkinter import messagebox
from typing import List

from bbstrader.btengine import DataHandler, Events, MT5Strategy
from bbstrader.metatrader import TradeAction, TradeSignal, TradingMode
from bbstrader.metatrader.trade import EXPERT_ID
from bbstrader.models import LEXICON, SentimentAnalyzer  # noqa: F401


class SentimentTrading(MT5Strategy):
    """
    A sentiment-based trading strategy that generates signals based on
    financial news sentiment scores for specified tickers.

    Inherits from:
        MT5Strategy: Base class for MetaTrader 5-compatible strategies.
    """

    NAME = "BBS@STS"
    ID = int(str(7950) + str(EXPERT_ID)[4:])
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
                - expected_return (float): Expected return threshold for exit signals for each symbol.
                - symbols (dict): Mapping of MT5 symbols to external (Yahoo Finance) tickers.
                - symbols_type (str): Can be "stock", "etf", "future", "forex", "crypto", "index".

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
        self.symbol_type = kwargs.get("symbols_type")
        self.threshold = kwargs.get("threshold", 0.2)
        self.ext_th = kwargs.get("expected_return", 5.0)
        self.max_positions = kwargs.get("max_positions", len(self.tickers))
        _max_trades = kwargs.get("max_trades", self.max_positions // len(self.tickers))
        self.max_trades = {s: _max_trades for s in self.tickers.keys()}
        self.analyser = SentimentAnalyzer()
        self._sentiments = {}
        del _max_trades

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
        positions = [p for p in self.positions if p.magic == self.ID]
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
        signals: List[TradeSignal] = []
        tickers = list(self.tickers.values())
        if len(tickers) == 0:
            return signals

        to_show = ", ".join(tickers[:5])
        self.logger.info(f"Fetching sentiments for tickers: {to_show}...")

        try:
            sentiments = self.analyser.get_sentiment_for_tickers(
                tickers,
                lexicon=LEXICON[self.symbol_type],
                asset_type=self.symbol_type,
                **self.kwargs,
            )
        except Exception as e:
            err_msg = f"Error fetching sentiments: {e}"
            self.logger.error(err_msg)
            messagebox.showerror("Error", err_msg)
            return signals
        self._sentiments = sentiments
        to_show = {s: round(sentiments[s], 3) for s in tickers[:4]}
        self.logger.debug(f"Sentiment Fectched for {to_show}...")

        for ticker, score in sentiments.items():
            symbol = self._get_mt5_equivalent(ticker)

            # Check if EXIT conditions are met
            exit_signal = None
            buys = self.get_positions_prices(symbol, self.ID, 0)
            sells = self.get_positions_prices(symbol, self.ID, 1)
            if (
                self.exit_positions(0, buys, symbol, th=self.ext_th)
                or score <= -self.threshold / 2
            ):
                exit_signal = TradeSignal(
                    id=self.ID, symbol=symbol, action=TradeAction.EXIT_LONG
                )
            elif (
                self.exit_positions(1, sells, symbol, th=self.ext_th)
                or score >= self.threshold
            ):
                exit_signal = TradeSignal(
                    id=self.ID, symbol=symbol, action=TradeAction.EXIT_SHORT
                )

            if exit_signal is not None:
                signals.append(exit_signal)

            # Generate LONG signal
            if score >= self.threshold and not self._ismax_postions():
                if len(buys) == 0:
                    self.logger.debug(
                        f"Ticker: {ticker}, Symbol: {symbol}, Sentiment: {score}"
                    )
                    signal = TradeSignal(
                        id=self.ID, symbol=symbol, action=TradeAction.LONG
                    )
                    signals.append(signal)
                elif len(buys) in range(1, self.max_trades[symbol] + 1):
                    current_price = self.account.get_tick_info(symbol).ask
                    if (
                        self.calculate_pct_change(current_price, min(buys))
                        <= -self.ext_th / 2
                    ):
                        self.logger.debug(
                            f"Ticker: {ticker}, Symbol: {symbol}, Sentiment: {score}"
                        )
                        signal = TradeSignal(
                            id=self.ID, symbol=symbol, action=TradeAction.LONG
                        )
                        signals.append(signal)

            # Generate SHORT signal
            if score <= -self.threshold / 2 and not self._ismax_postions():
                if len(sells) == 0:
                    self.logger.debug(
                        f"Ticker: {ticker}, Symbol: {symbol}, Sentiment: {score}"
                    )
                    signal = TradeSignal(
                        id=self.ID, symbol=symbol, action=TradeAction.SHORT
                    )
                    signals.append(signal)
                elif len(sells) in range(1, self.max_trades + 1):
                    if (
                        self.calculate_pct_change(current_price, max(sells))
                        >= self.ext_th / 2
                    ):
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
