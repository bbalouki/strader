import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

from strader.gui import SentimentTradingApp


def resource_path(relative_path):
    """Get absolute path to resource"""
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path


ICON_PATH = resource_path("assets/bbstrader.ico")


def main():
    try:
        root = tk.Tk()
        root.iconbitmap(ICON_PATH)
        app = SentimentTradingApp(root)  # noqa: F841
        root.mainloop()
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        error_details = f"{e}\n\n{traceback.format_exc()}"
        messagebox.showerror("Fatal Error", error_details)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        error_details = f"{e}\n\n{traceback.format_exc()}"
        messagebox.showerror("Fatal Error", error_details)
        sys.exit(1)
