
export function getRandomDecimalInRange(min: number, max: number): number {
    return min + Math.random() * (max - min);
}

export function truncateDecimal(num: number, digits: number): number {
    const multiplier = Math.pow(10, digits);
    return Math.trunc(num * multiplier) / multiplier;
}
