import type { Wallet } from '@/types/wallet'

// "12450.00" -> "12,450.00". Money stays a string: never turn it into a float.
export function formatBalance(balance: string) {
  return balance.replace(/\B(?=(\d{3})+\.)/g, ',')
}

export function toCents(amount: string) {
  return Math.round(Number(amount) * 100)
}

export function fromCents(cents: number) {
  return (cents / 100).toFixed(2)
}

// Only digits, in the browser's time zone: browsers don't all have Armenian month names.
export function formatDateTime(value: string) {
  const date = new Date(value)
  const pad = (part: number) => String(part).padStart(2, '0')
  const day = `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}`
  return `${day}, ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function isBonusReady(wallet: Wallet) {
  return !wallet.bonus_available_at || new Date(wallet.bonus_available_at) <= new Date()
}
