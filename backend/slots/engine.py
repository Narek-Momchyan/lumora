"""Zeus Legacy maths. Pure functions: no database, no Django, every random number comes from `stream`.

`stream` is an iterator of uniform floats in [0, 1): fairness.rng.float_stream in the game,
so a whole round can be recomputed from one nonce.

The grid is 5 rows of 6 columns. A symbol pays when 8 or more are anywhere on the grid. Winning
symbols explode, the others fall and new ones drop in, until a grid has no win. Scatters and
multipliers never explode. 4+ scatters pay once and start 15 free spins (+5 when it happens
during free spins). Multipliers that landed in a spin with a win are added together and multiply
that spin's symbol wins, never the scatter win. In free spins the sum carries over to the next
spin, but it only counts in a spin that collected a new multiplier.

All pays are whole numbers in hundredths of the bet (0.25x = 25), so the maths has no floats and
no rounding. Turning them into LC is the job of win_amount().
"""

from bisect import bisect_right
from decimal import ROUND_DOWN, Decimal
from itertools import accumulate

ROWS = 5
COLS = 6
MIN_WIN_COUNT = 8
MAX_TUMBLES = 30

SCATTER = "scatter"
MIN_SCATTERS = 4
FREE_SPINS_AWARD = 15
FREE_SPINS_RETRIGGER = 5

BONUS_BUY_COST = 100  # times the bet
SCATTERS_ON_BONUS_BUY = 4

MAX_WIN = 100_000  # 1000x, for one spin
BONUS_BUY_SPIN_MAX_WIN = 1_000  # 10x, for the spin that opens a bought bonus

# symbol: (pay for 8-9, for 10-11, for 12+)
PAYTABLE = {
    "trident": (1000, 2500, 5000),
    "pegasus": (250, 1000, 2500),
    "shield": (200, 500, 1500),
    "chalice": (150, 200, 1200),
    "red_stone": (100, 150, 1000),
    "purple_stone": (80, 120, 800),
    "yellow_stone": (50, 100, 500),
    "green_stone": (40, 90, 400),
    "blue_stone": (25, 75, 200),
}
SCATTER_PAY = {4: 300, 5: 500, 6: 10_000}  # 6 or more pay the same
MULTIPLIERS = {
    "mult_2": 2,
    "mult_5": 5,
    "mult_10": 10,
    "mult_25": 25,
    "mult_50": 50,
    "mult_100": 100,
    "mult_250": 250,
    "mult_500": 500,
}

# symbol: (weight in the base game, weight in free spins)
WEIGHTS = {
    "trident": (3500, 5000),
    "pegasus": (5500, 7000),
    "shield": (7500, 9000),
    "chalice": (9500, 11000),
    "red_stone": (15000, 14000),
    "purple_stone": (17000, 16000),
    "yellow_stone": (19000, 18000),
    "green_stone": (21000, 19000),
    "blue_stone": (22000, 20000),
    SCATTER: (2030, 2500),
    "mult_2": (130, 2900),
    "mult_5": (50, 1450),
    "mult_10": (20, 680),
    "mult_25": (5, 240),
    "mult_50": (2, 100),
    "mult_100": (1, 40),
    "mult_250": (0, 15),
    "mult_500": (0, 5),
}
SYMBOLS = tuple(WEIGHTS)

# Jackpot tiers from the rarest to the most common. A tier's chance is stake * rate / seed, so it
# doesn't depend on the bet size: a pool is won on average after it has grown by one more seed.
JACKPOT_TIERS = ("GRAND", "MAJOR", "MINOR", "MINI")
JACKPOT_SEEDS = {
    "MINI": Decimal("100.00"),
    "MINOR": Decimal("500.00"),
    "MAJOR": Decimal("5000.00"),
    "GRAND": Decimal("50000.00"),
}
JACKPOT_RATES = {
    "MINI": Decimal("0.0020"),
    "MINOR": Decimal("0.0010"),
    "MAJOR": Decimal("0.0005"),
    "GRAND": Decimal("0.0002"),
}


def _table(weights):
    """Cumulative weights, for a fast weighted draw: (symbols, running totals, total)."""
    running = list(accumulate(weights))
    return SYMBOLS, running, running[-1]


BASE_TABLE = _table([base for base, _ in WEIGHTS.values()])
FREE_TABLE = _table([free for _, free in WEIGHTS.values()])
# The first spin of a bought bonus has no multipliers.
NO_MULTIPLIER_TABLE = _table([0 if symbol in MULTIPLIERS else base for symbol, (base, _) in WEIGHTS.items()])


def draw(stream, table):
    symbols, running, total = table
    return symbols[bisect_right(running, int(next(stream) * total))]


def new_grid(stream, table):
    return [[draw(stream, table) for _ in range(COLS)] for _ in range(ROWS)]


def force_scatters(grid, stream, count):
    """Puts scatters on random cells until the grid has `count` of them."""
    needed = count - sum(row.count(SCATTER) for row in grid)
    if needed <= 0:
        return
    cells = [(row, col) for row in range(ROWS) for col in range(COLS) if grid[row][col] != SCATTER]
    for i in range(len(cells) - 1, 0, -1):  # Fisher-Yates
        j = int(next(stream) * (i + 1))
        cells[i], cells[j] = cells[j], cells[i]
    for row, col in cells[:needed]:
        grid[row][col] = SCATTER


def symbol_pay(symbol, count):
    if count < MIN_WIN_COUNT:
        return 0
    return PAYTABLE[symbol][0 if count < 10 else 1 if count < 12 else 2]


def evaluate(grid):
    """Returns (wins, winning cells, pay). Only paytable symbols win here."""
    cells = {}
    for row, symbols in enumerate(grid):
        for col, symbol in enumerate(symbols):
            cells.setdefault(symbol, []).append((row, col))

    wins = []
    winning = []
    total = 0
    for symbol, found in cells.items():
        if symbol in PAYTABLE and (pay := symbol_pay(symbol, len(found))):
            wins.append({"symbol": symbol, "count": len(found), "pay": pay})
            winning.extend(found)
            total += pay
    return wins, winning, total


def tumble(grid, winning, stream, table):
    """Winning cells empty, the rest fall down, new symbols fill each column from the top."""
    removed = set(winning)
    columns = []
    for col in range(COLS):
        kept = [grid[row][col] for row in range(ROWS) if (row, col) not in removed]
        columns.append([draw(stream, table) for _ in range(ROWS - len(kept))] + kept)
    return [[columns[col][row] for col in range(COLS)] for row in range(ROWS)]


def grid_multipliers(grid):
    return [MULTIPLIERS[symbol] for row in grid for symbol in row if symbol in MULTIPLIERS]


def scatter_pay(count):
    return SCATTER_PAY[min(count, 6)]


def play_spin(stream, *, is_free_spin=False, global_multiplier=0, bought=False):
    """One spin with all its tumbles. `bought` is the first spin of a bought bonus."""
    if is_free_spin:
        table = FREE_TABLE
    elif bought:
        table = NO_MULTIPLIER_TABLE
    else:
        table = BASE_TABLE

    grid = new_grid(stream, table)
    if bought:
        force_scatters(grid, stream, SCATTERS_ON_BONUS_BUY)

    symbol_win = 0
    scatter_win = 0
    triggered = False
    is_max_win = False
    steps = []

    for _ in range(MAX_TUMBLES):
        wins, winning, pay = evaluate(grid)
        scatters = sum(row.count(SCATTER) for row in grid)
        if scatters >= MIN_SCATTERS:
            triggered = True
            scatter_win = scatter_pay(scatters)  # assigned, not added: scatters pay once per spin

        symbol_win += pay
        pending = sum(grid_multipliers(grid))
        applied = global_multiplier + pending if symbol_win and pending else 1
        running_win = symbol_win * applied + scatter_win
        capped = running_win >= MAX_WIN
        is_max_win = is_max_win or capped

        steps.append(
            {
                "grid": [row[:] for row in grid],
                "wins": [] if capped else wins,
                "winning_cells": [] if capped else [list(cell) for cell in winning],
                "pay": 0 if capped else pay,
                "running_win": min(running_win, MAX_WIN),
            }
        )
        if not winning or capped:
            break
        grid = tumble(grid, winning, stream, table)
    else:
        # The tumble limit: the grid after the last tumble is the one multipliers are read from.
        steps.append(
            {"grid": [row[:] for row in grid], "wins": [], "winning_cells": [], "pay": 0, "running_win": steps[-1]["running_win"]}
        )

    collected = grid_multipliers(grid) if symbol_win else []
    collected_sum = sum(collected)
    global_multiplier += collected_sum
    final_multiplier = global_multiplier if collected_sum else 1

    win = min(symbol_win * final_multiplier + scatter_win, MAX_WIN)
    if bought:
        win = min(win, BONUS_BUY_SPIN_MAX_WIN)

    awarded = 0
    if triggered:
        awarded = FREE_SPINS_RETRIGGER if is_free_spin else FREE_SPINS_AWARD

    return {
        "is_free_spin": is_free_spin,
        "steps": steps,
        "scatter_win": scatter_win,
        "collected_multipliers": collected,
        "global_multiplier": global_multiplier,
        "win": win,
        "free_spins_awarded": awarded,
        "is_max_win": is_max_win,
    }


def play_round(stream, *, bonus_buy=False):
    """A paid spin plus all the free spins it opens. Returns the whole round."""
    first = play_spin(stream, bought=bonus_buy)
    spins = [first]
    total = first["win"]
    free_spins_left = first["free_spins_awarded"]
    multiplier = 0

    while free_spins_left > 0:
        spin = play_spin(stream, is_free_spin=True, global_multiplier=multiplier)
        spins.append(spin)
        total += spin["win"]
        multiplier = spin["global_multiplier"]
        free_spins_left += spin["free_spins_awarded"] - 1
        if spin["is_max_win"]:
            free_spins_left = 0  # reaching the max win ends the bonus

    return {
        "spins": spins,
        "total_win": total,
        "free_spins_played": len(spins) - 1,
        "bonus_buy": bonus_buy,
    }


def stake_for(amount, bonus_buy):
    return amount * BONUS_BUY_COST if bonus_buy else amount


def win_amount(amount, total_win):
    """LC for a round: `total_win` is in hundredths of the bet. Rounds down to 0.01."""
    return (amount * total_win / 100).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def jackpot_chance(tier, stake):
    return float(stake) * float(JACKPOT_RATES[tier]) / float(JACKPOT_SEEDS[tier])


def roll_jackpot(stake, r):
    """The tier won by a spin of this stake, or None. `r` is a uniform float in [0, 1)."""
    cursor = 0.0
    for tier in JACKPOT_TIERS:
        cursor += jackpot_chance(tier, stake)
        if r < cursor:
            return tier
    return None
