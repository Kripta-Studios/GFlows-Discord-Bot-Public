from dash import html, dcc
import dash_bootstrap_components as dbc
from yfinance import Tickers
from os import environ

def format_ticker(ticker):
    return f"{ticker[1:]}" if ticker[0] == "^" else ticker

def serve_layout():
    tickers_list = (environ.get("TICKERS") or "^SPX,^NDX,^RUT").strip().split(",")
    tickers = Tickers(tickers_list)
    ticker_info = {ticker: tickers.tickers[ticker].info for ticker in tickers_list}
    
    return html.Div(
        [
            dcc.Store(id="theme-store", storage_type="local", data=[dbc.themes.DARKLY, dbc.themes.FLATLY]),
            dcc.Store(id="exp-value", storage_type="local"),
            dcc.Store(id="refresh"),
            dcc.Interval(id="interval", interval=1000 * 3 * 1, n_intervals=0),
            dcc.Interval(id="plot-interval", interval=1000 * 10, n_intervals=0),  # Reduced to 10 seconds for testing
            dcc.Download(id="export-df-csv"),
            html.A(
                [
                    html.Img(
                        src="https://ko-fi.com/favicon.ico",
                        style={"height": "1rem", "margin-right": "0.5rem"},
                    ),
                    "Buy me a coffee",
                ],
                href="https://ko-fi.com/gammaflows",
                target="_blank",
                id="kofi-link-color",
                className="link-light",
            ),
            html.H1("Gamma Flows", className="text-center"),
            html.H2("Real-time Options Flow", className="text-center"),
            html.Hr(),
            dbc.Row(
                dbc.Tabs(
                    id="tabs",
                    children=[
                        dbc.Tab(
                            label=(
                                f"{ticker_info[ticker]['longName']} ({format_ticker(ticker)})"
                                if isinstance(ticker_info[ticker], dict)
                                else format_ticker(ticker)
                            ),
                            tab_id=format_ticker(ticker),
                            active_label_class_name="fw-bold",
                        )
                        for ticker in tickers_list
                    ],
                    class_name="fs-5 px-4 nav-fill",
                    persistence=True,
                    persistence_type="local",
                )
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(html.H4("Expirations"), className="mx-auto"),
                            dbc.ButtonGroup(
                                children=[
                                    html.Div(
                                        dcc.Dropdown(
                                            options=[
                                                {"label": html.Div(className="line-1-horizontal"), "value": "monthly-btn"},
                                                {"label": html.Div(className="line-1-horizontal"), "value": "opex-btn"},
                                                {"label": html.Div(className="line-1-horizontal"), "value": "0dte-btn"},
                                            ],
                                            id="monthly-options",
                                            placeholder="Monthly",
                                            searchable=False,
                                            clearable=False,
                                            className="d-flex h-100 border border-primary btn-outline-primary align-items-center",
                                            persistence=True,
                                            persistence_type="local",
                                        ),
                                        className="w-50",
                                    ),
                                    dbc.Button(
                                        "All",
                                        id="all-btn",
                                        color="primary",
                                        active=False,
                                        outline=True,
                                        n_clicks=0,
                                    ),
                                ],
                                id="exp-btns",
                            ),
                        ],
                        class_name="d-flex flex-column mt-2",
                    ),
                    dbc.Col(
                        [
                            html.Div(html.H4("Greeks"), className="mx-auto"),
                            dcc.Store(id="greek-value", storage_type="local"),
                            dbc.ButtonGroup(
                                children=[
                                    dbc.Button("Delta", id="delta-btn", color="primary", outline=True, n_clicks=0),
                                    dbc.Button("Gamma", id="gamma-btn", color="primary", outline=True, n_clicks=0),
                                    dbc.Button("Vanna", id="vanna-btn", color="primary", outline=True, n_clicks=0),
                                    dbc.Button("Charm", id="charm-btn", color="primary", outline=True, n_clicks=0),
                                ],
                                id="greek-btns",
                                class_name="overflow-auto",
                            ),
                        ],
                        class_name="d-flex flex-column mt-2",
                    ),
                    dbc.Col(
                        [
                            html.H4("Chart Options"),
                            dbc.DropdownMenu(
                                [
                                    dbc.DropdownMenuItem("Chart Data", id="btn-chart-data"),
                                    dbc.DropdownMenuItem("Significant Points", id="btn-sig-points"),
                                ],
                                label="Export",
                                id="export-menu",
                            ),
                            html.Label(
                                [
                                    "Dark Theme",
                                    dbc.Switch(id="switch", value=True, className="ms-2"),
                                ],
                                className="ms-2",
                            ),
                            dbc.Button(
                                "Ko-Fi",
                                id="kofi-btn",
                                color="light",
                                className="ms-2",
                                href="https://ko-fi.com/gammaflows",
                                external_link=True,
                            ),
                        ],
                        class_name="d-flex flex-column mt-2",
                    ),
                ],
                class_name="mx-2",
            ),
            dbc.Row(  # Changed from dcc.Row to dbc.Row
                dcc.Dropdown(
                    placeholder="",
                    clearable=False,
                    searchable=False,
                    id="live-dropdown",
                    persistence=True,
                    persistence_type="local",
                ),
                class_name="mt-2",
            ),
            html.Hr(),
            dcc.Loading(
                id="loading-icon",
                children=[
                    dbc.Row(
                        dcc.Graph(
                            id="live-chart",
                            responsive=True,
                            style={"display": "none"},
                        ),
                        class_name="vw-100 vh-100 mt-0",
                    ),
                    html.Hr(),
                    dbc.Accordion(
                        [
                            dbc.AccordionItem(
                                [
                                    html.P(
                                        "Delta Exposure represents the expected change in an option's price for a $1 change in the underlying asset's price."
                                    ),
                                    html.P(
                                        "The Absolute Delta Exposure is the total delta exposure for all options at a given strike price."
                                    ),
                                    html.P(
                                        "The Delta Exposure Profile represents the delta exposure across a range of price levels, for all expiries, the next expiry, and the next monthly expiry."
                                    ),
                                ],
                                title="Delta",
                            ),
                            # ... (other accordion items for Gamma, Vanna, Charm)
                        ],
                        start_collapsed=True,
                    ),
                ],
                type="default",
            ),
        ],
        className="mx-2",
    )
