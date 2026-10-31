import type { LoginPageLabels, Player } from '@/types/account'
import type { Game, GameCategory, LobbyPageLabels } from '@/types/game'
import type { HeaderLabels, Language, Logo, SidebarItem } from '@/types/header'
import type { Wallet } from '@/types/wallet'
import type {
  JackpotPool,
  SlotSound,
  SlotSpinRecord,
  SlotSymbol,
  SlotSymbolName,
  ZeusPageLabels,
} from '@/types/zeus'
import { serverFetch } from './server-api'

async function fetchOrNull<T>(path: string) {
  try {
    return await serverFetch<T>(path)
  } catch {
    return null
  }
}

// A page can't render without its texts, unlike the logo, the balance or the stats.
async function firstRow<T>(path: string) {
  const [row] = await serverFetch<T[]>(path)
  if (!row) throw new Error(`No rows in ${path}: run python manage.py load_sample`)
  return row
}

// The API answers {} before a logo is added.
export async function getLogo() {
  const logo = await fetchOrNull<Logo>('/logos')
  return logo?.image ? logo : null
}

export function getLanguages() {
  return fetchOrNull<Language[]>('/languages')
}

export function getGames() {
  return fetchOrNull<Game[]>('/games')
}

export function getGameCategories(lang: string) {
  return fetchOrNull<GameCategory[]>(`/game_categories?lang=${lang}`)
}

export function getSidebarItems(lang: string) {
  return fetchOrNull<SidebarItem[]>(`/sidebar_items?lang=${lang}`)
}

export function getWallet() {
  return fetchOrNull<Wallet>('/wallet')
}

export function getMe() {
  return fetchOrNull<Player>('/me')
}

export function getSlotSymbols() {
  return fetchOrNull<SlotSymbol[]>('/slot_symbols')
}

export function getSlotSymbolNames(lang: string) {
  return fetchOrNull<SlotSymbolName[]>(`/slot_symbol_names?lang=${lang}`)
}

export function getSlotSounds() {
  return fetchOrNull<SlotSound[]>('/slot_sounds')
}

export function getJackpotPools() {
  return fetchOrNull<JackpotPool[]>('/jackpot_pools')
}

export function getSlotSpins() {
  return fetchOrNull<SlotSpinRecord[]>('/slot_spins')
}

export function getZeusPageLabels(lang: string) {
  return firstRow<ZeusPageLabels>(`/zeus_page_labels?lang=${lang}`)
}

export function getLoginPageLabels(lang: string) {
  return firstRow<LoginPageLabels>(`/login_page_labels?lang=${lang}`)
}

export function getHeaderLabels(lang: string) {
  return firstRow<HeaderLabels>(`/header_labels?lang=${lang}`)
}

export function getLobbyPageLabels(lang: string) {
  return firstRow<LobbyPageLabels>(`/lobby_page_labels?lang=${lang}`)
}
