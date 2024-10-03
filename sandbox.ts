import { formatEther, parseEther } from "viem";
import * as logger from "./logger";
import {getRandomDecimalInRange} from "./utils";
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
    }

    public buy(buyerPublicKey: string, ethInput: number, slippage: number): void {
        const tokenOutput = this.getTokenOutputForEthInput(ethInput);
        const ethWei = parseEther(ethInput.toString());
        const tokenOutputWei = parseEther(tokenOutput.toString());

        // Update pool state
        this.tokenBalance -= tokenOutputWei;
        this.ethBalance += ethWei;

        // Update mappings
        updateHoldings(this.tokenHoldings, buyerPublicKey, tokenOutputWei);
        updateHoldings(this.ethHoldings, buyerPublicKey, -ethWei);

        
        // Log the changes in buyer's holdings
        const prevTokenBalance = this.tokenHoldings.get(buyerPublicKey) || BigInt(0);
        const prevEthBalance = this.ethHoldings.get(buyerPublicKey) || BigInt(0);

        this.dumpState(true, ethInput, tokenOutput);
    }

    public sell(sellerPublicKey: string, tokenInput: number, slippage: number): void {
        const minEthOutput = this.getEthOutputForTokenInput(tokenInput);
        const tokenInputWei = parseEther(tokenInput.toString());
        const ethOutputWei = parseEther(minEthOutput.toString());

        // Update pool state
        this.tokenBalance += tokenInputWei;
        this.ethBalance -= ethOutputWei;

        // Update mappings
        this.updateHoldings(this.tokenHoldings, sellerPublicKey, -tokenInputWei);
        this.updateHoldings(this.ethHoldings, sellerPublicKey, ethOutputWei);

        // Log the changes in seller's holdings
        
        this.dumpState(false, minEthOutput, tokenInput);
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

        // Distribute ETH to all wallets
        for (let i = 0; i < totalWallets; i++) {
            const ethAmount = getRandomDecimalInRange(minEth, maxEth);
            this.updateHoldings(this.ethHoldings, wallets[i], parseEther(ethAmount.toString()));
        }

        // Calculate the current token price
        const tokenPrice = Number(this.ethBalance) / Number(this.tokenBalance);
        logger.info(`Token price before distribution: ${tokenPrice}`);

        // Buy tokens for 90% of ETH balance for each wallet
        for (let i = 0; i < walletsWithTokens; i++) {
            const ethBalanceWei = this.ethHoldings.get(wallets[i]) || BigInt(0);
            const ethBalance = Number(formatEther(ethBalanceWei));
            const ethToBuy = ethBalance * 0.9; // 90% of ETH balance

            this.buy(wallets[i], ethToBuy, 0);
        }
        const newTokenPrice = Number(this.ethBalance) / Number(this.tokenBalance);
        logger.info(`Token price after distribution: ${newTokenPrice}`);
        logger.info(`Token price change: ${(Number(newTokenPrice - tokenPrice) / Number(tokenPrice)) * 100}%`);
    }

    public dumpState(isBuy: boolean, ethInput: number, tokenOutput: number): void {
        const state = {
            isBuy: isBuy,
            ethInput: ethInput,
            tokenOutput: tokenOutput,
            tokenBalance: Number(formatEther(this.tokenBalance)),
            ethBalance: Number(formatEther(this.ethBalance)),
            price: Number(this.ethBalance / this.tokenBalance)
        }
        const stateJson = JSON.stringify(state);
        fs.appendFileSync('sandbox_state.json', stateJson + "\n");
    }


    public getGasPrice(): number {
        return 2.1;
    }
}