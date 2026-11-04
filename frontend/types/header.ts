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
  category: string // '' or a game category: the item opens /?category=<code>
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
  open_menu_label: string
  close_menu_label: string
  language_label: string
  logout_button: string
  server_unreachable: string
}

// A page the top bar can name and the sidebar can match: a game's route or a sidebar link.
export interface PageInfo {
  title: string
  category: string
}
