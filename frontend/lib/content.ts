import type { LoginPageLabels, Player } from '@/types/account'
import type { CrashBet, CrashPageLabels } from '@/types/crash'
import type { Game, GameCategory, LobbyPageLabels } from '@/types/game'
import type { HeaderLabels, Language, Logo, SidebarItem } from '@/types/header'
import type { ForumClub, ForumLabels } from '@/types/forums'
import type { LiveLabels, LiveRow } from '@/types/live'
import type {
  Leaderboard,
  Matchday,
  PredictionEntry,
  PredictionLabels,
  PredictionStats,
  StandingRow,
  StandingZone,
} from '@/types/predictions'
import type { RoulettePageLabels, RouletteSlip } from '@/types/roulette'
import type {
  Bet,
  BetLabels,
  BetSummary,
  Competition,
  Market,
  Match,
  MatchDetail,
  PopularPick,
  SportsPageLabels,
  SportsUiLabels,
} from '@/types/sports'
import type { Wallet } from '@/types/wallet'
import type { JackpotPool, SlotSound, SlotSpinRecord, SlotSymbol, SlotSymbolName, ZeusPageLabels } from '@/types/zeus'
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

export function getCrashBets() {
  return fetchOrNull<CrashBet[]>('/crash_bets')
}

export function getCrashPageLabels(lang: string) {
  return firstRow<CrashPageLabels>(`/crash_page_labels?lang=${lang}`)
}

export function getRouletteBets() {
  return fetchOrNull<RouletteSlip[]>('/roulette_bets')
}

export function getRoulettePageLabels(lang: string) {
  return firstRow<RoulettePageLabels>(`/roulette_page_labels?lang=${lang}`)
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

export function getSportsPageLabels(lang: string) {
  return firstRow<SportsPageLabels>(`/sports_page_labels?lang=${lang}`)
}

export function getSportsUiLabels(lang: string) {
  return firstRow<SportsUiLabels>(`/sports_ui_labels?lang=${lang}`)
}

export function getBetLabels(lang: string) {
  return firstRow<BetLabels>(`/bet_labels?lang=${lang}`)
}

export function getCompetitions(lang: string) {
  return fetchOrNull<Competition[]>(`/competitions?lang=${lang}`)
}

export function getMatches(query: string, lang: string) {
  return fetchOrNull<Match[]>(`/matches?${query}&lang=${lang}`)
}

export function getMatch(id: string, lang: string) {
  return fetchOrNull<MatchDetail>(`/matches/${id}?lang=${lang}`)
}

export function getMarkets(query: string) {
  return fetchOrNull<Market[]>(`/markets?${query}`)
}

export function getPopularPicks(lang: string) {
  return fetchOrNull<PopularPick[]>(`/popular_picks?lang=${lang}`)
}

export function getBets(status: string, lang: string) {
  return fetchOrNull<Bet[]>(`/sport_bets?lang=${lang}${status ? `&status=${status}` : ''}`)
}

export function getBetSummary() {
  return fetchOrNull<BetSummary>('/sport_bets/summary')
}

export function getPredictionLabels(lang: string) {
  return firstRow<PredictionLabels>(`/prediction_labels?lang=${lang}`)
}

export function getMatchdays(code: string) {
  return fetchOrNull<Matchday[]>(`/matchdays?competition=${code}`)
}

export function getPredictions(code: string, matchday: number, lang: string) {
  return fetchOrNull<PredictionEntry[]>(`/predictions?competition=${code}&matchday=${matchday}&lang=${lang}`)
}

export function getLeaderboard(code: string, matchday?: number) {
  return fetchOrNull<Leaderboard>(
    `/prediction_leaderboard?competition=${code}${matchday === undefined ? '' : `&matchday=${matchday}`}`,
  )
}

export function getPredictionStats(code: string) {
  return fetchOrNull<PredictionStats>(`/prediction_stats?competition=${code}`)
}

export function getStandings(code: string, lang: string) {
  return fetchOrNull<StandingRow[]>(`/standings?competition=${code}&lang=${lang}`)
}

export function getStandingZones(code: string) {
  return fetchOrNull<StandingZone[]>(`/standing_zones?competition=${code}`)
}

export function getLiveLabels(lang: string) {
  return firstRow<LiveLabels>(`/live_labels?lang=${lang}`)
}

export function getLiveMatches(lang: string) {
  return fetchOrNull<LiveRow[]>(`/live_matches?lang=${lang}`)
}

export function getForumLabels(lang: string) {
  return firstRow<ForumLabels>(`/forum_labels?lang=${lang}`)
}

export function getForums(code: string, lang: string) {
  return fetchOrNull<ForumClub[]>(`/forums?competition=${encodeURIComponent(code)}&lang=${lang}`)
}
