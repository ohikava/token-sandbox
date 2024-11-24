from math import floor
from random import shuffle
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

    def buy(self, buyer_public_key, sol_input):
        token_output = self.get_token_output_for_sol_input(sol_input)

        self.token_balance -= token_output
        self.sol_balance += sol_input

        self.update_holdings(self.token_holdings, buyer_public_key, token_output)
        self.update_holdings(self.sol_holdings, buyer_public_key, -sol_input - self.fee)
        logger.info(f"BUY {buyer_public_key} {sol_input} {self.get_price()}")
        price = self.get_price()
        self.price_history.append({'price': price, 'timestamp': time.time()})

    def sell(self, seller_public_key, token_input):
        sol_output = self.get_sol_output_for_token_input(token_input)

        self.token_balance += token_input
        self.sol_balance -= sol_output

        self.update_holdings(self.token_holdings, seller_public_key, -token_input)
        self.update_holdings(self.sol_holdings, seller_public_key, sol_output-self.fee)
        logger.info(f"SELL {seller_public_key} {token_input} {self.get_price()}")
        price = self.get_price()
        self.price_history.append({'price': price, 'timestamp': time.time()})

    def get_price(self):
        return self.sol_balance / self.token_balance

    def get_balance(self, public_key):
        return self.sol_holdings.get(public_key, 0)

    def get_all_wallets(self):
        return list(self.sol_holdings.keys())

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

    def distribute_tokens(self, wallets, sol_amount, holders_ratio):
        shuffle(wallets)

        for wallet in wallets:
            self.sol_holdings[wallet] = sol_amount

        holders_threshold = floor(len(wallets) * holders_ratio)
        for wallet in wallets[:holders_threshold]:
            self.buy(wallet, (sol_amount-self.fee)*0.95)
        
        for wallet in wallets:
            self.snapshoot_after_distribution[wallet] = {
                "sol_balance": self.sol_holdings.get(wallet, 0),
                "token_balance": self.token_holdings.get(wallet, 0)
            }
        

        