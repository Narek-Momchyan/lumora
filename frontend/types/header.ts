export interface Logo {
  id: number
  name: string
  image: string
}

export interface Language {
  id: number
  code: string
  name: string
  order: number
}

export interface SidebarItem {
  id: number
  lang: string
  title: string
  url: string
  order: number
  is_soon: boolean
}

export interface HeaderLabels {
  id: number
  lang: string
  navigation_label: string
  soon_label: string
  search_placeholder: string
  demo_badge: string
  demo_note: string
  balance_label: string
  currency: string
  menu_label: string
  language_label: string
  logout_button: string
  server_unreachable: string
}
