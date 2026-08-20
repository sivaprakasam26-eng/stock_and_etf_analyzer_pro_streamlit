import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Stock Intelligence Pro",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Intelligence Pro")
st.caption("Research dashboard for comparing stocks using price momentum, technical indicators, and fundamentals.")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Analysis Settings")

    period = st.selectbox(
        "Historical period",
        ["6mo", "1y", "2y", "5y"],
        index=1
    )

    st.subheader("Scoring Weights")

    momentum_weight = st.slider(
        "Momentum",
        0, 40, 30
    )

    trend_weight = st.slider(
        "Trend",
        0, 40, 25
    )

    fundamental_weight = st.slider(
        "Fundamentals",
        0, 40, 30
    )

    technical_weight = st.slider(
        "Technical",
        0, 40, 15
    )

    st.divider()

    st.info(
        "The score is a research signal, not a guarantee of future performance."
    )

# ============================================================
# INPUT
# ============================================================

tickers_input = st.text_input(
    "Enter stock tickers",
    "AAPL, MSFT, NVDA, GOOGL, AMZN",
    help="Enter one or more ticker symbols separated by commas."
)

tickers = [
    ticker.strip().upper()
    for ticker in tickers_input.split(",")
    if ticker.strip()
]

analyze_button = st.button(
    "🔍 Analyze Stocks",
    type="primary",
    use_container_width=True
)

# ============================================================
# INDICATORS
# ============================================================

def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def calculate_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return macd, signal


def calculate_bollinger(series, period=20):
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()

    upper = middle + (2 * std)
    lower = middle - (2 * std)

    return middle, upper, lower


# ============================================================
# STOCK ANALYSIS
# ============================================================

def analyze_stock(ticker):

    try:

        stock = yf.Ticker(ticker)

        hist = stock.history(
            period=period,
            auto_adjust=True
        )

        if hist.empty:
            return None

        info = stock.info

        # NEW: get name + description

        name = info.get("longName") or info.get("shortName") or ticker
        description = info.get("longBusinessSummary", "No description available.")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

        close = hist["Close"]

        # -------------------------
        # Moving averages
        # -------------------------

        hist["MA20"] = close.rolling(20).mean()
        hist["MA50"] = close.rolling(50).mean()
        hist["MA200"] = close.rolling(200).mean()

        # -------------------------
        # RSI
        # -------------------------

        hist["RSI"] = calculate_rsi(close)

        # -------------------------
        # MACD
        # -------------------------

        hist["MACD"], hist["MACD_SIGNAL"] = calculate_macd(close)

        hist["MACD_HIST"] = (
            hist["MACD"] - hist["MACD_SIGNAL"]
        )

        # -------------------------
        # Bollinger Bands
        # -------------------------

        (
            hist["BB_MIDDLE"],
            hist["BB_UPPER"],
            hist["BB_LOWER"]
        ) = calculate_bollinger(close)

        latest = hist.iloc[-1]

        current_price = float(latest["Close"])

        # ====================================================
        # MOMENTUM SCORE
        # ====================================================

        momentum_points = 0

        return_1m = (
            close.iloc[-1] / close.iloc[-22] - 1
            if len(close) >= 22 else 0
        )

        return_3m = (
            close.iloc[-1] / close.iloc[-63] - 1
            if len(close) >= 63 else 0
        )

        return_6m = (
            close.iloc[-1] / close.iloc[-126] - 1
            if len(close) >= 126 else 0
        )

        if return_1m > 0:
            momentum_points += 1

        if return_3m > 0:
            momentum_points += 1

        if return_6m > 0:
            momentum_points += 1

        momentum_score = momentum_points / 3

        # ====================================================
        # TREND SCORE
        # ====================================================

        trend_points = 0

        if current_price > latest["MA50"]:
            trend_points += 1

        if current_price > latest["MA200"]:
            trend_points += 1

        if latest["MA50"] > latest["MA200"]:
            trend_points += 1

        trend_score = trend_points / 3

        # ====================================================
        # TECHNICAL SCORE
        # ====================================================

        technical_points = 0

        rsi = latest["RSI"]

        # Healthy momentum zone
        if 45 <= rsi <= 65:
            technical_points += 2

        elif 35 <= rsi < 45:
            technical_points += 1

        elif 65 < rsi <= 70:
            technical_points += 1

        # MACD
        if latest["MACD"] > latest["MACD_SIGNAL"]:
            technical_points += 1

        # Price relative to Bollinger middle
        if current_price > latest["BB_MIDDLE"]:
            technical_points += 1

        technical_score = technical_points / 4

        # ====================================================
        # FUNDAMENTAL SCORE
        # ====================================================

        pe = info.get("trailingPE")

        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")

        profit_margin = info.get("profitMargins")

        debt_to_equity = info.get("debtToEquity")

        fundamental_points = 0
        fundamental_possible = 0

        # Revenue growth
        if revenue_growth is not None:
            fundamental_possible += 1

            if revenue_growth > 0.10:
                fundamental_points += 1

        # Earnings growth
        if earnings_growth is not None:
            fundamental_possible += 1

            if earnings_growth > 0.10:
                fundamental_points += 1

        # Profit margin
        if profit_margin is not None:
            fundamental_possible += 1

            if profit_margin > 0.10:
                fundamental_points += 1

        # Valuation
        if pe is not None and pe > 0:
            fundamental_possible += 1

            if pe < 30:
                fundamental_points += 1

        # Debt
        if debt_to_equity is not None:
            fundamental_possible += 1

            if debt_to_equity < 100:
                fundamental_points += 1

        if fundamental_possible > 0:
            fundamental_score = (
                fundamental_points / fundamental_possible
            )
        else:
            fundamental_score = 0.5

        # ====================================================
        # FINAL SCORE
        # ====================================================

        total_weight = (
            momentum_weight
            + trend_weight
            + fundamental_weight
            + technical_weight
        )

        final_score = (
            momentum_score * momentum_weight
            + trend_score * trend_weight
            + fundamental_score * fundamental_weight
            + technical_score * technical_weight
        ) / total_weight * 100

        # ====================================================
        # SIGNAL
        # ====================================================

        if final_score >= 75:
            signal = "🟢 Strong"
        elif final_score >= 60:
            signal = "🟢 Positive"
        elif final_score >= 45:
            signal = "🟡 Neutral"
        elif final_score >= 30:
            signal = "🟠 Weak"
        else:
            signal = "🔴 Poor"

        return {
            "Ticker": ticker,
            "Name": name,                    # ✅ NEW
            "Description": description,      # ✅ NEW
            "Sector": sector,                # ✅ NEW
            "Industry": industry,            # ✅ NEW
            "Score": round(final_score, 1),
            "Signal": signal,
            "Price": current_price,
            "RSI": round(float(rsi), 1),
            "P/E": round(float(pe), 2) if pe else None,
            "Revenue Growth": revenue_growth,
            "1M Return": return_1m,
            "3M Return": return_3m,
            "6M Return": return_6m,
            "Momentum": round(momentum_score * 100, 1),
            "Trend": round(trend_score * 100, 1),
            "Fundamentals": round(fundamental_score * 100, 1),
            "Technical": round(technical_score * 100, 1),
            "Hist": hist
        }

    except Exception as e:

        st.warning(
            f"Could not analyze {ticker}: {str(e)}"
        )

        return None


# ============================================================
# RUN ANALYSIS
# ============================================================

if analyze_button:

    if not tickers:

        st.error("Please enter at least one ticker.")

        st.stop()

    results = []

    progress = st.progress(0)

    with st.spinner("Fetching market data and calculating indicators..."):

        for index, ticker in enumerate(tickers):

            result = analyze_stock(ticker)

            if result:
                results.append(result)

            progress.progress(
                (index + 1) / len(tickers)
            )

    progress.empty()

    # ========================================================
    # RESULTS
    # ========================================================

    if not results:

        st.error(
            "No valid stock data was returned. Check the ticker symbols."
        )

        st.stop()

    results = sorted(
        results,
        key=lambda x: x["Score"],
        reverse=True
    )

    # ========================================================
    # TOP PICK
    # ========================================================

    top = results[0]

    st.success(
        f"🏆 Highest Research Score: {top['Ticker']} — {top['Score']}/100 ({top['Signal']})"
    )

    # ========================================================
    # SUMMARY CARDS
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Top Stock",
            top["Ticker"]
        )

    with col2:
        st.metric(
            "Score",
            f"{top['Score']}/100"
        )

    with col3:
        st.metric(
            "RSI",
            top["RSI"]
        )

    with col4:
        st.metric(
            "Price",
            f"${top['Price']:,.2f}"
        )

    # ========================================================
    # RANKINGS
    # ========================================================

    st.subheader("🏆 Stock Rankings")

    ranking_data = []

    for result in results:

        ranking_data.append({
            "Rank": len(ranking_data) + 1,
            "Ticker": result["Ticker"],
            "Score": result["Score"],
            "Signal": result["Signal"],
            "Price": round(result["Price"], 2),
            "RSI": result["RSI"],
            "Momentum": result["Momentum"],
            "Trend": result["Trend"],
            "Fundamentals": result["Fundamentals"],
            "Technical": result["Technical"],
            "1M": f"{result['1M Return'] * 100:.1f}%",
            "3M": f"{result['3M Return'] * 100:.1f}%",
            "6M": f"{result['6M Return'] * 100:.1f}%"
        })

    ranking_df = pd.DataFrame(ranking_data)

    st.dataframe(
        ranking_df,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # STOCK TABS
    # ========================================================

    st.subheader("📊 Detailed Stock Analysis")

    tabs = st.tabs(
        [result["Ticker"] for result in results]
    )

    for tab, stock in zip(tabs, results):

        with tab:

            hist = stock["Hist"]

            st.header(
                f"{stock['Ticker']} — {stock['Signal']} : {stock['Name']} , Sector: {stock['Sector']}, Industry: {stock['Industry']}"
            )

            # ------------------------------------------------
            # METRICS
            # ------------------------------------------------

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                st.metric(
                    "Score",
                    f"{stock['Score']}/100"
                )

            with c2:
                st.metric(
                    "Price",
                    f"${stock['Price']:,.2f}"
                )

            with c3:
                st.metric(
                    "RSI",
                    stock["RSI"]
                )

            with c4:
                st.metric(
                    "P/E",
                    stock["P/E"]
                    if stock["P/E"] is not None
                    else "N/A"
                )

            with c5:
                st.metric(
                    "6M Return",
                    f"{stock['6M Return'] * 100:.1f}%"
                )

            # ------------------------------------------------
            # PRICE CHART
            # ------------------------------------------------

            st.subheader("📈 Price & Moving Averages")

            fig_price = go.Figure()

            fig_price.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["Close"],
                    name="Price",
                    mode="lines"
                )
            )

            fig_price.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["MA20"],
                    name="MA20",
                    mode="lines"
                )
            )

            fig_price.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["MA50"],
                    name="MA50",
                    mode="lines"
                )
            )

            fig_price.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["MA200"],
                    name="MA200",
                    mode="lines"
                )
            )

            fig_price.update_layout(
                height=500,
                xaxis_title="Date",
                yaxis_title="Price",
                hovermode="x unified"
            )

            st.plotly_chart(
                fig_price,
                use_container_width=True,
                key=f"price_chart_{stock['Ticker']}"
            )

            # ------------------------------------------------
            # INDICATOR COLUMNS
            # ------------------------------------------------

            indicator_col1, indicator_col2 = st.columns(2)

            # ------------------------------------------------
            # RSI
            # ------------------------------------------------

            with indicator_col1:

                st.subheader("📉 RSI")

                fig_rsi = go.Figure()

                fig_rsi.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["RSI"],
                        name="RSI",
                        mode="lines"
                    )
                )

                fig_rsi.add_hline(
                    y=70,
                    line_dash="dash"
                )

                fig_rsi.add_hline(
                    y=30,
                    line_dash="dash"
                )

                fig_rsi.update_layout(
                    height=350,
                    yaxis=dict(
                        range=[0, 100]
                    ),
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig_rsi,
                    use_container_width=True,
                    key=f"rsi_chart_{stock['Ticker']}"
                )

            # ------------------------------------------------
            # MACD
            # ------------------------------------------------

            with indicator_col2:

                st.subheader("📊 MACD")

                fig_macd = go.Figure()

                fig_macd.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["MACD"],
                        name="MACD",
                        mode="lines"
                    )
                )

                fig_macd.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["MACD_SIGNAL"],
                        name="Signal",
                        mode="lines"
                    )
                )

                fig_macd.add_trace(
                    go.Bar(
                        x=hist.index,
                        y=hist["MACD_HIST"],
                        name="Histogram"
                    )
                )

                fig_macd.update_layout(
                    height=350,
                    hovermode="x unified"
                )

                st.plotly_chart(
                    fig_macd,
                    use_container_width=True,
                    key=f"macd_chart_{stock['Ticker']}"
                )

            # ------------------------------------------------
            # BOLLINGER BANDS
            # ------------------------------------------------

            st.subheader("📏 Bollinger Bands")

            fig_bb = go.Figure()

            fig_bb.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["Close"],
                    name="Price",
                    mode="lines"
                )
            )

            fig_bb.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["BB_UPPER"],
                    name="Upper Band",
                    mode="lines"
                )
            )

            fig_bb.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["BB_MIDDLE"],
                    name="Middle",
                    mode="lines"
                )
            )

            fig_bb.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["BB_LOWER"],
                    name="Lower Band",
                    mode="lines"
                )
            )

            fig_bb.update_layout(
                height=450,
                hovermode="x unified"
            )

            st.plotly_chart(
                fig_bb,
                use_container_width=True,
                key=f"bb_chart_{stock['Ticker']}"
            )

            # ------------------------------------------------
            # SCORE BREAKDOWN
            # ------------------------------------------------

            st.subheader("🧠 Score Breakdown")

            score_df = pd.DataFrame({
                "Factor": [
                    "Momentum",
                    "Trend",
                    "Fundamentals",
                    "Technical"
                ],
                "Score": [
                    stock["Momentum"],
                    stock["Trend"],
                    stock["Fundamentals"],
                    stock["Technical"]
                ]
            })

            fig_score = go.Figure(
                go.Bar(
                    x=score_df["Factor"],
                    y=score_df["Score"],
                    text=score_df["Score"],
                    textposition="auto"
                )
            )

            fig_score.update_layout(
                height=350,
                yaxis=dict(
                    range=[0, 100],
                    title="Score"
                )
            )

            st.plotly_chart(
                fig_score,
                use_container_width=True,
                key=f"score_chart_{stock['Ticker']}"
            )

            # ------------------------------------------------
            # RETURNS
            # ------------------------------------------------

            st.subheader("📅 Performance")

            r1, r2, r3 = st.columns(3)

            with r1:
                st.metric(
                    "1 Month",
                    f"{stock['1M Return'] * 100:.2f}%"
                )

            with r2:
                st.metric(
                    "3 Months",
                    f"{stock['3M Return'] * 100:.2f}%"
                )

            with r3:
                st.metric(
                    "6 Months",
                    f"{stock['6M Return'] * 100:.2f}%"
                )

            # ------------------------------------------------
            # RAW DATA
            # ------------------------------------------------

            with st.expander("View calculated data"):

                st.dataframe(
                    hist.tail(100),
                    use_container_width=True
                )

else:

    st.info(
        "Enter your tickers above and click **🔍 Analyze Stocks** to begin."
    )