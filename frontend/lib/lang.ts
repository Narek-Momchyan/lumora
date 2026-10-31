import { cookies } from 'next/headers'

const LANGS = ['en', 'am', 'ru']
const DEFAULT_LANG = 'en'

export async function displayLang() {
  const cookieStore = await cookies()
  const lang = cookieStore.get('lang')?.value
  return lang && LANGS.includes(lang) ? lang : DEFAULT_LANG
}

// `am` is our code for Armenian, but the HTML language code is `hy`.
export function htmlLang(lang: string) {
  return lang === 'am' ? 'hy' : lang
}
