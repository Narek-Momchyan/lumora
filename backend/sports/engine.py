"""Lumora's football odds: a Dixon–Coles Poisson model. Pure Python, no Django, no database.

Every team has an attack and a defence rating, every competition a base scoring rate and a home
advantage. The expected goals of a match are

    λ_home = exp(base_c + home_c + attack_home − defence_away)
    λ_away = exp(base_c          + attack_away − defence_home)

and each side's goals follow a Poisson distribution. Dixon–Coles multiplies the four low scores
(0-0, 1-0, 0-1, 1-1) by τ(ρ), because real football has more draws there than two independent
Poissons give. The ratings are fitted to past results by maximum likelihood, with recent matches
weighted more (time decay) and a penalty that pulls a team with few matches towards the average
(shrinkage). All six competitions are fitted together: Champions League matches link the leagues,
so a Premier League side and a Serie A side are rated on one scale.

From the score matrix come every market's fair probabilities; a margin turns them into odds.
"""

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal

MAIN_MARGIN = 0.055  # 1X2, double chance, totals, both teams to score
CORRECT_SCORE_MARGIN = 0.15
MIN_ODDS = Decimal("1.01")
MAX_ODDS = Decimal("500.00")

HALF_LIFE_DAYS = 120  # a match four months old counts half
SHRINKAGE = 4.0  # L2 penalty on attack and defence: the weight of the "average team" prior
MAX_GOALS = 10  # the score matrix goes up to 10-10; the rest is renormalised away
TOTAL_LINES = (Decimal("0.5"), Decimal("1.5"), Decimal("2.5"), Decimal("3.5"), Decimal("4.5"))
CORRECT_SCORES = tuple(f"{home}-{away}" for home in range(4) for away in range(4))
RHO_GRID = tuple(round(-0.20 + step * 0.005, 3) for step in range(61))  # −0.20 … 0.10

ONE_X_TWO = "1x2"
DOUBLE_CHANCE = "double_chance"
TOTAL = "total"
BTTS = "btts"
CORRECT_SCORE = "correct_score"


@dataclass(frozen=True)
class Result:
    """One finished match, with the regular-time score (extra time is not football's 90 minutes)."""

    competition: str
    home: int
    away: int
    home_goals: int
    away_goals: int
    day: date


@dataclass
class Ratings:
    base: dict = field(default_factory=dict)  # competition -> log of the away side's goals per match
    home: dict = field(default_factory=dict)  # competition -> home advantage
    attack: dict = field(default_factory=dict)  # team -> attack rating (0 = average)
    defence: dict = field(default_factory=dict)  # team -> defence rating (0 = average)
    rho: float = 0.0
    matches: int = 0

    def as_dict(self):
        return {
            "base": self.base,
            "home": self.home,
            "attack": {str(team): value for team, value in self.attack.items()},
            "defence": {str(team): value for team, value in self.defence.items()},
            "rho": self.rho,
            "matches": self.matches,
        }


# ---------------------------------------------------------------- fitting


def weight(result_day, today, half_life=HALF_LIFE_DAYS):
    return 0.5 ** (max((today - result_day).days, 0) / half_life)


def fit(results, today, half_life=HALF_LIFE_DAYS, shrinkage=SHRINKAGE, iterations=200, tolerance=1e-6):
    """Ratings that maximise the weighted Poisson likelihood minus the shrinkage penalty.

    Newton's method one block at a time (attacks, defences, bases, home advantages). Inside a block
    the parameters never meet in one equation, so each one's step is exact and independent:
    step = gradient / curvature, where gradient = Σ w (goals − expected) and
    curvature = Σ w expected (+ shrinkage for team ratings).
    """
    games = [(r, weight(r.day, today, half_life)) for r in results]
    ratings = Ratings(matches=len(games))
    if not games:
        return ratings

    for r, _ in games:
        for team in (r.home, r.away):
            ratings.attack.setdefault(team, 0.0)
            ratings.defence.setdefault(team, 0.0)
        ratings.base.setdefault(r.competition, math.log(1.2))
        ratings.home.setdefault(r.competition, 0.25)

    for _ in range(iterations):
        change = 0.0
        for block in ("attack", "defence", "base", "home"):
            grad, curv = {}, {}
            for r, w in games:
                lam, mu = expected_goals(ratings, r.competition, r.home, r.away)
                if block == "attack":
                    terms = [(r.home, r.home_goals - lam, lam), (r.away, r.away_goals - mu, mu)]
                elif block == "defence":  # defence lowers the opponent's goals: the sign flips
                    terms = [(r.away, lam - r.home_goals, lam), (r.home, mu - r.away_goals, mu)]
                elif block == "base":
                    terms = [(r.competition, r.home_goals - lam + r.away_goals - mu, lam + mu)]
                else:
                    terms = [(r.competition, r.home_goals - lam, lam)]
                for key, g, h in terms:
                    grad[key] = grad.get(key, 0.0) + w * g
                    curv[key] = curv.get(key, 0.0) + w * h

            values = getattr(ratings, block)
            penalty = shrinkage if block in ("attack", "defence") else 0.0
            for key, g in grad.items():
                step = (g - penalty * values[key]) / (curv[key] + penalty)
                values[key] += step
                change = max(change, abs(step))
        if change < tolerance:
            break

    ratings.rho = fit_rho(games, ratings)
    return ratings


def fit_rho(games, ratings):
    """The ρ that makes the low scores most likely, given the fitted expected goals (a grid search)."""
    best, best_ll = 0.0, -math.inf
    for rho in RHO_GRID:
        ll = 0.0
        for r, w in games:
            lam, mu = expected_goals(ratings, r.competition, r.home, r.away)
            t = tau(r.home_goals, r.away_goals, lam, mu, rho)
            if t <= 0:
                ll = -math.inf
                break
            ll += w * math.log(t)
        if ll > best_ll:
            best, best_ll = rho, ll
    return best


# ---------------------------------------------------------------- one match


def expected_goals(ratings, competition, home, away):
    base = ratings.base.get(competition, math.log(1.2))
    advantage = ratings.home.get(competition, 0.0)
    lam = math.exp(base + advantage + ratings.attack.get(home, 0.0) - ratings.defence.get(away, 0.0))
    mu = math.exp(base + ratings.attack.get(away, 0.0) - ratings.defence.get(home, 0.0))
    return lam, mu


def tau(home_goals, away_goals, lam, mu, rho):
    """Dixon–Coles correction: only the four lowest scores move, the total stays 1."""
    if home_goals == 0 and away_goals == 0:
        return 1 - lam * mu * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + lam * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + mu * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)


def score_matrix(lam, mu, rho=0.0, max_goals=MAX_GOALS):
    """P(home scores x, away scores y) for x, y in 0..max_goals, summing to 1."""
    home = [poisson(x, lam) for x in range(max_goals + 1)]
    away = [poisson(y, mu) for y in range(max_goals + 1)]
    matrix = [[home[x] * away[y] * tau(x, y, lam, mu, rho) for y in range(max_goals + 1)] for x in range(max_goals + 1)]
    total = sum(map(sum, matrix))
    return [[p / total for p in row] for row in matrix]


def market_probabilities(matrix):
    """{(kind, line, code): fair probability} for every market we offer."""
    cells = [(x, y, p) for x, row in enumerate(matrix) for y, p in enumerate(row)]
    home = sum(p for x, y, p in cells if x > y)
    draw = sum(p for x, y, p in cells if x == y)
    away = sum(p for x, y, p in cells if x < y)
    probabilities = {
        (ONE_X_TWO, None, "home"): home,
        (ONE_X_TWO, None, "draw"): draw,
        (ONE_X_TWO, None, "away"): away,
        (DOUBLE_CHANCE, None, "1X"): home + draw,
        (DOUBLE_CHANCE, None, "12"): home + away,
        (DOUBLE_CHANCE, None, "X2"): draw + away,
    }
    for line in TOTAL_LINES:
        over = sum(p for x, y, p in cells if x + y > line)
        probabilities[(TOTAL, line, "over")] = over
        probabilities[(TOTAL, line, "under")] = 1 - over
    yes = sum(p for x, y, p in cells if x > 0 and y > 0)
    probabilities[(BTTS, None, "yes")] = yes
    probabilities[(BTTS, None, "no")] = 1 - yes
    shown = 0.0
    for code in CORRECT_SCORES:
        x, y = map(int, code.split("-"))
        probabilities[(CORRECT_SCORE, None, code)] = matrix[x][y]
        shown += matrix[x][y]
    probabilities[(CORRECT_SCORE, None, "other")] = 1 - shown
    return probabilities


def margin_for(kind):
    return CORRECT_SCORE_MARGIN if kind == CORRECT_SCORE else MAIN_MARGIN


def price(probability, margin):
    """Odds with the margin: 1 / (p · (1 + margin)), rounded down to 0.01, between 1.01 and 500."""
    if probability <= 0:
        return MAX_ODDS
    odds = Decimal(1 / (probability * (1 + margin))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return min(max(odds, MIN_ODDS), MAX_ODDS)


def match_odds(ratings, competition, home, away):
    """{(kind, line, code): (fair probability, odds)} for one upcoming match."""
    lam, mu = expected_goals(ratings, competition, home, away)
    probabilities = market_probabilities(score_matrix(lam, mu, ratings.rho))
    return {key: (p, price(p, margin_for(key[0]))) for key, p in probabilities.items()}


# ---------------------------------------------------------------- settlement


def selection_wins(kind, line, code, home_goals, away_goals):
    """Did this pick win on the regular-time score? (Extra time and penalties never count.)"""
    if kind == ONE_X_TWO:
        outcome = "home" if home_goals > away_goals else "away" if home_goals < away_goals else "draw"
        return code == outcome
    if kind == DOUBLE_CHANCE:
        outcome = "1" if home_goals > away_goals else "2" if home_goals < away_goals else "X"
        return outcome in code
    if kind == TOTAL:
        over = home_goals + away_goals > line
        return over if code == "over" else not over
    if kind == BTTS:
        both = home_goals > 0 and away_goals > 0
        return both if code == "yes" else not both
    if kind == CORRECT_SCORE:
        score = f"{home_goals}-{away_goals}"
        return score == code if code != "other" else score not in CORRECT_SCORES
    raise ValueError(f"Unknown market {kind!r}")


# ---------------------------------------------------------------- simulation and backtest


def sample_score(matrix, u):
    """The score whose cumulative probability first passes u (u uniform in [0, 1))."""
    cumulative = 0.0
    for x, row in enumerate(matrix):
        for y, p in enumerate(row):
            cumulative += p
            if u < cumulative:
                return x, y
    return len(matrix) - 1, len(matrix) - 1


def one_x_two(matrix):
    probabilities = market_probabilities(matrix)
    return [probabilities[(ONE_X_TWO, None, code)] for code in ("home", "draw", "away")]


def scores(probabilities, home_goals, away_goals):
    """(log loss, Brier score) of a 1X2 forecast [home, draw, away] for the real result."""
    outcome = 0 if home_goals > away_goals else 2 if home_goals < away_goals else 1
    log_loss = -math.log(max(probabilities[outcome], 1e-12))
    brier = sum((p - (1 if index == outcome else 0)) ** 2 for index, p in enumerate(probabilities))
    return log_loss, brier


def backtest(results, min_history=60):
    """Walk forward through the season: each day is predicted only from the days before it.

    Returns the average 1X2 log loss and Brier score of the model and of a baseline that only knows
    how often home wins, draws and away wins happened in each competition so far.
    """
    results = sorted(results, key=lambda r: r.day)
    days = sorted({r.day for r in results})
    model = [0.0, 0.0]
    baseline = [0.0, 0.0]
    predicted = 0
    for day in days:
        history = [r for r in results if r.day < day]
        if len(history) < min_history:
            continue
        ratings = fit(history, day)
        for r in (r for r in results if r.day == day):
            lam, mu = expected_goals(ratings, r.competition, r.home, r.away)
            forecast = one_x_two(score_matrix(lam, mu, ratings.rho))
            loss, brier = scores(forecast, r.home_goals, r.away_goals)
            model[0] += loss
            model[1] += brier
            loss, brier = scores(frequencies(history, r.competition), r.home_goals, r.away_goals)
            baseline[0] += loss
            baseline[1] += brier
            predicted += 1
    if not predicted:
        return {"matches": 0}
    return {
        "matches": predicted,
        "model_log_loss": model[0] / predicted,
        "model_brier": model[1] / predicted,
        "baseline_log_loss": baseline[0] / predicted,
        "baseline_brier": baseline[1] / predicted,
    }


def frequencies(history, competition):
    """Home / draw / away shares in this competition so far (add-one smoothing; all leagues if new)."""
    rows = [r for r in history if r.competition == competition] or history
    counts = [1, 1, 1]
    for r in rows:
        counts[0 if r.home_goals > r.away_goals else 2 if r.home_goals < r.away_goals else 1] += 1
    total = sum(counts)
    return [count / total for count in counts]
