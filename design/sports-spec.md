# Lumora Football — product spec

Narek's decisions from November 2026. Lumora becomes **football first**: demo bets and score
predictions on top football leagues, plus club forums. The casino games (Neon Crash, Zeus
Legacy, Lumora Roulette) stay as a second section, "Casino". All the rules in `CLAUDE.md` still
apply: **demo coins (LC) only**, no real money, no prizes, money moves only through
`wallet/services.py`, every text from the admin in en/am/ru.

Designs: `design/06-sports-home.png` … `design/12-forum-topic.png` (PNG mock-ups, 1440 wide,
some pages are taller because they scroll). Build only what the API supports.

---

## 1. Theme: "Night stadium" and the Sports | Casino switch

- The sidebar starts with a **Sports | Casino** switch (design 06). Sports routes use the green
  "night stadium" theme, casino routes the existing neon theme. Wallet and Leaderboard keep the
  mode the player chose last (cookie `mode`).
- One set of Tailwind class names, two sets of values: the tokens are CSS variables and the
  sports values are set under `[data-theme="sports"]` on `<html>`. Components never check the
  theme themselves.

| Token | Casino (now) | Sports |
| --- | --- | --- |
| bg | #07080F | #04100A |
| surface | #11131F | #0A1A11 |
| surface2 | #191C2C | #0F2418 |
| border | #272B45 | #1B3A27 |
| text | #F2F4FF | #EEFFF3 |
| muted | #8A90B3 | #7FA08D |
| cyan (main accent) | #00E5FF | #B6FF3B (lime) |
| magenta (second accent) | #FF2BD6 | #1FD67A (grass) |
| lime | #B6FF3B | #B6FF3B |
| danger | #FF4D6D | #FF4D6D |

In sports the names `cyan` and `magenta` would no longer match their colours, so S0 may rename
them to `accent` and `accent2` everywhere (propose it in the plan).

- Background in sports: dark green with faint vertical mowing stripes, two floodlight glows at
  the top, pitch lines (halfway line, centre circle, boxes) on hero cards.
- Selected odds: lime fill with dark text and a glow. Primary button: lime → grass gradient.
- Clubs show **their crests**. The sync saves the crest image that football-data.org gives for
  each team (`crest`) into `Team.crest`, an image field like our other images, replaceable in the
  admin. While an image is missing or fails to load, the club's initials in its colours (admin
  fields: short code, colour, text colour) are shown instead; the PNG mock-ups show only this
  fallback. Leagues keep country flags (a star for the Champions League).

### Animations (use `motion`, respect `prefers-reduced-motion`, pause when the tab is hidden)
1. **Switching to Sports**: a green wave sweeps across the screen from the switch (~600 ms) with
   a rolling ball, and the tokens cross-fade to green. Back to Casino: the same with neon.
2. **Background**: the floodlight glows drift slowly, the grass stripes shimmer softly.
3. **Live**: the red live dot pulses; a new score flips the digits and the card gets a green
   "GOAL" burst; when odds change, the button flashes ▲ green or ▼ red for 2 s.
4. **Bet slip**: the picked odds button pulses and a chip flies into the slip, the count badge
   bounces; "Place bet" turns into ✓; when a bet is won while the player is online, lime/green
   confetti.
5. **Predictions**: the focused score box glows; the +3 / +1 badge pops when a match is scored.

## 2. Data

- **football-data.org** (free plan, 10 requests/minute, key in `.env`): competitions `PL`, `PD`,
  `SA`, `BL1`, `FL1`, `CL`; teams, fixtures, results and standings. It is the **only source for
  settlement** (final score). The free plan delays scores and has no odds, lineups or player
  data, so we do not show those.
- **API-Football** (free plan, 100 requests/day, key in `.env`): only live scores and minutes
  while one of our matches is in play (`fixtures?live=all`, filtered by our league ids). Poll
  about every 5 minutes, only between kickoff and kickoff + 130 min, with a daily budget guard
  (stop at 90 requests). First check that the free plan returns the current season; if it does
  not, show football-data's delayed score with an "updates with delay" label instead.
- Each provider sits behind an adapter (`sports/providers/…`), so a paid live feed can replace
  it later. A sync command/runner stores everything in our database; the frontend never calls a
  provider. Team names that differ between providers are matched through an alias table.
- Tests never call the network: they use recorded JSON fixtures.

## 3. Odds model (pure `sports/engine.py`)

- Poisson model: λ_home = exp(μ + home_adv + attack_home − defence_away), λ_away likewise
  without home advantage. Fit attack/defence on recent results with time decay and shrink to the
  league average when a team has few matches (promoted teams start weaker).
- From the score matrix: 1X2, Double chance, Over/Under 0.5–4.5, Both teams to score,
  Correct score (0-0 … 3-3 and "Other").
- Margin: about 5–6 % on the main markets, about 15 % on correct score (constants). Odds are
  rounded down to 2 decimals, never below 1.01. Show the fair probabilities as "Lumora model".
- Odds are recomputed when new results arrive and **frozen at kickoff**.
- Tests: every market's probabilities sum to 1, the overround matches the margin, and a
  200,000-match simulation from the model returns 1/(1+margin) to a bettor (Rule 7 for sports).

## 4. Bets

- **Pre-match only**: bets close at kickoff by server time. No in-play betting, no cash-out.
- **Single** and **Express** (2–10 picks, each from a different match; odds multiply; a cap on
  total odds and on the potential win, constants).
- The request sends the odds the player saw; if the odds have changed, answer `409` with code
  `odds_changed` and the new odds, and the player confirms again.
- Stake limits as constants (for example 1–5,000 LC). Debit through `wallet.services`, idempotency
  key, Decimal, one transaction.
- **Settlement** after football-data marks the match FINISHED, on the regular-time score (90 min
  + stoppage; extra time and penalties do not count). Idempotent job. Postponed, cancelled or
  abandoned matches: the pick is **void** (single → refund, express → that pick counts as 1.00).
  Any lost pick loses the express.
- My bets (design 08): open / settled / all, weekly staked, returned, profit, won count.

## 5. Predictions (free, no LC)

- One prediction per player per match, editable until kickoff.
- After full time: exact score **3 points**, right result **1 point**.
- Leaderboards per league: matchday and season. Ties: more exact scores, then the earlier
  prediction.

## 6. Club forums (design 11, 12)

- One forum per club of our competitions (created by the sync). Topics with a tag (match talk,
  transfers, tactics, predictions, off-topic), posts, likes. Logged-in players only.
- Moderation: Report button with a reason (insult or hate, spam or ads, real-money betting,
  other); in the admin, moderators hide/unhide posts, pin and lock topics, and ban a player from
  posting until a date. Hidden posts show "hidden by a moderator".
- Limits: one post every 30 s, 10 topics a day, post length 1–2,000 characters, no links, a
  banned-words list per language edited in the admin. Every refusal is an `ErrorMessage` code.
- Player text is not translated; all interface text comes from the admin like everywhere else.

## 7. Routes

| Route | Design |
| --- | --- |
| `/` Football home (featured match, live now, matches by league, bet slip, predictions) | 06 |
| `/matches/[id]` match page with all markets, predict the score, fan talk | 07 |
| `/my-bets` | 08 |
| `/predictions` | 09 |
| `/leagues/[code]` matches, table, results | 10 |
| `/live` live matches | – (like the live cards of 06) |
| `/forums`, `/forums/[club]`, `/forums/[club]/[topic]` | 11, 12 |
| `/casino` the old lobby; `/crash`, `/zeus-legacy`, `/roulette` stay | 02–05 |

Sports sidebar: Football, Live, the 6 leagues, then My bets, Predictions, Club forums,
Leaderboard, Wallet. Casino sidebar: Lobby, Slots, Crash, Table games, Wallet, Leaderboard.

## 8. Phases (one Claude Code session each, plan first, Narek reviews)

- **S0** Theme tokens + Sports | Casino switch + both sidebars + shared UI kit
  (`components/ui/`) + casino pages consistent with designs 01–05.
- **S1** `sports` backend data: competitions, teams (colours, aliases), matches, standings,
  football-data sync with rate limits, admin, tests on recorded JSON.
- **S2** Odds engine, markets, bets (single/express), settlement, void rules, tests and the
  200k simulation.
- **S3** Frontend: Football home, match page, bet slip, My bets (designs 06–08) + animations 1–4.
- **S4** Predictions and leaderboards (design 09), league pages (design 10).
- **S5** Live scores (API-Football, budget guard) over `/ws/sports`, live page.
- **S6** Club forums with moderation (designs 11–12).

Out of scope: in-play betting, cash-out, player statistics, league logos, real bookmaker odds,
anything with real money.
