export interface Game {
  id: number
  slug: string
  title: string
  category: string
  rtp: string
  min_bet: string
  max_bet: string
  is_featured: boolean
  is_playable: boolean
  image: string | null
}

export interface GameCategory {
  id: number
  lang: string
  code: string
  filter_label: string
  card_label: string
  order: number
  is_soon: boolean
}

export interface LobbyPageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  bonus_eyebrow: string
  bonus_title: string
  bonus_text: string
  bonus_claim_button: string
  bonus_claiming: string
  bonus_claimed: string
  bonus_next: string
  filter_all: string
  filters_label: string
  section_popular: string
  section_all: string
  soon_badge: string
  rtp_label: string
  no_results: string
  server_unreachable: string
}
