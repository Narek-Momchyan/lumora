import type { LoginPageLabels } from '@/types/account'
import type { Game } from '@/types/game'
import type { Language, Logo } from '@/types/header'
import { serverFetch } from './server-api'

async function fetchOrNull<T>(path: string) {
  try {
    return await serverFetch<T>(path)
  } catch {
    return null
  }
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

// Unlike the logo or the stats, a page can't render without its texts.
export async function getLoginPageLabels(lang: string) {
  const [labels] = await serverFetch<LoginPageLabels[]>(`/login_page_labels?lang=${lang}`)
  if (!labels) throw new Error(`No login page labels for "${lang}": run python manage.py load_sample`)
  return labels
}
