import type { Game } from '@/types/game'
import type { PageInfo, SidebarItem } from '@/types/header'

// A playable game opens its page; a new game needs its route added here.
export const GAME_ROUTES: Record<string, string> = {
  'neon-crash': '/crash',
  'lumora-roulette': '/roulette',
  'zeus-legacy': '/zeus-legacy',
}

// Path → the page's title and category, for the top bar and the sidebar's active item.
// A game's page belongs to its category, so on /crash the sidebar's Crash item is the active one.
export function pagesByPath(games: Game[], items: SidebarItem[]) {
  const pages: Record<string, PageInfo> = {}

  for (const { url, title, category } of items) {
    if (url !== '/' && !category) pages[url] = { title, category: '' }
  }
  for (const { slug, title, category } of games) {
    const route = GAME_ROUTES[slug]
    if (route) pages[route] = { title, category }
  }
  return pages
}
