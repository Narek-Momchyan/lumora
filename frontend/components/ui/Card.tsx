import type { HTMLAttributes } from 'react'

type Tone = 'default' | 'hero' | 'lime'
type Padding = 'none' | 'sm' | 'md' | 'lg'

const TONES: Record<Tone, string> = {
  default: 'border border-border bg-surface',
  hero: 'bg-linear-to-r from-accent2/30 via-surface2 to-accent/60 shadow-2xl shadow-accent2/10',
  lime: 'border border-lime/40 bg-lime/5',
}

const PADDINGS: Record<Padding, string> = {
  none: '',
  sm: 'p-3',
  md: 'p-4 lg:p-5',
  lg: 'p-5 lg:p-6',
}

interface CardStyle {
  tone?: Tone
  padding?: Padding
  large?: boolean // the big stage of a game or the bonus banner: a rounder corner
}

// For a Link that looks like a card (a game in the lobby).
export function cardClass({ tone = 'default', padding = 'lg', large = false }: CardStyle = {}) {
  return `${large ? 'rounded-3xl' : 'rounded-2xl'} ${TONES[tone]} ${PADDINGS[padding]}`
}

interface CardProps extends HTMLAttributes<HTMLElement>, CardStyle {
  as?: 'div' | 'section' | 'article' | 'aside'
}

// Every panel of the site: the bet panel, the live tables, the game cards, the login card.
export default function Card({ as: Tag = 'section', tone, padding, large, className = '', ...props }: CardProps) {
  return <Tag className={`${cardClass({ tone, padding, large })} ${className}`} {...props} />
}
