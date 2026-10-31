export interface RegisterPayload {
  email: string
  password: string
  display_name?: string
}

export interface Player {
  id: number
  email: string
  display_name: string
  date_joined: string
}
