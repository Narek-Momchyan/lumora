import type { ForumLabels, ForumPost, ForumRule, ForumTopic, TopicSort, TopicTag } from '@/types/forums'

// The same limits as backend forums/services.py. The backend checks them again on every post.
export const TITLE_MAX = 120
export const BODY_MAX = 2000
export const TOPICS_PAGE = 50 // a topic list never has more rows per request

export const TAGS: TopicTag[] = ['match_talk', 'transfers', 'tactics', 'predictions', 'off_topic']
export const SORTS: TopicSort[] = ['latest', 'replies', 'views']

export function tagLabel(tag: TopicTag, labels: ForumLabels) {
  const names: Record<TopicTag, string> = {
    match_talk: labels.tag_match_talk,
    transfers: labels.tag_transfers,
    tactics: labels.tag_tactics,
    predictions: labels.tag_predictions,
    off_topic: labels.tag_off_topic,
  }
  return names[tag]
}

export function sortLabel(sort: TopicSort, labels: ForumLabels) {
  return { latest: labels.sort_latest, replies: labels.sort_replies, views: labels.sort_views }[sort]
}

// The author's name, or the plain "Player" text when the player has no display name.
export function authorName(name: string | null, labels: ForumLabels) {
  return name ?? labels.anonymous_player
}

// Characters as the backend counts them: after trimming, one per letter (not per UTF-16 unit).
export function length(value: string) {
  return [...value.trim()].length
}

// The cursor for the next page of the "latest" sort: the last row you have.
export function cursor(topic: ForumTopic) {
  return `${topic.last_post_at}_${topic.id}`
}

// The club forum's URL query: a tag and a sort, left out when they are the default.
export function forumHref(club: number, tag: string, sort: string) {
  const query = new URLSearchParams({ ...(tag && { tag }), ...(sort !== 'latest' && { sort }) }).toString()
  return `/forums/${club}${query ? `?${query}` : ''}`
}

export const POSTS_PAGE = 100 // a post list never has more rows per request
export const RULES: ForumRule[] = ['insult_hate', 'spam_ads', 'real_money', 'other']

// "rule: spam or ads" for a post a moderator hid, and the reasons of the report dialog.
export function ruleLabel(rule: ForumRule | '', labels: ForumLabels) {
  const names: Record<ForumRule, string> = {
    insult_hate: labels.rule_insult_hate,
    spam_ads: labels.rule_spam_ads,
    real_money: labels.rule_real_money,
    other: labels.rule_other,
  }
  return rule ? names[rule] : names.other
}

// The posts shown, from the ones we have and some new ones: each post once (by id), oldest first. A reply
// the player just posted and the same reply arriving in a later "Load more" page are one post, and a post
// that arrives later than a newer one still lands before it.
export function mergePosts(current: ForumPost[], incoming: ForumPost[]) {
  const byId = new Map<number, ForumPost>()
  for (const post of [...current, ...incoming]) byId.set(post.id, post)
  return [...byId.values()].sort((a, b) => a.id - b.id)
}
