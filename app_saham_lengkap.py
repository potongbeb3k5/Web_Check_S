import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json
import os
import smtplib
from email.mime.text import MIMEText
import plotly.graph_objects as go

# === Konfigurasi Streamlit ===
st.set_page_config(page_title="Analisa Saham & Kripto", layout="wide")
st.title("📈 Analisa Saham & Kripto + Sinyal Beli/Jual + Upload Watchlist")

# === Watchlist ===
WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f)

watchlist = load_watchlist()

with st.sidebar:
    st.header("⭐ Watchlist Saham/Kripto")
    if watchlist:
        for item in watchlist:
            st.markdown(f"- {item}")
    else:
        st.caption("Belum ada kode.")

    st.markdown("## 📅 Rentang Tanggal")
    start_date = st.date_input("Dari", datetime.date.today() - datetime.timedelta(days=180))
    end_date = st.date_input("Sampai", datetime.date.today())

    fast_mode = st.checkbox("⚡ Fast Screening: Tampilkan hanya BELI/JUAL")

# === Input manual atau upload ===
st.subheader("📥 Input Kode Saham/Kripto atau Upload File")
ticker_input = st.text_input("Masukkan kode saham atau kripto (contoh: AAPL, BBCA.JK, BTC-USD, ETH-USD)", "").upper()

uploaded_file = st.file_uploader("Atau upload file .csv/.xlsx (dengan kolom 'ticker')", type=["csv", "xlsx"])

def read_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    return None

if uploaded_file:
    df_upload = read_uploaded_file(uploaded_file)
    tickers = df_upload['ticker'].dropna().unique().tolist()
elif ticker_input:
    tickers = [ticker_input]
else:
    tickers = []

# === Fungsi Ambil Data & Indikator ===
@st.cache_data
def get_data(ticker, start, end):
    return yf.Ticker(ticker).history(start=start, end=end)

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def compute_bollinger_bands(series, window=20, num_std=2):
    ma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = ma + (std * num_std)
    lower = ma - (std * num_std)
    return upper, lower

# === Notifikasi Email ===
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"
EMAIL_RECEIVER = "receiver_email@gmail.com"

def send_email_notification(ticker, signal, price):
    subject = f"📢 Sinyal {signal} untuk {ticker}"
    body = f"Sinyal {signal} terdeteksi untuk {ticker} dengan harga terakhir {price:.2f}."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

# === Tab Saham & Kripto ===
tab_saham, tab_kripto = st.tabs(["🏢 Saham", "🔐 Kripto"])

def display_analysis(ticker):
    hist = get_data(ticker, start_date, end_date)
    if hist.empty or 'Close' not in hist.columns:
        st.error(f"❌ Data tidak ditemukan untuk {ticker}.")
        return

    hist["MA20"] = hist["Close"].rolling(window=20).mean()
    hist["RSI"] = compute_rsi(hist["Close"])
    hist["MACD"], hist["MACD_SIGNAL"] = compute_macd(hist["Close"])
    hist["BB_UPPER"], hist["BB_LOWER"] = compute_bollinger_bands(hist["Close"])

    if hist[["Close", "MA20", "RSI", "MACD", "MACD_SIGNAL"]].dropna().empty:
        st.warning(f"⚠️ Data historis untuk analisa belum cukup tersedia ({ticker}).")
        return

    last_close = hist["Close"].iloc[-1]
    last_ma = hist["MA20"].iloc[-1]
    last_rsi = hist["RSI"].iloc[-1]
    last_macd = hist["MACD"].iloc[-1]
    last_signal = hist["MACD_SIGNAL"].iloc[-1]

    signal = "⚪ Netral"
    signal_color = "gray"
    if last_rsi < 40 and last_close > last_ma and last_macd > last_signal:
        signal = "🟢 BELI"
        signal_color = "green"
    elif last_rsi > 60 and last_close < last_ma and last_macd < last_signal:
        signal = "🔴 JUAL"
        signal_color = "red"

    if fast_mode and signal == "⚪ Netral":
        return

    st.markdown(f"## 📊 Analisa: `{ticker}`")
    st.markdown(f"**Sinyal:** <span style='color:{signal_color}; font-size:24px'>{signal}</span>", unsafe_allow_html=True)
    st.caption(f"📌 Harga: {last_close:.2f}, MA20: {last_ma:.2f}, RSI: {last_rsi:.2f}, MACD: {last_macd:.2f}, Signal: {last_signal:.2f}")

    if signal in ["🟢 BELI", "🔴 JUAL"]:
        send_email_notification(ticker, signal, last_close)

    # Chart Candlestick + MA + BB
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,
                                 open=hist['Open'], high=hist['High'],
                                 low=hist['Low'], close=hist['Close'],
                                 name='Candlestick'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], mode='lines', name='MA20'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_UPPER'], mode='lines', name='BB Upper'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_LOWER'], mode='lines', name='BB Lower'))
    fig.update_layout(title=f"Candlestick Chart - {ticker}", xaxis_title="Tanggal", yaxis_title="Harga")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📉 RSI Chart"):
        st.line_chart(hist["RSI"])
    with st.expander("📊 MACD Chart"):
        st.line_chart(hist[["MACD", "MACD_SIGNAL"]])
    with st.expander("🔊 Volume"):
        st.bar_chart(hist["Volume"])

# Jalankan analisa per kategori
ticker_saham = [t for t in tickers if not t.endswith("-USD")]
ticker_kripto = [t for t in tickers if t.endswith("-USD")]

with tab_saham:
    for ticker in ticker_saham:
        st.divider()
        display_analysis(ticker)

with tab_kripto:
    for ticker in ticker_kripto:
        st.divider()
        display_analysis(ticker)

st.success("✅ Analisa selesai. Periksa sinyal & grafik di atas.")
