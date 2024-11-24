import threading
import pandas as pd
import requests
import streamlit as st
import time
import queue
import random 



q = queue.Queue()

state = {"price_history": [], "slope": [], "intercept": []}
def test_run():
    while True:
        r = requests.get("http://localhost:5001/getpricehistory")
        if r.status_code == 200:
            q.put(r.json()["priceHistory"])
        time.sleep(1)


def update_dashboard():
    with st.sidebar:
        slope = st.number_input("Enter slope:", step=0.000000001, format="%.12f")
        intercept = st.number_input("Enter intercept:", step=0.000000001, format="%.12f")

        submit = st.button("Submit")
        if submit:
            if "slope" in st.session_state and "intercept" in st.session_state:
                current_session_slopes = st.session_state['slope'].split(";")
                current_session_intercepts = st.session_state['intercept'].split(";")
                current_session_slopes.append(slope)
                current_session_intercepts.append(intercept)
                print(slope, intercept)
                
                st.session_state['slope'] = ";".join(map(str, current_session_slopes))
                st.session_state['intercept'] = ";".join(map(str, current_session_intercepts))
            else:
                st.session_state['slope'] = str(slope)
                st.session_state['intercept'] = str(intercept)
            submit = False

    while True:
        new_price_history = q.get()
        if len(new_price_history) > len(state["price_history"]):
            state["price_history"] = new_price_history
            prices = [i['price'] for i in state["price_history"]]
            index = [i['timestamp'] for i in state["price_history"]]
            df = pd.DataFrame({"price": prices}, index=index)
            if "slope" in st.session_state and "intercept" in st.session_state:
                slopes = st.session_state['slope'].split(";")
                intercepts = st.session_state['intercept'].split(";")
                for i in range(len(slopes)):
                    df["line_{}".format(i)] = float(slopes[i]) * df.index + float(intercepts[i])
                    
            st.line_chart(df)



threading.Thread(target=test_run).start()

# dashboard title
st.title("Streamlit Learning")

with st.empty():
    update_dashboard()
