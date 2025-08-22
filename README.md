# Strader: Sentiment-Based Signal System

Strader is a desktop application for MetaTrader 5 (MT5) that executes trades based on real-time sentiment analysis of financial assets. It provides a user-friendly graphical user interface (GUI) to configure and run sentiment-based trading strategies.

## Features

- **GUI Interface:** An intuitive interface built with `tkinter` for easy configuration of all trading parameters.
- **MT5 Integration:** Connects directly to your MetaTrader 5 account to execute trades.
- **Sentiment Analysis:** Fetches and analyzes sentiment from sources like Reddit to generate trading signals.
- **Real-time Logging:** A dedicated log panel displays real-time information about the application's status, trades, and errors.
- **Sentiment Visualization:** A bar chart displays the sentiment scores of the configured tickers, updated in real-time.
- **Configurable Strategy:** Customize the trading strategy with parameters like sentiment thresholds, maximum positions, and risk management settings.
- **Configuration Files:** Load MT5 and API credentials from external `.ini` files for convenience and security.

## How it Works

The application follows a simple workflow:

1.  **Connect:** It establishes a connection to the MetaTrader 5 terminal using the provided credentials.
2.  **Fetch Sentiment:** It uses the `bbstrader` library to fetch financial news and social media data for the specified tickers and calculates a sentiment score for each.
3.  **Generate Signals:** Based on the configured thresholds, it generates `LONG` (buy) or `SHORT` (sell) signals.
4.  **Execute Trades:** The signals are sent to the `bbstrader` trading engine, which executes the trades on your MT5 account.
5.  **Monitor and Visualize:** The application continuously monitors sentiment and displays logs and visualizations in the GUI.

## Getting Started

### Prerequisites

- Python 3.8+
- MetaTrader 5 Terminal

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/bbalouki/strader.git
    cd strader
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application:**

    ```bash
    python -m strader
    ```

2.  **Fill in the GUI fields:**

    - **MT5 Terminal Inputs:** Provide the path to your `terminal64.exe`, your MT5 login, password, and server. You can also load these from a config file.
    - **Trading Strategy Inputs:** Enter your API credentials for Reddit and FMP. Provide the list of tickers to trade in the format `MT5_TICKER:YAHOO_FINANCE_TICKER`.
    - **Trading Engine Inputs:** Configure the trading parameters like time frame, risk, and other settings.

3.  **Start the engine:**
    Click the **Submit** button to start the trading engine. The application will start logging its activities and displaying sentiment charts.

## Configuration

You can use `.ini` configuration files to store your credentials securely.

### MT5 Configuration (`mt5.ini`)

Create a file named `mt5.ini` with the following format:

```ini
[MT5]
login = YOUR_MT5_LOGIN
password = YOUR_MT5_PASSWORD
server = YOUR_MT5_SERVER
```

### API Configuration (`api.ini`)

Create a file named `api.ini` for your API keys:

```ini
[API]
reddit_client_id = YOUR_REDDIT_CLIENT_ID
reddit_client_secret = YOUR_REDDIT_CLIENT_SECRET
reddit_user_agent = YOUR_REDDIT_USER_AGENT
fmp_api = YOUR_FMP_API_KEY
```

In the GUI, use the "Load MT5 Config" and "Load API Config" buttons to load these files.

## Dependencies

- [bbstrader](https://pypi.org/project/bbstrader/): The core trading engine and sentiment analysis library.
- `tkinter`: For the graphical user interface.
- `matplotlib`: For plotting sentiment charts.
- `loguru`: For logging.

## Disclaimer

Trading financial markets involves substantial risk and is not suitable for all investors. The developers of this application are not responsible for any financial losses you may incur. Use this application at your own risk.
