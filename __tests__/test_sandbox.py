import unittest
from sandbox import Sandbox

class TestSandbox(unittest.TestCase):

    def setUp(self):
        self.sandbox = Sandbox(token_supply=1000000, pooled_sol=1000, decimals=18)

    def test_buy(self):
        initial_sol_balance = self.sandbox.sol_balance
        initial_token_balance = self.sandbox.token_balance
        buyer_public_key = "buyer1"
        sol_input = 100
        token_output = self.sandbox.get_token_output_for_sol_input(sol_input)
        self.sandbox.buy(buyer_public_key, sol_input)

        self.assertEqual(self.sandbox.sol_balance, initial_sol_balance + sol_input)
        self.assertEqual(self.sandbox.token_balance, initial_token_balance - token_output)
        self.assertEqual(self.sandbox.sol_holdings[buyer_public_key], -sol_input - self.sandbox.fee)
        self.assertGreater(len(self.sandbox.price_history), 0)

    def test_sell(self):
        initial_sol_balance = self.sandbox.sol_balance
        initial_token_balance = self.sandbox.token_balance
        seller_public_key = "seller1"

        # First, buy some tokens to sell
        self.sandbox.buy(seller_public_key, 100)

        self.sandbox.sell(seller_public_key, self.sandbox.get_token_balance(seller_public_key))

        self.assertEqual(self.sandbox.token_balance, initial_token_balance)
        self.assertEqual(self.sandbox.sol_balance, initial_sol_balance)
        self.assertEqual(self.sandbox.token_holdings[seller_public_key], 0)
        self.assertGreater(len(self.sandbox.price_history), 0)

    def test_get_balance(self):
        public_key = "address1"
        self.sandbox.sol_holdings[public_key] = 500
        balance = self.sandbox.get_balance(public_key)
        self.assertEqual(balance, 500)

    def test_get_token_balance(self):
        public_key = "address2"
        self.sandbox.token_holdings[public_key] = 300
        token_balance = self.sandbox.get_token_balance(public_key)
        self.assertEqual(token_balance, 300)

    def test_price_history(self):
        self.sandbox.buy("buyer1", 100)
        self.sandbox.sell("seller1", 50)
        self.assertGreater(len(self.sandbox.price_history), 0)
        

if __name__ == '__main__':
    unittest.main()
