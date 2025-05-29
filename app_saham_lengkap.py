import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import os

st.set_page_config(page_title="Saham NASDAQ & IHSG", layout="wide")
st.title("📊 Analisis Saham + Sinyal Beli/Jual + Watchlist")

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
        st.caption("Belum ada saham favorit.")

# === Input Saham ===
ticker = st.text_input("Masukkan kode saham (contoh: AAPL atau BBCA.JK)", "AAPL").upper()

# Tombol simpan ke watchlist
if st.button("⭐ Simpan ke Watchlist"):
    if ticker not in watchlist:
        watchlist.append(ticker)
        save_watchlist(watchlist)
        st.success(f"{ticker} ditambahkan ke watchlist.")

# === Caching data harga dan info saham ===
@st.cache_data
def load_price_data(ticker):
    return yf.Ticker(ticker).history(period="6mo")

@st.cache_data
def load_stock_info(ticker):
    return yf.Ticker(ticker).info

# === Load data ===
hist = load_price_data(ticker)
info = load_stock_info(ticker)

if hist.empty:
    st.error("Data tidak ditemukan.")
    st.stop()

# === Moving Average & RSI ===
hist['MA20'] = hist['Close'].rolling(window=20).mean()
hist['RSI'] = ta.rsi(hist['Close'], length=14)

# === Sinyal Beli/Jual ===
last_close = hist['Close'].iloc[-1]
last_ma20 = hist['MA20'].iloc[-1]
last_rsi = hist['RSI'].iloc[-1]

signal = "-"
if last_rsi < 30 and last_close > last_ma20:
    signal = "🟢 **SINYAL BELI**"
elif last_rsi > 70 and last_close < last_ma20:
    signal = "🔴 **SINYAL JUAL**"
else:
    signal = "⚪ **Tunggu / Netral**"

st.subheader(f"📢 Sinyal untuk {ticker}: {signal}")
st.caption(f"📌 RSI: {last_rsi:.2f}, MA20: {last_ma20:.2f}, Harga Terakhir: {last_close:.2f}")

# === Grafik Harga ===
st.subheader("📈 Grafik Harga + MA")
st.line_chart(hist[['Close', 'MA20']])

# === Indikator RSI ===
with st.expander("📉 RSI"):
    st.line_chart(hist['RSI'])

# === Info Saham ===
with st.expander("ℹ️ Ringkasan Saham"):
    st.markdown(f"""
    **Nama:** {info.get('longName', '-')}
    
    **Sektor:** {info.get('sector', '-')}
    
    **Harga Sekarang:** ${info.get('currentPrice', '-')}  
    **Target Harga:** {info.get('targetMeanPrice', '-')}  
    **PER (PE Ratio):** {info.get('trailingPE', '-')}  
    **Market Cap:** {info.get('marketCap', '-')}
    """)
    st.write(info.get("longBusinessSummary", "-"))
