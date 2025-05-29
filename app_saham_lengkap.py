import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import json
import os

# === Konfigurasi Streamlit ===
st.set_page_config(page_title="Analisa Saham NASDAQ & IHSG", layout="wide")
st.title("📈 Analisa Saham + Sinyal Beli/Jual + Upload Saham")

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

# === Pilih tanggal ===
st.sidebar.markdown("## 📅 Rentang Tanggal")
start_date = st.sidebar.date_input("Dari", datetime.date.today() - datetime.timedelta(days=180))
end_date = st.sidebar.date_input("Sampai", datetime.date.today())

# === Input manual atau upload ===
st.subheader("📥 Input Kode Saham atau Upload File")
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

# === Fungsi Ambil Data & Hitung RSI ===
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

# === Tampilkan hasil analisa ===
for ticker in tickers:
    st.divider()
    st.markdown(f"## 📊 Analisa: `{ticker}`")
    hist = get_data(ticker, start_date, end_date)

    if hist.empty:
        st.error("❌ Data tidak ditemukan.")
        continue

    hist["MA20"] = hist["Close"].rolling(window=20).mean()
    hist["RSI"] = compute_rsi(hist["Close"])

    last_close = hist["Close"].iloc[-1]
    last_ma = hist["MA20"].iloc[-1]
    last_rsi = hist["RSI"].iloc[-1]

    signal = "⚪ Netral"
    signal_color = "gray"
    if last_rsi < 30 and last_close > last_ma:
        signal = "🟢 BELI"
        signal_color = "green"
    elif last_rsi > 70 and last_close < last_ma:
        signal = "🔴 JUAL"
        signal_color = "red"

    st.markdown(f"**Sinyal:** <span style='color:{signal_color}; font-size:24px'>{signal}</span>", unsafe_allow_html=True)
    st.caption(f"📌 Harga: {last_close:.2f}, MA20: {last_ma:.2f}, RSI: {last_rsi:.2f}")

    st.line_chart(hist[["Close", "MA20"]])
    with st.expander("📉 RSI Chart"):
        st.line_chart(hist["RSI"])
