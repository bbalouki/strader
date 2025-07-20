import configparser
from pathlib import Path
from tkinter import messagebox
from typing import Dict, List, Type

from bbstrader.metatrader.trade import Trade, create_trade_instance


def load_config(filepath):
    config = configparser.ConfigParser(interpolation=None)
    if not Path(filepath).exists():
        messagebox.showerror(
            "Input Error", f"Configuration file '{filepath}' not found."
        )
    config.read(filepath)
    return config


def validate_input(input, input_type: Type, log_name: str):
    """
    Validates the input against the specified type.
    Raises ValueError if the input is not of the specified type.

    :param input: The input value to validate.
    :param input_type: The expected type of the input.
    :param log_name: The name of the input for logging purposes.
    :return: The input converted to the specified type if valid.
    """
    try:
        return input_type(input)
    except Exception as e:
        messagebox.showerror(
            "Input Error",
            f"Invalid input for {log_name}: {e}, Must be of type {input_type.__name__}",
        )


def get_tickers(tickers: str) -> Dict[str, str]:
    """
    Parses a string of tickers into a dictionary.
    The string should be formatted as "MT5_ticker1:ticker1, MT5_ticker2:ticker2,...".

    :param tickers: A string containing tickers in the specified format.
    :return: A dictionary mapping tickers to their MT5 equivalents.
    :raises ValueError: If the input string is empty or improperly formatted.
    """
    if not tickers:
        messagebox.showerror("Input Error", "Tickers string cannot be empty.")
    string = tickers.strip().replace("\n", "").replace(" ", "").replace('"""', "")
    if string.endswith(","):
        string = string[:-1]
    return dict(item.split(":") for item in string.split(","))


def get_mt5_path(path: str):
    """
    Validates the provided MT5 path.
    The path must point to the 'terminal64.exe' executable.

    :param path: The path to the MT5 executable.
    :return: The validated path.
    :raises ValueError: If the path is invalid or does not point to 'terminal64.exe'.
    """
    error = "MT5 Error"
    if not path or not Path(path).exists():
        messagebox.showerror(error, "Invalid MT5 path provided.")
    if not path.endswith("terminal64.exe"):
        messagebox.showerror(
            error,
            "MT5 path must end with 'terminal64.exe'. Please provide the correct path.",
        )
    return path


def get_trade_instances(mt5_tickers: List[str], trade_kwargs: Dict) -> Dict[str, Trade]:
    """
    Creates trade instances for each ticker using the provided arguments.

    :param mt5_tickers: A list of MT5 ticker strings.
    :param trade_kwargs: A dictionary of arguments to pass to the Trade constructor.
    :return: A dictionary mapping each ticker to its corresponding Trade instance.
    """
    if not mt5_tickers:
        messagebox.showerror("Input Error", "MT5 tickers list cannot be empty.")
    return create_trade_instance(mt5_tickers, trade_kwargs)
