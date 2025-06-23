import sys
import tkinter as tk
from tkinter import messagebox
from strader.gui import SentimentTradingSystem


def main():
    try:
        root = tk.Tk()
        app = SentimentTradingSystem(root)  # noqa: F841
        root.mainloop()
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Fatal Error", str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
