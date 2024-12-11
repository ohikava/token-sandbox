import asyncio
import time
import uuid
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from typing import List, Set
from sandbox import Sandbox
import concurrent.futures

app = FastAPI()

class Transaction(BaseModel):
    amount: float
    slippage: float
    walletAddress: str
    ca: str

class PriceHistoryResponse(BaseModel):
    priceHistory: List[dict]

class DistributionBody(BaseModel):
    wallets: List[str]
    sol_amount: float
    holders_ratio: float
    ca: str

class PriceResponse(BaseModel):
    price: float

class RandomTransactionsBody(BaseModel):
    num_txs: int
    interval: int
    regime: str
    ca: str
CA = [
    "4gaFmTcPiDzH6iGF57BbRi2ZXG7yLqUXh1hFHuZXpump",
    "3D63Em2RZQAFU9pPKE7JBRkHgw1VeqMQc1udkeegpump",
    "36EDhw36PVwXAZZcteF2uDPpYPzJt9pivpKQVGGYpump",
    "6zNYQSxnSZRZkgG5HM7FepF8y17DVyQm4ProHcXKpump",
    "HMY5WQhrKN6mWar98nRmtxTja8zXgw94UFdjhsLNpump",
    "EXYEJtv6qEu8Efrf7exPX6s49KtVNgKkBmf4YqG1pump",
    "BtargL5u77J8jYW35boKhKoqfSTFVyJBiV6RCzXpump",
    "8wwtyF8XfpAa7gvWq4ZZaob5aL8sjVeGta8YRRNEpump",
    "6ByeCaCTA4JrzvEXZwu9fwbjY1EVL4HsEfnA9ttEpump",
    "yviwboP29tMSjWk2SkgXN7wTUGmBsYxjk4GXopvpump"
]
ca2sandbox = {ca: Sandbox(token_supply=1000000, pooled_sol=1000, decimals=9, fee=0.0001) for ca in CA}

@app.get("/getallca")
def get_all_ca():
    return {"ca": CA}

@app.get("/getreserves")
def get_reserves(ca: str = ""):
    return {"solReserves": ca2sandbox[ca].sol_balance, "tokenReserves": ca2sandbox[ca].token_balance}

@app.get("/getbalance")
def get_balance(ca: str = "", public_key: str = ""):
    return {"balance": ca2sandbox[ca].get_balance(public_key)}

@app.get("/gettokenbalance")
def get_token_balance(ca: str = "", public_key: str = ""):
    return {"tokenBalance": ca2sandbox[ca].get_token_balance(public_key)}


# @app.post("/buy")
# async def buy(transaction: Transaction):
#     ca = transaction.ca
#     await ca2sandbox[ca].buy(transaction.walletAddress, transaction.amount)
#     return {"message": "Bought"}

# @app.post("/sell")
# async def sell(transaction: Transaction):
#     ca = transaction.ca
#     await ca2sandbox[ca].sell(transaction.walletAddress, transaction.amount)
#     return {"message": "Sold"}

@app.get("/getprice", response_model=PriceResponse)
def get_price(ca: str = ""):
    return {"price": ca2sandbox[ca].get_price()}

@app.get("/getpricehistory", response_model=PriceHistoryResponse)
def get_price_history(ca: str = ""):
    return {"priceHistory": ca2sandbox[ca].price_history}

@app.get("/getAllBalances")
def get_all_balances(ca: str = ""):
    wallets = ca2sandbox[ca].get_all_wallets()
    balances = [{"address": wallet, "ethBalance": ca2sandbox[ca].get_balance(wallet), "tokenBalance": ca2sandbox[ca].get_token_balance(wallet)} for wallet in wallets]
    for balance in balances:
        wallet = balance["address"]
        balance["solDelta"] = balance["ethBalance"] - ca2sandbox[ca].snapshoot_after_distribution.get(wallet, {}).get("sol_balance", 0)
        balance["tokenDelta"] = balance["tokenBalance"] - ca2sandbox[ca].snapshoot_after_distribution.get(wallet, {}).get("token_balance", 0)

    return {"balances": balances}

@app.get("/reset")
def reset(ca: str = ""):
    ca2sandbox[ca].reset()
    return {"message": "State reset"}

@app.post("/distributeTokens")
async def distribute_tokens(body: DistributionBody):
    ca = body.ca
    await ca2sandbox[ca].distribute_tokens(body.wallets, body.sol_amount, body.holders_ratio)
    return {"message": "Tokens distributed"}

@app.get("/gettx")
def get_tx(ca: str = ""):
    return {"tx": ca2sandbox[ca].tx}

async def generate_random_transactions_with_notification(ca, num_txs, interval, regime):
    orders = await ca2sandbox[ca].generate_random_transactions(num_txs, interval, regime)
    for order in orders:
        order["ca"] = ca
    for order in orders:
        if order["isBuy"]:
            await buy_with_notification(ca, order)
        else:
            await sell_with_notification(ca, order)
        await asyncio.sleep(order["sleep"])

@app.post("/generateRandomTransactions")
async def generate_random_transactions(body: RandomTransactionsBody):
    ca = body.ca
    asyncio.create_task(generate_random_transactions_with_notification(ca, body.num_txs, body.interval, body.regime))
    print("Transactions generated")
    return {"message": "Transactions generated"}

from fastapi import WebSocket, WebSocketDisconnect

# Create a list to hold active WebSocket connections
active_connections = []

async def notify_order(order):
    for connection in active_connections:
        await connection.send_json(order)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection open
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def buy_with_notification(ca, order):
    wallet_address = order["to"]
    amount = order["amountIn"]
    await ca2sandbox[ca].buy(wallet_address, amount)
    await notify_order(order)

async def sell_with_notification(ca, order):
    wallet_address = order["to"]
    amount = order["amountIn"]
    await ca2sandbox[ca].sell(wallet_address, amount)
    await notify_order(order)

@app.post("/buy")
async def buy(transaction: Transaction):
    order = {
        "amountIn": transaction.amount,
        "amountOut": ca2sandbox[transaction.ca].get_sol_output_for_token_input(transaction.amount),
        "isBuy": True,
        "to": transaction.walletAddress,
        "timestamp": time.time(),
        "price": ca2sandbox[transaction.ca].get_price(),
        "id": str(uuid.uuid4()),
        "ca": transaction.ca
    }
    ca = transaction.ca
    await buy_with_notification(ca, order)
    return {"message": "Bought"}

@app.post("/sell")
async def sell(transaction: Transaction):
    order = {
        "amountIn": transaction.amount,
        "amountOut": ca2sandbox[transaction.ca].get_sol_output_for_token_input(transaction.amount),
        "isBuy": False,
        "to": transaction.walletAddress,
        "timestamp": time.time(),
        "price": ca2sandbox[transaction.ca].get_price(),
        "id": str(uuid.uuid4()),
        "ca": transaction.ca
    }
    ca = transaction.ca
    await sell_with_notification(ca, order)
    return {"message": "Sold"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

