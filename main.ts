import { Sandbox } from "./sandbox";
import express from 'express';
import cors from 'cors';


const sandbox = new Sandbox(14520427, 170, 18);


const app = express();
const port = 5001;

app.use(express.json());
app.use(cors())



// Distribute holdings endpoint
app.post('/distributeHoldings', (req: any, res: any) => {
    const { minEth, maxEth, ratioWithoutTokens, wallets } = req.body;
    sandbox.distributeHoldings(minEth, maxEth, ratioWithoutTokens, wallets);
    res.json({ message: 'Holdings distributed' });
});

app.get("/getprice", (req: any, res: any) => {
    res.json({ price: sandbox.getPrice() });
});

app.get("/getgasprice", (req: any, res: any) => {
    res.json({ gasPrice: sandbox.getGasPrice() });
});

app.get("/getreserves", (req: any, res: any) => {
    res.json({ reserves: sandbox.getReserves() });
});

app.get("/getbalance/:publicKey", (req: any, res: any) => {
    const publicKey = req.params.publicKey;
    res.json({ balance: sandbox.getBalance(publicKey) });
});

app.get("/gettokenbalance/:publicKey", (req: any, res: any) => {
    const publicKey = req.params.publicKey;
    res.json({ tokenBalance: sandbox.getTokenBalance(publicKey) });
});

app.post("/buy", (req: any, res: any) => {
    const {amount, slippage, walletAddress } = req.body;
    sandbox.buy(walletAddress, amount, slippage);
    res.json({ message: "Bought" });
});

app.post("/sell", (req: any, res: any) => {
    const { amount, slippage, walletAddress } = req.body;
    sandbox.sell(walletAddress, amount, slippage);
    res.json({ message: "Sold" });
});

app.get("/getAllBalances", (req: any, res: any) => {
    const wallets = sandbox.getAllWallets(); // Assuming this method exists in sandbox
    const balances = wallets.map((wallet: any) => ({
        address: wallet,
        ethBalance: sandbox.getBalance(wallet),
        tokenBalance: sandbox.getTokenBalance(wallet)
    }));
    res.json({ balances });
});
app.get("/reloadState", (req: any, res: any) => {
    sandbox.reloadState();
    res.json({ message: "State reloaded" });
});

app.get("/getwalletchanges", (req: any, res: any) => {
    const changes = sandbox.getWalletChanges();
    const changes_list = [];
    for (const [address, change] of changes) {
        changes_list.push({
            address,
            ethChange: change.ethChange,
            tokenChange: change.tokenChange
        });
    }

    res.json({changes: changes_list });
});

app.get("/getpricehistory", (req: any, res: any) => {
    res.json({ priceHistory: sandbox.priceHistory });
});

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});
