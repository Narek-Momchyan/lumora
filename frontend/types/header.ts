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
  mode: 'sports' | 'casino'
  group: '' | 'leagues' | 'my' // listed under this heading
  title: string
  url: string
  icon: string | null
  category: string // '' or a game category: the casino item opens /casino?category=<code>
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
  sports_mode: string
  casino_mode: string
  mode_switch_label: string
  leagues_group: string
  my_lumora_group: string
  language_label: string
  logout_button: string
  server_unreachable: string
}

// A page the top bar can name and the sidebar can match: a game's route or a sidebar link.
export interface PageInfo {
  title: string
  category: string
}
