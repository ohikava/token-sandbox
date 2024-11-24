from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from sandbox import Sandbox

app = FastAPI()

class Transaction(BaseModel):
    amount: float
    slippage: float
    walletAddress: str

class PriceHistoryResponse(BaseModel):
    priceHistory: List[dict]

class DistributionBody(BaseModel):
    wallets: List[str]
    sol_amount: float
    holders_ratio: float

class PriceResponse(BaseModel):
    price: float

sandbox = Sandbox(token_supply=1000000, pooled_sol=100, decimals=9, fee=0.0001) 

@app.get("/getreserves")
def get_reserves():
    return {"solReserves": sandbox.sol_balance, "tokenReserves": sandbox.token_balance}

@app.get("/getbalance/{public_key}")
def get_balance(public_key: str):
    return {"balance": sandbox.get_balance(public_key)}

@app.get("/gettokenbalance/{public_key}")
def get_token_balance(public_key: str):
    return {"tokenBalance": sandbox.get_token_balance(public_key)}

@app.post("/buy")
def buy(transaction: Transaction):
    sandbox.buy(transaction.walletAddress, transaction.amount)
    return {"message": "Bought"}

@app.post("/sell")
def sell(transaction: Transaction):
    sandbox.sell(transaction.walletAddress, transaction.amount)
    return {"message": "Sold"}

@app.get("/getprice", response_model=PriceResponse)
def get_price():
    return {"price": sandbox.get_price()}

@app.get("/getpricehistory", response_model=PriceHistoryResponse)
def get_price_history():
    return {"priceHistory": sandbox.price_history}

@app.get("/getAllBalances")
def get_all_balances():
    wallets = sandbox.get_all_wallets()
    balances = [{"address": wallet, "ethBalance": sandbox.get_balance(wallet), "tokenBalance": sandbox.get_token_balance(wallet)} for wallet in wallets]
    return {"balances": balances}

@app.get("/reloadState")
def reload_state():
    sandbox.reloadState()
    return {"message": "State reloaded"}

@app.get("/getwalletchanges")
def get_wallet_changes():
    changes = sandbox.getWalletChanges()
    changes_list = [{"address": address, "ethChange": change.ethChange, "tokenChange": change.tokenChange} for address, change in changes.items()]
    return {"changes": changes_list}

@app.post("/distributeTokens")
def distribute_tokens(body: DistributionBody):
    sandbox.distribute_tokens(body.wallets, body.sol_amount, body.holders_ratio)
    return {"message": "Tokens distributed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
