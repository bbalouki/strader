import threading
import tkinter as tk
from tkinter import StringVar, filedialog, messagebox, scrolledtext, ttk

import matplotlib
import matplotlib.pyplot as plt
from bbstrader.trading.execution import MT5_ENGINE_TIMEFRAMES, Mt5ExecutionEngine
from loguru import logger
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from strader import inputs
from strader.strategy import SentimentTrading

matplotlib.use("TkAgg")

SYMBOLS_TYPE = ["stock", "etf", "future", "forex", "crypto", "index"]


class SentimentTradingApp(object):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.title("Sentiment-Based Signal System")
        root.geometry("1600x900")

        self.trade_engine = None
        self.pending_prompt = None
        self._chart_update_job = None
        self.prompt_response_ready = threading.Event()
        self.prompt_response_value = None
        self._last_sentiments = {}
        self.setup_layout(root)

    def on_close(self):
        if self._chart_update_job is not None:
            try:
                self.root.after_cancel(self._chart_update_job)
            except Exception:
                pass
            self._chart_update_job = None

        if self.trade_engine:
            self.trade_engine.stop()

        # Breaks out of mainloop
        self.root.quit()
        # Fully destroys GUI
        self.root.destroy()

    def setup_layout(self, root: tk.Tk):
        # Columns
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=3)
        root.grid_columnconfigure(2, weight=4)

        # Rows
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=0)

        # Left - Inputs
        self._input_frame = ttk.Frame(root, padding=5)
        self._input_frame.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.build_scrollable_input_panel(self._input_frame)

        # Center - Logs
        self.log_frame = ttk.Frame(root, padding=10)
        self.log_frame.grid(row=0, column=1, sticky="nsew")

        # Bottom Left (prompt input)
        self.prompt_frame = ttk.Frame(root, padding=(10, 0))
        self.prompt_frame.grid(row=1, column=1, sticky="ew")

        # Right - Charts
        self.chart_frame = ttk.Frame(root, padding=10)
        self.chart_frame.grid(row=0, column=2, rowspan=2, sticky="nsew")

        self.build_inputs()
        self.build_logs()
        self.build_prompt()
        self.build_charts()

    def build_scrollable_input_panel(self, parent):
        """
        Creates a scrollable input panel for the GUI.
        This panel will contain all the input fields for the MT5 terminal,
        trading strategy, and engine inputs.
        The panel is designed to be scrollable to accommodate many input fields.

        :param parent: The parent widget to contain the scrollable panel.
        :return: None
        """
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        # Create canvas and scrollbar
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.input_frame = ttk.Frame(canvas)

        # Bind scroll region
        self.input_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.input_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Layout
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable scrolling with mouse wheel
        self.input_frame.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"),
        )

    def browse_path(self):
        """Open a file dialog to select the MT5 terminal executable."""
        file_path = filedialog.askopenfilename(
            title="Select MT5 Terminal Executable",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")],
        )
        if file_path:
            self.mt5_path.delete(0, tk.END)
            self.mt5_path.insert(0, file_path)
            self.log(f"Selected MT5 Terminal Path: {file_path}")

    def load_config_from_file(self, name):
        """Load configuration from a file and populate input fields."""
        config_file_path = filedialog.askopenfilename(
            title=f"Select {name} File",
            filetypes=[("INI Files", "*.ini"), ("All Files", "*.*")],
        )
        # If the user cancels the dialog, config_file_path will be empty
        if not config_file_path:
            self.log("Configuration loading cancelled by user.")
            return None
        if config_file_path:
            try:
                config = inputs.load_config(config_file_path)
                self.log(f"Successfully loaded {name} from {config_file_path}")
                return config
            except Exception as e:
                messagebox.showerror(
                    "Loading Error",
                    f"Failed to load or parse the configuration file.\n\nError: {e}, "
                    f"Please make sure you enter {name} manually or load them from a file",
                )
                return None

    def build_terminal_inputs(self):
        """Builds the input fields for MT5 terminal connection details."""
        ttk.Label(
            self.input_frame, text="MT5 TERMINAL INPUTS", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(20, 0))

        path_frame = ttk.Frame(self.input_frame)
        path_frame.pack(fill="x", pady=10)

        # Label in column 0
        ttk.Label(path_frame, text="Terminal Path", font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="e", padx=5
        )

        # Entry in column 1
        self.mt5_path = ttk.Entry(path_frame, width=30)
        self.mt5_path.grid(row=0, column=1, padx=5)

        # Browse Button in column 2
        ttk.Button(path_frame, text="Browse", command=self.browse_path).grid(
            row=0, column=2, padx=5
        )

        label_frame = ttk.LabelFrame(self.input_frame, text="MT5 Credentials")
        label_frame.pack(pady=10, fill="x", padx=5)

        # Login
        ttk.Label(label_frame, text="Login", font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="e", padx=5, pady=3
        )
        self.mt5_login = ttk.Entry(label_frame, width=30)
        self.mt5_login.grid(row=0, column=1, padx=5, pady=3)

        # Password
        ttk.Label(label_frame, text="Password", font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="e", padx=5, pady=3
        )
        self.mt5_password = ttk.Entry(label_frame, show="*", width=30)
        self.mt5_password.grid(row=1, column=1, padx=5, pady=3)

        # Server
        ttk.Label(label_frame, text="Server", font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="e", padx=5, pady=3
        )
        self.mt5_server = ttk.Entry(label_frame, width=30)
        self.mt5_server.grid(row=2, column=1, padx=5, pady=3)
        ttk.Button(
            label_frame,
            text="Load MT5 Config",
            command=self.populate_mt5_inputs_from_config,
        ).grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 10))

    def populate_mt5_inputs_from_config(self):
        """Populate GUI fields from config file."""
        config = self.load_config_from_file("MT5 Credentials")
        if not config:
            return
        # Check if the file contains the required [MT5] section
        if "MT5" in config:
            # 1. Clear the current content of the entry fields
            self.mt5_login.delete(0, tk.END)
            self.mt5_password.delete(0, tk.END)
            self.mt5_server.delete(0, tk.END)

            # 2. Insert the new values from the config file
            self.mt5_login.insert(0, config["MT5"].get("login", ""))
            self.mt5_password.insert(0, config["MT5"].get("password", ""))
            self.mt5_server.insert(0, config["MT5"].get("server", ""))
        else:
            message = "The selected file does not contain an [MT5] section."
            self.log(message)
            messagebox.showwarning("Invalid File", message)

    def populate_api_inputs_from_config(self):
        """Populate GUI fields from config file."""
        config = self.load_config_from_file("API Credentials")
        if not config:
            return
        if "API" in config:
            # 1. Clear the current content of the entry fields
            self.reddit_client_id.delete(0, tk.END)
            self.reddit_client_secret.delete(0, tk.END)
            self.reddit_user_agent.delete(0, tk.END)
            self.fmp_api.delete(0, tk.END)

            # 2. Insert the new values from the config file
            self.reddit_client_id.insert(0, config["API"].get("reddit_client_id", ""))
            self.reddit_client_secret.insert(
                0, config["API"].get("reddit_client_secret", "")
            )
            self.reddit_user_agent.insert(0, config["API"].get("reddit_user_agent", ""))
            self.fmp_api.insert(0, config["API"].get("fmp_api", ""))
        else:
            message = "The selected file does not contain an [API] section."
            self.log(message)
            messagebox.showwarning("Invalid File", message)

    def load_tickers_from_file(self):
        """Load tickers from a text file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        # Stop if the user cancelled the dialog
        if not file_path:
            self.log("Ticker loading cancelled by user.")
            return
        try:
            with open(file_path, "r") as f:
                tickers = f.read().strip()
            self.ticker_text.delete("1.0", tk.END)
            self.ticker_text.insert(tk.END, tickers)
            self.log(f"Loaded tickers from file: {file_path}")
        except Exception as e:
            self.log(f"Error loading file: {e}")
            error_message = f"Failed to read the ticker file.\n\nError: {e}"
            self.log(error_message)
            messagebox.showerror("File Error", error_message)

    def build_strategy_inputs(self):
        """Builds the input fields for trading strategy configuration."""
        ttk.Label(
            self.input_frame,
            text="TRADING STRATEGY INPUTS",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(10, 0))

        label_frame = ttk.LabelFrame(self.input_frame, text="APIs and Secrets")
        label_frame.pack(pady=10, fill="x", padx=5)

        # client_id
        ttk.Label(label_frame, text="Reddit Client ID", font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="e", padx=5, pady=3
        )
        self.reddit_client_id = ttk.Entry(label_frame, width=30, show="*")
        self.reddit_client_id.grid(row=1, column=1, padx=5, pady=3)

        # client_secret
        ttk.Label(label_frame, text="Reddit Client Secret", font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="e", padx=5, pady=3
        )
        self.reddit_client_secret = ttk.Entry(label_frame, width=30, show="*")
        self.reddit_client_secret.grid(row=2, column=1, padx=5, pady=3)

        # user_agent
        ttk.Label(label_frame, text="Reddit User Agent", font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="e", padx=5, pady=3
        )
        self.reddit_user_agent = ttk.Entry(label_frame, width=30, show="*")
        self.reddit_user_agent.grid(row=3, column=1, padx=5, pady=3)

        # fmp_api
        ttk.Label(label_frame, text="FMP API Key", font=("Segoe UI", 9)).grid(
            row=4, column=0, sticky="e", padx=5, pady=3
        )
        self.fmp_api = ttk.Entry(label_frame, width=30, show="*")
        self.fmp_api.grid(row=4, column=1, padx=5, pady=3)

        ttk.Button(
            label_frame,
            text="Load API Config",
            command=self.populate_api_inputs_from_config,
        ).grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        kwargs_label_frame = ttk.LabelFrame(self.input_frame, text="Other Parameters")
        kwargs_label_frame.pack(pady=10, fill="x", padx=5)

        # Row 0 - Ticker label
        ttk.Label(
            kwargs_label_frame,
            text="Tickers (MT5_ticker:Ticker)",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        # Row 1 - Ticker input (Text widget)
        self.ticker_text = tk.Text(kwargs_label_frame, height=5, width=40)
        self.ticker_text.grid(row=1, column=0, columnspan=2, padx=5, pady=3)

        # Row 2 - Load button below ticker text
        ttk.Button(
            kwargs_label_frame,
            text="Load from File",
            command=self.load_tickers_from_file,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        # Row 3 Symbol type
        DEFAULT_SYMBOS_TYPE = "stock"
        ttk.Label(kwargs_label_frame, text="Symbol type", font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="e", padx=5, pady=3
        )
        self.symbls_type = StringVar()
        self.symbls_type.set(DEFAULT_SYMBOS_TYPE)
        self.symbls_type_dropdown = ttk.Combobox(
            kwargs_label_frame,
            textvariable=self.symbls_type,
            values=SYMBOLS_TYPE,
            state="readonly",
            width=25,
        )
        self.symbls_type_dropdown.grid(row=3, column=1, padx=5, pady=3, sticky="w")

        # Row 4 - Sentiment Threshold
        ttk.Label(
            kwargs_label_frame, text="Sentiment Threshold", font=("Segoe UI", 9)
        ).grid(row=4, column=0, sticky="e", padx=5, pady=3)

        self.threshold = ttk.Entry(kwargs_label_frame, width=30)
        self.threshold.grid(row=4, column=1, padx=5, pady=3, sticky="w")
        self.threshold.insert(0, "0.2")

        # Row 5 - Maximum Positions
        ttk.Label(
            kwargs_label_frame, text="Maximum Positions", font=("Segoe UI", 9)
        ).grid(row=5, column=0, sticky="e", padx=5, pady=3)

        self.max_positions = ttk.Entry(kwargs_label_frame, width=30)
        self.max_positions.grid(row=5, column=1, padx=5, pady=3, sticky="w")
        self.max_positions.insert(0, "100")

        # Row 6 - Expected Return Threshold
        ttk.Label(
            kwargs_label_frame, text="Expected Return (%)", font=("Segoe UI", 9)
        ).grid(row=6, column=0, sticky="e", padx=5, pady=3)

        self.expected_return = ttk.Entry(kwargs_label_frame, width=30)
        self.expected_return.grid(row=6, column=1, padx=5, pady=3, sticky="w")
        self.expected_return.insert(0, "5.0")

    def build_engine_inputs(self):
        """Builds the input fields for trading engine configuration."""
        ttk.Label(
            self.input_frame,
            text="TRADING ENGINE INPUTS",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(10, 0))

        params_frame = ttk.LabelFrame(self.input_frame, text="Parameters")
        params_frame.pack(fill="x", padx=5, pady=10)

        # Time Frame
        DEFAULT_TIMEFRAME = "15m"
        ttk.Label(params_frame, text="Time Frame", font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="e", padx=5, pady=3
        )
        self.time_frame = StringVar()
        self.time_frame.set(DEFAULT_TIMEFRAME)
        self.time_frame_dropdown = ttk.Combobox(
            params_frame,
            textvariable=self.time_frame,
            values=MT5_ENGINE_TIMEFRAMES,
            state="readonly",
            width=25,
        )
        self.time_frame_dropdown.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        # Starting time (HH:MM)
        ttk.Label(
            params_frame, text="Starting Time (HH:MM)", font=("Segoe UI", 9)
        ).grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.start_time = ttk.Entry(params_frame, width=25)
        self.start_time.grid(row=1, column=1, padx=5, pady=3)
        self.start_time.insert(0, "00:00")

        # Finishing time (HH:MM)
        # Stopping new entries
        ttk.Label(
            params_frame, text="Finishing Time (HH:MM)", font=("Segoe UI", 9)
        ).grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.finish_time = ttk.Entry(params_frame, width=25)
        self.finish_time.grid(row=2, column=1, padx=5, pady=3)
        self.finish_time.insert(0, "23:59")

        # Ending time (HH:MM)
        # closing all positions
        ttk.Label(params_frame, text="Ending Time (HH:MM)", font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="e", padx=5, pady=3
        )
        self.end_time = ttk.Entry(params_frame, width=25)
        self.end_time.grid(row=3, column=1, padx=5, pady=3)
        self.end_time.insert(0, "23:59")

        # Iteration Time
        ttk.Label(params_frame, text="Iteration Time (min)", font=("Segoe UI", 9)).grid(
            row=4, column=0, sticky="e", padx=5, pady=3
        )
        self.iter_time = ttk.Entry(params_frame, width=25)
        self.iter_time.grid(row=4, column=1, padx=5, pady=3)
        self.iter_time.insert(0, "15")

        # Daily Risk
        ttk.Label(params_frame, text="Risk/trade (%)", font=("Segoe UI", 9)).grid(
            row=5, column=0, sticky="e", padx=5, pady=3
        )
        self.daily_risk = ttk.Entry(params_frame, width=25)
        self.daily_risk.grid(row=5, column=1, padx=5, pady=3)
        self.daily_risk.insert(0, "0.01")

        # Max Risk
        ttk.Label(params_frame, text="Max Risk (%)", font=("Segoe UI", 9)).grid(
            row=6, column=0, sticky="e", padx=5, pady=3
        )
        self.max_risk = ttk.Entry(params_frame, width=25)
        self.max_risk.grid(row=6, column=1, padx=5, pady=3)
        self.max_risk.insert(0, "10.0")

        # Toggle Options
        row_index = 7
        toggle_options = [
            ("Enable MM", "mm_enabled"),
            ("Enable Auto Trade", "auto_trade_enabled"),
            ("Enable Debugging", "debug_mode_enabled"),
            ("Enable Notifications", "notification_enabled"),
        ]

        for label, var_name in toggle_options:
            setattr(self, var_name, StringVar(value="False"))
            ttk.Checkbutton(
                params_frame,
                text=label,
                variable=getattr(self, var_name),
                onvalue="True",
                offvalue="False",
            ).grid(row=row_index, column=0, columnspan=2, sticky="w", padx=5)
            row_index += 1

        # Trading Periods
        ttk.Label(params_frame, text="Trading Period", font=("Segoe UI", 9)).grid(
            row=row_index, column=0, sticky="w", padx=5, pady=(10, 0)
        )
        self.trading_periods = StringVar(value="month")

        periods = [
            ("Monthly", "month"),
            ("Weekly", "week"),
            ("Daily", "day"),
            ("24/7", "24/7"),
        ]
        for i, (label, value) in enumerate(periods):
            ttk.Radiobutton(
                params_frame,
                text=label,
                variable=self.trading_periods,
                value=value,
            ).grid(
                row=row_index + 1 + i,
                column=0,
                columnspan=2,
                sticky="w",
                padx=20,
                pady=1,
            )

    def build_inputs(self):
        """Builds all input fields for the GUI."""
        self.build_terminal_inputs()
        self.build_strategy_inputs()
        self.build_engine_inputs()
        ttk.Button(self.input_frame, text="Submit", command=self.handle_submit).pack(
            pady=10
        )

    def zoom_log_area(self, event):
        """Zoom in/out the log area text size with Ctrl + Mouse Wheel."""
        if event.delta > 0:
            self.log_font_size = min(self.log_font_size + 1, 30)
        else:
            self.log_font_size = max(self.log_font_size - 1, 6)

        self.log_area.configure(font=("Courier", self.log_font_size))

    def build_logs(self):
        """Builds the log area for displaying messages."""
        text = "Sentiment-Based Trading System"
        ttk.Label(self.log_frame, text=text, font=("Segoe UI", 30, "bold")).pack(
            anchor="w"
        )
        self.log_font_size = 10
        self.log_area = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=25,
            font=("Courier", self.log_font_size),
        )
        self.log_area.pack(fill="both", expand=True)
        self.log_area.insert(tk.END, "Welcome to the Sentiment-Based Signal System.\n")
        self.log_area.bind("<Control-MouseWheel>", self.zoom_log_area)

    def build_prompt(self):
        """Builds the prompt input area for user responses."""
        label = ttk.Label(
            self.prompt_frame,
            text="Enter response (if prompted)",
            font=("Segoe UI", 10),
        )
        label.pack(side="left", padx=(0, 5))

        self.prompt_entry = ttk.Entry(self.prompt_frame, width=60)
        self.prompt_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        send_btn = ttk.Button(
            self.prompt_frame, text="Send", command=self.handle_prompt_response
        )
        send_btn.pack(side="left")

    def gui_safe_prompt(self, prompt):
        """Safely handles prompts in the GUI thread."""
        self.pending_prompt = prompt
        self.prompt_response_value = None
        self.prompt_response_ready.clear()

        self.root.after(0, self.log(prompt))

        # Wait for the response to be set by the user
        self.prompt_response_ready.wait()
        return self.prompt_response_value

    def handle_prompt_response(self):
        """Handles the user's response to a prompt."""
        user_input = self.prompt_entry.get()
        self.prompt_entry.delete(0, tk.END)  # Clear the entry field

        self.log(f">>> User input: {user_input}")

        if self.pending_prompt:
            self.prompt_response_value = user_input
            self.prompt_response_ready.set()
            self.pending_prompt = None

    def initialize_engine(self, symbols_list, trades, **kwargs):
        """Initializes the trading engine with the provided parameters."""
        if hasattr(self, "trade_engine") and self.trade_engine:
            # Stop any existing engine before starting a new one
            self.trade_engine.stop()
        self.trade_engine = Mt5ExecutionEngine(
            symbols_list,
            trades,
            SentimentTrading,
            prompt_callback=self.gui_safe_prompt,
            **kwargs,
        )
        threading.Thread(target=self.trade_engine.run, daemon=True).start()

    def get_inputs(self):
        """Collects and validates all input fields from the GUI."""
        tickers = inputs.get_tickers(self.ticker_text.get("1.0", tk.END).strip())
        mt5_path = inputs.get_mt5_path(self.mt5_path.get().strip())
        mt5_login = inputs.validate_input(
            self.mt5_login.get().strip(), int, "MT5 Login"
        )
        daily_risk = (
            inputs.validate_input(
                self.daily_risk.get().strip(), float, "Daily Risk (percentage)"
            )
            if self.daily_risk.get().strip()
            else 0.01
        )
        max_risk = (
            inputs.validate_input(
                self.max_risk.get().strip(), float, "Max Risk (percentage)"
            )
            if self.max_risk.get().strip()
            else 10.0
        )
        threshold = (
            inputs.validate_input(
                self.threshold.get().strip(), float, "Sentiment Threshold"
            )
            if self.threshold.get().strip()
            else 0.2
        )
        max_positions = (
            inputs.validate_input(
                self.max_positions.get().strip(), int, "Max Positions"
            )
            if self.max_positions.get().strip()
            else 100
        )  # Default value for

        # Expected return
        expected_return = (
            inputs.validate_input(
                self.expected_return.get().strip(), float, "Expected Return"
            )
            if self.expected_return.get().strip()
            else 5.0
        )
        iter_time = (
            inputs.validate_input(self.iter_time.get().strip(), int, "Iteration Time")
            if self.iter_time.get().strip()
            else 15
        )  # Default value for iteration time
        mm_enabled = self.mm_enabled.get() == "True"
        auto_trade_enabled = self.auto_trade_enabled.get() == "True"
        debug_mode_enabled = self.debug_mode_enabled.get() == "True"
        notification_enabled = self.notification_enabled.get() == "True"

        return (
            tickers,
            mt5_path,
            mt5_login,
            daily_risk,
            max_risk,
            threshold,
            max_positions,
            expected_return,
            iter_time,
            mm_enabled,
            auto_trade_enabled,
            debug_mode_enabled,
            notification_enabled,
        )

    def handle_submit(self):
        """Handles the submission of input fields and initializes the trading engine."""
        # Collect inputs from the GUI
        (
            tickers,
            mt5_path,
            mt5_login,
            daily_risk,
            max_risk,
            threshold,
            max_positions,
            expected_return,
            iter_time,
            mm_enabled,
            auto_trade_enabled,
            debug_mode_enabled,
            notification_enabled,
        ) = self.get_inputs()

        if not all(
            [
                tickers,
                mt5_path,
                mt5_login,
                self.mt5_password.get().strip(),
                self.mt5_server.get().strip(),
            ]
        ):
            err_msg = "MT5 Credentials missing, Please fill in all fields, (e.g., login, password, server, path)"
            self.log(err_msg)
            messagebox.showerror("Invalid Credentilas", err_msg)
            return

        if (
            not self.time_frame.get().strip()
            or self.time_frame.get().strip() not in MT5_ENGINE_TIMEFRAMES
        ):
            err_msg = (
                f"Please select a valid time frame, e.g., ({MT5_ENGINE_TIMEFRAMES}) "
            )
            self.log(err_msg)
            messagebox.showerror("Invalid Time frame", err_msg)
            return

        if self.trading_periods.get().strip() not in ["month", "week", "day", "24/7"]:
            err_msg = (
                "Please select a valid trading period, e.g., (month, week, day, 24/7)"
            )
            self.log(err_msg)
            messagebox.showerror("Invalid period", err_msg)
            return
        if self.symbls_type.get().strip() not in SYMBOLS_TYPE:
            err_msg = (
                f"Please select a valid symbols_type, e.g., ({','.join(SYMBOLS_TYPE)})"
            )
            self.log(err_msg)
            messagebox.showerror("Invalid Symbol type", err_msg)
            return

        self.log("Initializing trading engine...")

        def gui_safe_logger(msg):
            # Ensures GUI thread safety
            self.log_frame.after(0, self.log(msg))

        logger.add(
            gui_safe_logger,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} {level} {message}",
        )

        mt5_con_kwargs = {
            "path": mt5_path,
            "login": mt5_login,
            "password": self.mt5_password.get().strip(),
            "server": self.mt5_server.get().strip(),
            "copy": True,
        }
        symbols_list = list(tickers.keys())
        max_trades = int(max_positions / len(symbols_list))
        trade_kwargs = {
            **mt5_con_kwargs,
            "expert_id": SentimentTrading.ID,
            "time_frame": self.time_frame.get().strip(),
            "start_time": self.start_time.get().strip(),
            "finishing_time": self.finish_time.get().strip(),
            "ending_time": self.end_time.get().strip(),
            "max_trades": max_trades,
            "max_risk": max_risk,
            "daily_risk": daily_risk,
            "logger": logger,
        }
        trade_instances = inputs.get_trade_instances(symbols_list, trade_kwargs)
        del trade_kwargs["logger"]
        del trade_kwargs["max_trades"]

        strategy_kwargs = {
            "symbols": tickers,
            "symbols_type": self.symbls_type.get().strip(),
            "threshold": threshold,
            "max_positions": max_positions,
            "expected_return": expected_return,
            "client_id": self.reddit_client_id.get().strip(),
            "client_secret": self.reddit_client_secret.get().strip(),
            "user_agent": self.reddit_user_agent.get().strip(),
            "fmp_api": self.fmp_api.get().strip(),
            "max_trades": max_trades,
            "logger": logger,
        }

        engine_kwargs = {
            "mm": mm_enabled,
            "auto_trade": auto_trade_enabled,
            "iter_time": iter_time,
            "period": self.trading_periods.get().strip(),
            "comment": f"{SentimentTrading.NAME}",
            "account": f"{mt5_login}@{self.mt5_server.get().strip().split('-')[0]}",
            "strategy_name": SentimentTrading.NAME,
            "debug_mode": debug_mode_enabled,
            "notify": notification_enabled,
            "optimizer": None,
            **trade_kwargs,
            **strategy_kwargs,
        }

        self.initialize_engine(
            symbols_list,
            trade_instances,
            **engine_kwargs,
        )
        # Start live chart update loop
        self.start_chart_update_loop()

    def start_chart_update_loop(self, interval_ms=5000):
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return  # Do not schedule if window is closed

        self.update_charts(self.get_sentiments())

        # Cancel previous job if any
        if self._chart_update_job is not None:
            try:
                self.root.after_cancel(self._chart_update_job)
            except Exception:
                pass

        # Reschedule new job and store the reference
        self._chart_update_job = self.root.after(
            interval_ms,
            self.start_chart_update_loop,  # Not lambda anymore
        )

    def get_sentiments(self):
        if not hasattr(self, "trade_engine") or not self.trade_engine:
            return {}
        return self.trade_engine.strategy.sentiments

    def build_charts(self):
        self.chart_canvas = None
        self.update_charts(self.get_sentiments())

    def update_charts(self, sentiment_dict: dict):
        if not self.root.winfo_exists():
            return
        if sentiment_dict == self._last_sentiments:
            return  # Skip replot if nothing has changed
        self._last_sentiments = sentiment_dict
        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
        threshold = (
            inputs.validate_input(
                self.threshold.get().strip(), float, "Sentiment Threshold"
            )
            if self.threshold.get().strip()
            else 0.2
        )
        # only plot sentiments values > self.threshold
        sentiment_dict = {
            k: v for k, v in sentiment_dict.items() if abs(v) >= threshold / 2
        }
        # sort by sentiment score
        sentiment_dict = dict(
            sorted(sentiment_dict.items(), key=lambda item: item[1], reverse=True)
        )
        tickers = list(sentiment_dict.keys())
        scores = list(sentiment_dict.values())
        colors = ["green" if s >= 0 else "red" for s in scores]

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(tickers, scores, color=colors)
        ax.axvline(0, color="black", linewidth=1)
        ax.set_title("Top Positive & Negative Ticker Sentiments")
        ax.set_xlabel("Sentiment Score")
        ax.set_ylabel("Tickers")

        fig.tight_layout()
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
