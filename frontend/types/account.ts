export interface TokenPair {
  access: string
  refresh: string
}

export interface RegisterPayload {
  email: string
  password: string
  display_name?: string
}

export interface RegisteredPlayer {
  id: number
  email: string
  display_name: string
}
