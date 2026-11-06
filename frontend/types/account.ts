export interface RegisterPayload {
  email: string
  password: string
  display_name?: string
}

export interface Player {
  id: number
  email: string
  display_name: string
  public_id: string // how other players' screens tell this player apart (a roulette seat is player-<public_id>)
  date_joined: string
}

export interface LoginPageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  language_switcher_label: string
  hero_title_line_1: string
  hero_title_line_2: string
  hero_text: string
  stat_games: string
  stat_rtp: string
  stat_real_money: string
  footer_note: string
  tab_login: string
  tab_signup: string
  login_title: string
  login_subtitle: string
  signup_title: string
  signup_subtitle: string
  email_label: string
  email_placeholder: string
  password_label: string
  display_name_label: string
  login_button: string
  login_pending: string
  signup_button: string
  signup_pending: string
  or_text: string
  create_account_button: string
  have_account_button: string
  server_unreachable: string
}
