import type { Wallet } from '@/types/wallet'

// "12450.00" -> "12,450.00". Money stays a string: never turn it into a float.
export function formatBalance(balance: string) {
  return balance.replace(/\B(?=(\d{3})+\.)/g, ',')
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
