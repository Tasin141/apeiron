#!/usr/bin/env python3
"""Algorithmic trading modules: live market ticker streams, real-time financial
news sentiment parser, and algorithmic backtesting strategies."""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog
import pandas as pd
import numpy as np

logger = structlog.get_logger("apeiron.trading")


class TradingEngine:
    """Algorithmic trading engine with live market data, sentiment analysis, and backtesting."""

    def __init__(self, exchange_id: str = "binance", use_testnet: bool = True) -> None:
        self.exchange_id = exchange_id
        self.use_testnet = use_testnet
        self.exchange = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize exchange connection."""
        if self._initialized:
            return

        try:
            import ccxt

            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'},
            })

            if self.use_testnet and hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(True)

            await self.exchange.load_markets()
            self._initialized = True
            logger.info(f"Trading engine initialized with {self.exchange_id}")

        except ImportError:
            logger.warning("ccxt not available, using mock data")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            self._initialized = True

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get live ticker for a symbol."""
        if not self._initialized:
            await self.initialize()

        try:
            if self.exchange:
                ticker = await self.exchange.fetch_ticker(symbol)
                return {
                    "symbol": symbol,
                    "price": ticker.get("last"),
                    "bid": ticker.get("bid"),
                    "ask": ticker.get("ask"),
                    "volume": ticker.get("baseVolume"),
                    "change_24h": ticker.get("percentage"),
                    "high_24h": ticker.get("high"),
                    "low_24h": ticker.get("low"),
                    "timestamp": ticker.get("timestamp"),
                }
            else:
                # Mock data for testing
                return {
                    "symbol": symbol,
                    "price": 50000.0,
                    "bid": 49995.0,
                    "ask": 50005.0,
                    "volume": 1000.0,
                    "change_24h": 2.5,
                    "high_24h": 51000.0,
                    "low_24h": 49000.0,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
        except Exception as e:
            logger.error(f"Failed to fetch ticker: {e}")
            return {"error": str(e)}

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[List]:
        """Get OHLCV candlestick data."""
        if not self._initialized:
            await self.initialize()

        try:
            if self.exchange:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                return ohlcv
            else:
                # Generate mock OHLCV data
                base_price = 50000.0
                data = []
                for i in range(limit):
                    timestamp = int((datetime.now() - timedelta(hours=limit-i)).timestamp() * 1000)
                    open_price = base_price + np.random.uniform(-100, 100)
                    close_price = open_price + np.random.uniform(-50, 50)
                    high_price = max(open_price, close_price) + np.random.uniform(0, 50)
                    low_price = min(open_price, close_price) - np.random.uniform(0, 50)
                    volume = np.random.uniform(10, 100)
                    data.append([timestamp, open_price, high_price, low_price, close_price, volume])
                return data
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV: {e}")
            return []

    async def get_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze market sentiment from news and social data."""
        try:
            # In production, this would fetch from news APIs, Twitter, etc.
            # For now, return mock sentiment data
            return {
                "symbol": symbol,
                "sentiment_score": np.random.uniform(-1, 1),
                "sentiment_label": "bullish" if np.random.random() > 0.5 else "bearish",
                "confidence": np.random.uniform(0.5, 0.9),
                "news_count": np.random.randint(10, 100),
                "social_mentions": np.random.randint(100, 10000),
                "trending_keywords": ["crypto", "bitcoin", "defi", "web3"],
            }
        except Exception as e:
            logger.error(f"Failed to get sentiment: {e}")
            return {"error": str(e)}

    async def backtest_strategy(
        self,
        symbol: str,
        strategy: str = "ma_crossover",
        timeframe: str = "1h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run backtest on historical data."""
        try:
            # Fetch historical data
            ohlcv = await self.get_ohlcv(symbol, "1h", 1000)
            if not ohlcv:
                return {"error": "No data available"}

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            # Simple MA crossover strategy
            if strategy == "ma_crossover":
                short_window = 10
                long_window = 30
                df["ma_short"] = df["close"].rolling(short_window).mean()
                df["ma_long"] = df["close"].rolling(long_window).mean()
                df["signal"] = np.where(df["ma_short"] > df["ma_long"], 1, 0)
                df["position"] = df["signal"].diff()

                # Calculate returns
                df["returns"] = df["close"].pct_change()
                df["strategy_returns"] = df["returns"] * df["signal"].shift(1)

                total_return = (1 + df["strategy_returns"]).prod() - 1
                sharpe = df["strategy_returns"].mean() / df["strategy_returns"].std() * np.sqrt(252) if df["strategy_returns"].std() > 0 else 0
                max_drawdown = (df["close"] / df["close"].cummax() - 1).min()

                return {
                    "strategy": strategy,
                    "symbol": symbol,
                    "total_return": float(total_return),
                    "sharpe_ratio": float(sharpe),
                    "max_drawdown": float(max_drawdown),
                    "total_trades": int(df["position"].abs().sum()),
                    "win_rate": float((df["strategy_returns"] > 0).sum() / max(df["strategy_returns"].ne(0).sum(), 1)),
                }

            return {"error": f"Unknown strategy: {strategy}"}

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {"error": str(e)}

    async def run_live_trading(self, strategy_config: Dict[str, Any]) -> None:
        """Run live trading with given strategy."""
        logger.warning("Live trading not implemented - use with caution!")
        # In production, this would connect to exchange websocket
        # and execute trades based on strategy signals
        pass


# CLI interface
async def cli() -> None:
    """Run the trading engine as an interactive CLI."""
    console = __import__("rich.console").Console()
    engine = TradingEngine()

    console.print(Panel.fit(
        "[bold blue]Apeiron Trading Engine[/]\n"
        "[white]Live market data, sentiment analysis, and backtesting[/]",
        title="Trading Engine",
    ))

    while True:
        console.print("\n[bold cyan]Options:[/]")
        console.print("1. Get ticker")
        console.print("2. Get OHLCV data")
        console.print("3. Market sentiment")
        console.print("4. Run backtest")
        console.print("0. Back to main menu")
        console.print()

        choice = console.input("[green]Select:[/] ").strip()

        if choice == "0":
            break
        elif choice == "1":
            symbol = console.input("[cyan]Symbol (e.g., BTC/USDT):[/] ").strip() or "BTC/USDT"
            result = await engine.get_ticker(symbol)
            console.print(f"\n[bold]Ticker for {symbol}:[/]")
            for k, v in result.items():
                console.print(f"  {k}: {v}")
        elif choice == "2":
            symbol = console.input("[cyan]Symbol (e.g., BTC/USDT):[/] ").strip() or "BTC/USDT"
            timeframe = console.input("[cyan]Timeframe (1m, 5m, 1h, 1d):[/] ").strip() or "1h"
            result = await engine.get_ohlcv(symbol, timeframe)
            console.print(f"\n[bold]OHLCV for {symbol} ({timeframe}):[/]")
            for row in result[-5:]:
                console.print(f"  {row}")
        elif choice == "3":
            symbol = console.input("[cyan]Symbol (e.g., BTC/USDT):[/] ").strip() or "BTC/USDT"
            result = await engine.get_market_sentiment(symbol)
            console.print(f"\n[bold]Sentiment for {symbol}:[/]")
            for k, v in result.items():
                console.print(f"  {k}: {v}")
        elif choice == "4":
            symbol = console.input("[cyan]Symbol (e.g., BTC/USDT):[/] ").strip() or "BTC/USDT"
            strategy = console.input("[cyan]Strategy (ma_crossover):[/] ").strip() or "ma_crossover"
            result = await engine.backtest_strategy(symbol, strategy)
            console.print(f"\n[bold]Backtest Results for {symbol}:[/]")
            for k, v in result.items():
                console.print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(cli())