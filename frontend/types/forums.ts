import type { Team } from './sports'

// Mirrors backend forums/models.py ForumLabel: every text of the forum pages.
export interface ForumLabels {
  page_text: string
  clubs_title: string
  topics_count: string // "{count} topics"
  posts_count: string // "{count} posts"
  fans: string // "{club} fans"
  all_topics: string
  tag_match_talk: string
  tag_transfers: string
  tag_tactics: string
  tag_predictions: string
  tag_off_topic: string
  sort_latest: string
  sort_replies: string
  sort_views: string
  pinned: string
  locked: string
  replies: string
  views: string
  by_author: string // "by {name}"
  new_topic: string
  topic_title: string
  topic_body: string
  topic_tag: string
  create_topic: string
  cancel: string
  no_topics: string
  no_clubs: string
  next_match: string
  open_match: string
  rules_title: string
  rule_respect: string
  rule_on_topic: string
  rule_no_betting: string
  rule_no_personal: string
  rules_note: string
  breadcrumb_forums: string
  author_tag: string
  top_predictor: string
  anonymous_player: string // "Player": an author without a display name
  reply: string
  report: string
  like: string
  hidden_by_moderator: string
  hidden_rule: string // "rule: {rule}"
  rule_insult_hate: string
  rule_spam_ads: string
  rule_real_money: string
  rule_other: string
  report_title: string
  send_report: string
  report_sent: string
  write_reply: string
  reply_hint: string
  post_reply: string
  posting: string
  attach_prediction: string
  prediction_in_post: string // "Prediction · {home} {score} {away}"
  about_topic: string
  stat_replies: string
  stat_views: string
  stat_age: string
  the_match: string
  predict_score: string
  load_more: string
  topic_locked_note: string
  banned_note: string // "You cannot post until {until}."
  set_display_name: string
}

// One club's forum in the list (GET /api/forums). Its id is the club's id: the URL is /forums/<id>.
export interface ForumClub {
  id: number
  team: Team
  competition: string | null // the club's league code
  topics: number
  posts: number // posts a moderator hid are not counted
}

export type TopicTag = 'match_talk' | 'transfers' | 'tactics' | 'predictions' | 'off_topic'
export type TopicSort = 'latest' | 'replies' | 'views'

// The author of a topic or post: the display name only (null when the player has none). The API sends no
// user id and no email.
export interface ForumAuthor {
  name: string | null
}

// One topic in a club's list (GET /api/topics).
export interface ForumTopic {
  id: number
  forum: number
  title: string
  tag: TopicTag
  match: number | null
  is_pinned: boolean
  is_locked: boolean
  author: ForumAuthor
  replies: number
  views: number // distinct players who opened the topic page
  post_count: number
  created_at: string
  last_post_at: string
  last_author: string | null
}

export type ForumRule = 'insult_hate' | 'spam_ads' | 'real_money' | 'other'

// A prediction a player attached to a post (their own, for the topic's match).
export interface PostPrediction {
  home_goals: number
  away_goals: number
  home: Team
  away: Team
}

// One post of a topic (GET /api/posts). A post a moderator hid has `body: null`: its text is never sent.
export interface ForumPost {
  id: number
  topic: number
  author: ForumAuthor
  is_author: boolean // wrote the topic ("Author" tag)
  is_mine: boolean
  top_predictor: boolean // in the top 3 of the club's league in the predictions table
  created_at: string
  hidden: boolean
  hidden_rule: ForumRule | ''
  body: string | null
  likes: number
  liked_by_me: boolean
  prediction: PostPrediction | null
}
