import { formatEther, parseEther } from "viem";
import * as logger from "./logger";
import {getRandomDecimalInRange, truncateDecimal} from "./utils";
import * as fs from 'fs';


function updateHoldings(holdings: Map<string, bigint>, publicKey: string, amount: bigint): void {
    const currentHolding = holdings.get(publicKey) || BigInt(0);
    holdings.set(publicKey, currentHolding + amount);
}


export class Sandbox {
    private tokenSupply: bigint;
    private pooledEthLiquidity: bigint;
    private decimals: number;
    private tokenBalance: bigint;
    private ethBalance: bigint;
    public isRunning: boolean;
    public tokenHoldings: Map<string, bigint>;
    public ethHoldings: Map<string, bigint>;
    public state_snapshot: any;
    public initial_price: number;
    public ethBalanceSnap: bigint;
    public tokenBalanceSnap: bigint;

    constructor(tokenSupply: number, pooledEthLiquidity: number, decimals: number) {
        let tokenSupplyWei = parseEther(tokenSupply.toString());
        let pooledEthLiquidityWei = parseEther(pooledEthLiquidity.toString());

        this.tokenSupply = tokenSupplyWei;
        this.pooledEthLiquidity = pooledEthLiquidityWei;
        this.decimals = decimals;
        this.tokenBalance = tokenSupplyWei;
        this.ethBalance = pooledEthLiquidityWei;

        this.isRunning = false;
        this.tokenHoldings = new Map<string, bigint>();
        this.ethHoldings = new Map<string, bigint>();
        this.state_snapshot = null;

        this.initial_price = this.getPrice();
        this.ethBalanceSnap = this.ethBalance;
        this.tokenBalanceSnap = this.tokenBalance;
    }

    public buy(buyerPublicKey: string, ethInput: number, slippage: number): void {
        const tokenOutput = this.getTokenOutputForEthInput(ethInput);
        const ethWei = parseEther(ethInput.toString());
        const tokenOutputWei = parseEther(tokenOutput.toString());
        const delta_eth = this.getBalance(buyerPublicKey) - ethInput;
        
        this.tokenBalance -= tokenOutputWei;
        this.ethBalance += ethWei;

        updateHoldings(this.tokenHoldings, buyerPublicKey, tokenOutputWei);
        updateHoldings(this.ethHoldings, buyerPublicKey, -ethWei);

        const price = this.getPrice();

        const prevTokenBalance = this.tokenHoldings.get(buyerPublicKey) || BigInt(0);
        const prevEthBalance = this.ethHoldings.get(buyerPublicKey) || BigInt(0);

        const price_change = truncateDecimal((price - this.initial_price) / this.initial_price * 100, 2);
        logger.info(`BUY ${buyerPublicKey} ETH: ${ethInput} TOKEN: ${tokenOutput}, DELTA ETH: ${delta_eth}, PRICE CHANGE: ${price_change}%`)

    }

    public sell(sellerPublicKey: string, tokenInput: number, slippage: number): void {
        const minEthOutput = this.getEthOutputForTokenInput(tokenInput);
        const tokenInputWei = parseEther(tokenInput.toString());
        const ethOutputWei = parseEther(minEthOutput.toString());
        const token_delta = this.getTokenBalance(sellerPublicKey) - tokenInput;

        this.tokenBalance += tokenInputWei;
        this.ethBalance -= ethOutputWei;
        
        this.updateHoldings(this.tokenHoldings, sellerPublicKey, -tokenInputWei);
        this.updateHoldings(this.ethHoldings, sellerPublicKey, ethOutputWei);

        const price = this.getPrice();
        const price_change = truncateDecimal((price - this.initial_price) / this.initial_price * 100, 2);
        logger.info(`SELL ${sellerPublicKey} ETH: ${minEthOutput} TOKEN: ${tokenInput} DELTA TOKEN: ${token_delta}, PRICE CHANGE: ${price_change}%`)
        

    }

    public getPrice(): number {
        return Number(this.ethBalance) / Number(this.tokenBalance);
    }

    public getReserves(): { token0: number; token1: number } {
        return {
            token0: Number(formatEther(this.ethBalance)),
            token1: Number(formatEther(this.tokenBalance))
        };
    }

    public getBalance(publicKey: string): number {
        return Number(formatEther(this.ethHoldings.get(publicKey) || BigInt(0)));
    }

    public getTokenBalance(publicKey: string): number {
        return Number(formatEther(this.tokenHoldings.get(publicKey) || BigInt(0)));
    }

    public getTokenOutputForEthInput(ethInput: number): number {
        const ethInputWei = parseEther(ethInput.toString());
        const k = this.tokenBalance * this.ethBalance;
        return Number(formatEther(this.tokenBalance - (k / (this.ethBalance + ethInputWei))));
    }

    public getEthOutputForTokenInput(tokenInput: number): number {
        const tokenInputWei = parseEther(tokenInput.toString());
        const k = this.tokenBalance * this.ethBalance;
        return Number(formatEther(this.ethBalance - (k / (this.tokenBalance + tokenInputWei))));
    }

    private updateHoldings(holdings: Map<string, bigint>, publicKey: string, amount: bigint): void {
        const currentHolding = holdings.get(publicKey) || BigInt(0);
        holdings.set(publicKey, currentHolding + amount);
    }

    public distributeHoldings(
        minEth: number,
        maxEth: number,
        ratioWithoutTokens: number,
        wallets: string[]
    ): void {
        if (ratioWithoutTokens < 0 || ratioWithoutTokens > 1) {
            throw new Error("Ratio must be between 0 and 1");
        }

        const totalWallets = wallets.length;
        const walletsWithoutTokens = Math.round(totalWallets * ratioWithoutTokens);
        const walletsWithTokens = totalWallets - walletsWithoutTokens;
        logger.info(`walletsWithTokens: ${walletsWithTokens}`)
        logger.info(`walletsWithoutTokens: ${walletsWithoutTokens}`)

        for (let i = 0; i < totalWallets; i++) {
            const ethAmount = getRandomDecimalInRange(minEth, maxEth);
            this.updateHoldings(this.ethHoldings, wallets[i], parseEther(ethAmount.toString()));
        }

        const tokenPrice = Number(this.ethBalance) / Number(this.tokenBalance);
        logger.info(`Token price before distribution: ${tokenPrice}`);

        for (let i = 0; i < walletsWithTokens; i++) {
            const ethBalanceWei = this.ethHoldings.get(wallets[i]) || BigInt(0);
            const ethBalance = Number(formatEther(ethBalanceWei));
            const ethToBuy = ethBalance;

            this.buy(wallets[i], ethToBuy, 0);
        }
        const newTokenPrice = Number(this.ethBalance) / Number(this.tokenBalance);
        logger.info(`Token price after distribution: ${newTokenPrice}`);
        logger.info(`Token price change: ${(Number(newTokenPrice - tokenPrice) / Number(tokenPrice)) * 100}%`);

        this.initial_price = newTokenPrice;
        const balances = wallets.map(wallet => ({
            address: wallet,
            ethBalance: Number(formatEther(this.ethHoldings.get(wallet) || BigInt(0))),
            tokenBalance: Number(formatEther(this.tokenHoldings.get(wallet) || BigInt(0)))
        }));

        this.state_snapshot = balances;
        this.ethBalanceSnap = this.ethBalance;
        this.tokenBalanceSnap = this.tokenBalance;
    }

    public getGasPrice(): number {
        return 2.1;
    }

    public getAllWallets(): string[] {
        return Array.from(this.ethHoldings.keys());
    }
    public reloadState(): void {
        this.tokenBalance = this.tokenBalanceSnap;
        this.ethBalance = this.ethBalanceSnap;

        this.tokenHoldings = new Map<string, bigint>();
        this.ethHoldings = new Map<string, bigint>();

        for (const wallet of this.getAllWallets()) {
            this.tokenHoldings.set(wallet, this.state_snapshot.tokenHoldings.get(wallet) || BigInt(0));
            this.ethHoldings.set(wallet, this.state_snapshot.ethHoldings.get(wallet) || BigInt(0));
        }
    }

public getWalletChanges(): Map<string, { ethChange: number; tokenChange: number }> {
    const res = new Map<string, { ethChange: number; tokenChange: number }>();
    for (const wallet of this.state_snapshot) {
        const address = wallet.address;
        const initialEthBalance = wallet.ethBalance;
        const currentEthBalance = this.getBalance(address);
        const initialTokenBalance = wallet.tokenBalance;
        const currentTokenBalance = this.getTokenBalance(address);

        const ethChange = currentEthBalance - initialEthBalance
        const tokenChange = currentTokenBalance - initialTokenBalance
        res.set(address, { ethChange, tokenChange });
    }
    return res;

}
}