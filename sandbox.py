import asyncio
from math import floor
from random import shuffle
import random
import time
from loguru import logger


class Sandbox:
    def __init__(self, token_supply, pooled_sol, decimals, fee=0.0001):
        self.token_supply = token_supply
        self.pooled_sol = pooled_sol
        self.decimals = decimals
        self.token_balance = token_supply
        self.sol_balance = pooled_sol
        self.is_running = False
        self.token_holdings = {}
        self.sol_holdings = {}
        self.fee = fee
        self.price_history = [{"price": self.get_price(), "timestamp": time.time()}]
        self.initial_price = self.get_price()
        self.snapshoot_after_distribution = {}
        self.tx = []

        with open("random_wallets_list.txt", "r") as f:
            self.wallets_for_random_tx = f.read().split("\n")
        
        asyncio.run(self.distribute_tokens(self.wallets_for_random_tx, 3, 0.5))
        


    def reset(self):
        self.token_holdings = {}
        self.sol_holdings = {}
        self.token_balance = self.token_supply
        self.sol_balance = self.pooled_sol
        self.price_history = [{"price": self.get_price(), "timestamp": time.time()}]
        self.initial_price = self.get_price()
        self.snapshoot_after_distribution = {}
        self.tx = []
        with open("random_wallets_list.txt", "r") as f:
            self.wallets_for_random_tx = f.read().split("\n")
        
        self.distribute_tokens(self.wallets_for_random_tx, 3, 0.5)


    async def buy(self, buyer_public_key, sol_input):
        token_output = self.get_token_output_for_sol_input(sol_input)

        self.token_balance -= token_output
        self.sol_balance += sol_input

        self.update_holdings(self.token_holdings, buyer_public_key, token_output)
        self.update_holdings(self.sol_holdings, buyer_public_key, -sol_input - self.fee)
        logger.info(f"BUY {buyer_public_key} {sol_input} {self.get_price()}")
        price = self.get_price()
        self.price_history.append({'price': price, 'timestamp': time.time()})
        self.tx.append({
            "type": "buy",
            "sender": buyer_public_key[-4:],
            "amount_in": sol_input,
            "amount_out": token_output,
            "price": price,
            "timestamp": time.time()
        })
        
    async def sell(self, seller_public_key, token_input):
        sol_output = self.get_sol_output_for_token_input(token_input)

        self.token_balance += token_input
        self.sol_balance -= sol_output

        self.update_holdings(self.token_holdings, seller_public_key, -token_input)
        self.update_holdings(self.sol_holdings, seller_public_key, sol_output-self.fee)
        logger.info(f"SELL {seller_public_key} {token_input} {self.get_price()}")
        price = self.get_price()
        self.price_history.append({'price': price, 'timestamp': time.time()})
        self.tx.append({
            "type": "sell",
            "sender": seller_public_key[-4:],
            "amount_in": token_input,
            "amount_out": sol_output,
            "price": price,
            "timestamp": time.time()
        })

    def get_price(self):
        return self.sol_balance / self.token_balance

    def get_balance(self, public_key):
        return self.sol_holdings.get(public_key, 0)

    def get_all_wallets(self):
        return [i for i in self.sol_holdings.keys() if i not in self.wallets_for_random_tx]
    def get_token_balance(self, public_key):
        return self.token_holdings.get(public_key, 0)

    def get_token_output_for_sol_input(self, sol_input):
        k = self.token_balance * self.sol_balance
        return self.token_balance - (k / (self.sol_balance + sol_input))

    def get_sol_output_for_token_input(self, token_input):
        k = self.token_balance * self.sol_balance
        return self.sol_balance - (k / (self.token_balance + token_input))

    def update_holdings(self, holdings, public_key, amount):
        current_holding = holdings.get(public_key, 0)
        holdings[public_key] = current_holding + amount

    async def distribute_tokens(self, wallets, sol_amount, holders_ratio):
        shuffle(wallets)

        for wallet in wallets:
            self.sol_holdings[wallet] = sol_amount

        holders_threshold = floor(len(wallets) * holders_ratio)
        for wallet in wallets[:holders_threshold]:
            await self.buy(wallet, (sol_amount-self.fee)*0.95)
        
        for wallet in wallets:
            self.snapshoot_after_distribution[wallet] = {
                "sol_balance": self.sol_holdings.get(wallet, 0),
                "token_balance": self.token_holdings.get(wallet, 0)
            }
    
    async def generate_random_transactions(self, num_txs, interval, regime):
        for _ in range(num_txs):
            while True:
                wallet = random.choice(self.wallets_for_random_tx)
                balance = self.get_balance(wallet)
                token_balance = self.get_token_balance(wallet)
                if regime == 'buy' and balance * 0.9 > 0.001:
                    amount = random.uniform(0.001, balance * 0.9)
                    await self.buy(wallet, amount)
                    break
                elif regime == 'sell' and token_balance > 0:
                    amount = random.uniform(1, token_balance)
                    await self.sell(wallet, amount)
                    break
                elif regime == 'shuffle':
                    type_ = random.choice(['buy', 'sell'])
                    if type_ == 'buy' and balance * 0.9 > 0.001:
                        amount = random.uniform(0.001, balance * 0.9)
                        await self.buy(wallet, amount)
                        break
                    elif type_ == 'sell' and token_balance > 0:
                        amount = random.uniform(1, token_balance)
                        await self.sell(wallet, amount)
                        break
            await asyncio.sleep(interval)
        
    
        