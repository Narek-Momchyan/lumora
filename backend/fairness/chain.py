"""Hash chains for rounds shared by all players, see fairness/rng.py for how they work."""

from .rng import new_server_seed, walk_chain


def new_chain(model, length):
    last_seed = new_server_seed()
    return model.objects.create(last_seed=last_seed, commitment=walk_chain(last_seed, length), length=length)


def next_link(model, last_round, length):
    """The chain and position of the round after `last_round`. A finished chain gets a new one."""
    chain, position = (last_round.chain, last_round.position + 1) if last_round else (None, 0)
    if chain is None or position >= chain.length:
        return new_chain(model, length), 0
    return chain, position


def seed_at(chain, position):
    return walk_chain(chain.last_seed, chain.length - 1 - position)
