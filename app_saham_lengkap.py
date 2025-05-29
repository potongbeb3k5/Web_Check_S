import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json
import os
import smtplib
from email.mime.text import MIMEText
import requests

# === Konfigurasi Streamlit ===
st.set_page_config(page_title="Analisa Saham NASDAQ & IHSG", layout="wide")
st.title("\U0001F4C8 Analisa Saham + Sinyal Beli/Jual + Upload Saham")

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
    st.header("⭐ Watchlist Saham")
    if watchlist:
        for item in watchlist:
            st.markdown(f"- {item}")
    else:
        st.caption("Belum ada saham.")

    st.markdown("## \U0001F4C5 Rentang Tanggal")
    start_date = st.date_input("Dari", datetime.date.today() - datetime.timedelta(days=180))
    end_date = st.date_input("Sampai", datetime.date.today())

    fast_mode = st.checkbox("⚡ Fast Screening: Tampilkan hanya BELI/JUAL")

# === Input manual atau upload ===
st.subheader("\U0001F4E5 Input Kode Saham atau Upload File")
ticker_input = st.text_input("Masukkan kode saham (contoh: AAPL atau BBCA.JK)", "").upper()

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
EMAIL_SENDER = "e.invitiation@gmail.com"
EMAIL_PASSWORD = "Sjmahpe512"
EMAIL_RECEIVER = "mustaqimhidayatulloh@gmail.com"

def send_email_notification(ticker, signal, price):
    subject = f"\U0001F4E2 Sinyal {signal} untuk {ticker}"
    body = f"Sinyal {signal} terdeteksi untuk {ticker} dengan harga terakhir {price:.2f}."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

# === Analisa Saham ===
for ticker in tickers:
    st.divider()
    st.markdown(f"## \U0001F4CA Analisa: `{ticker}`")
    hist = get_data(ticker, start_date, end_date)

    if hist.empty:
        st.error("❌ Data tidak ditemukan.")
        continue

    hist["MA20"] = hist["Close"].rolling(window=20).mean()
    hist["RSI"] = compute_rsi(hist["Close"])
    hist["MACD"], hist["MACD_SIGNAL"] = compute_macd(hist["Close"])
    hist["BB_UPPER"], hist["BB_LOWER"] = compute_bollinger_bands(hist["Close"])

    last_close = hist["Close"].iloc[-1]
    last_ma = hist["MA20"].iloc[-1]
    last_rsi = hist["RSI"].iloc[-1]

    signal = "⚪ Netral"
    signal_color = "gray"
    if last_rsi < 30 and last_close > last_ma:
        signal = "\U0001F7E2 BELI"
        signal_color = "green"
    elif last_rsi > 70 and last_close < last_ma:
        signal = "\U0001F534 JUAL"
        signal_color = "red"

    if fast_mode and signal == "⚪ Netral":
        continue

    st.markdown(f"**Sinyal:** <span style='color:{signal_color}; font-size:24px'>{signal}</span>", unsafe_allow_html=True)
    st.caption(f"\U0001F4CC Harga: {last_close:.2f}, MA20: {last_ma:.2f}, RSI: {last_rsi:.2f}")

    # Kirim notifikasi jika sinyal beli/jual
    if signal in ["\U0001F7E2 BELI", "\U0001F534 JUAL"]:
        send_email_notification(ticker, signal, last_close)

    # Chart
    st.line_chart(hist[["Close", "MA20", "BB_UPPER", "BB_LOWER"]])
    with st.expander("\U0001F4C9 RSI Chart"):
        st.line_chart(hist["RSI"])
    with st.expander("\U0001F4CA MACD Chart"):
        st.line_chart(hist[["MACD", "MACD_SIGNAL"]])
    with st.expander("\U0001F50A Volume"):
        st.bar_chart(hist["Volume"])

st.success("✅ Analisa selesai. Periksa sinyal & grafik di atas.")
