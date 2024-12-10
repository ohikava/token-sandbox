import threading
import time
import streamlit as st
import requests
import pandas as pd


st.title("Token Sandbox")
all_ca = requests.get("http://localhost:5001/getallca").json()['ca']

state = {
    "slope": 0,
    "intercept": 0,
    "ca": all_ca[0]
}


@st.fragment(run_every="1s")
def plot_price_history():
    data = requests.get(f"http://localhost:5001/getpricehistory?ca={state['ca']}").json()['priceHistory']
    priceses = [i['price'] for i in data]
    index = [i['timestamp'] for i in data]

    df = pd.DataFrame({"price": priceses}, index=index)
    df['trend'] = state["slope"] * df.index + state["intercept"]

    st.line_chart(df)

@st.fragment(run_every="1s")
def plot_tx():
    data = requests.get(f"http://localhost:5001/gettx?ca={state['ca']}").json()['tx']
    df = pd.DataFrame(data, columns=["type", "sender", "amount_in", "amount_out", "price", "timestamp"])
    df = df.sort_values(by='timestamp', ascending=False)
    df['sender'] = df['sender'].str.slice(0, 4) + "..." + df['sender'].str.slice(-4)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s') + pd.Timedelta(hours=3)
    st.dataframe(df)

@st.fragment(run_every="1s")
def plot_wallets_balances():
    data = requests.get(f"http://localhost:5001/getAllBalances?ca={state['ca']}").json()['balances']
    df = pd.DataFrame(data, columns=["address", "ethBalance", "tokenBalance", "solDelta", "tokenDelta"])
    df['address'] = df['address'].str.slice(0, 4) + "..." + df['address'].str.slice(-4)
    st.dataframe(df)

@st.fragment(run_every="1s")
def plot_stats():
    data = requests.get(f"http://localhost:5001/getAllBalances?ca={state['ca']}").json()['balances']
    df = pd.DataFrame(data, columns=["address", "ethBalance", "tokenBalance", "solDelta", "tokenDelta"])
    df['address'] = df['address'].str.slice(0, 4) + "..." + df['address'].str.slice(-4)
    current_price = requests.get(f"http://localhost:5001/getprice?ca={state['ca']}").json()['price']
    totalSum = df['ethBalance'].sum()
    totalSumTokens = df['tokenBalance'].sum()
    st.text(f"current price: {current_price}")
    st.text(f"total sum: {totalSum}")
    st.text(f"total sum tokens: {totalSumTokens} ~ {round(totalSumTokens * current_price, 2)} SOL")
    holdersN = (df['tokenBalance'] > 1).sum()
    st.text(f"holders number: {holdersN}")
    totalDelta = df['solDelta'].sum()
    st.text(f"total delta: {totalDelta}")
    totalDeltaTokens = df['tokenDelta'].sum()
    st.text(f"total delta tokens: {totalDeltaTokens} ~ {round(totalDeltaTokens * current_price, 2)} SOL")

plot_price_history()
plot_tx()
plot_wallets_balances()
plot_stats()
with st.sidebar:
    ca = st.selectbox("Select ca:", all_ca)
    if ca != state['ca']:
        state['ca'] = ca

    st.text("trend line")
    slope = st.number_input("Enter slope:", step=0.1, format="%.12f")
    intercept = st.number_input("Enter intercept:", step=0.1, format="%.12f")

    if st.button("submit"):
        state["slope"] = slope
        state["intercept"] = intercept

    reset = st.button("reset")
    if reset:
        state["slope"] = 0
        state["intercept"] = 0
        requests.get(f"http://localhost:5001/reset?ca={state['ca']}")
    
    st.text("distribute tokens")
    sol_amount = st.number_input("Enter sol amount:", step=0.1, format="%.4f")
    holders_ratio = st.number_input("Enter holders ratio:", step=0.1, format="%.4f")
    wallets_number = st.number_input("Enter wallets number:", step=1, format="%d", value=50)

    if st.button("distribute"):
        with open("wallets.txt", "r") as f:
            wallets = f.read().split(",")
        wallets = [i.replace('"', '') for i in wallets]
        wallets = wallets[:wallets_number]
        requests.post("http://localhost:5001/distributeTokens", json={"wallets": wallets, "sol_amount": sol_amount, "holders_ratio": holders_ratio, "ca": state['ca']})
    
    st.text("generate random transactions")
    num_txs = st.number_input("Enter number of transactions:", step=1, format="%d", value=20)
    interval = st.number_input("Enter interval (seconds):", step=1, format="%d", value=1)
    regime = st.selectbox("Select regime:", ["buy", "sell", "shuffle"])

    if st.button("generate"):
        requests.post("http://localhost:5001/generateRandomTransactions", json={"num_txs": num_txs, "interval": interval, "regime": regime, "ca": state['ca']})




