import random
from statistics import mean

from benchmark_ai import run_game


POPULATION_SIZE = 24
GENERATIONS = 20
GAMES_PER_CANDIDATE = 8
EVALUATION_SEED = 2481
GA_SEED = 1337
MAX_PIECES = 5000

ELITE_COUNT = 4
TOURNAMENT_SIZE = 3
MUTATION_RATE = 0.25
MUTATION_SCALE = 0.12

GENE_KEYS = ("completeLines", "aggregateHeight", "holes", "bumpiness")
BOUNDS = {
    "completeLines": (0.05, 3.0),
    "aggregateHeight": (0.02, 2.0),
    "holes": (0.02, 3.0),
    "bumpiness": (0.0, 2.0),
}


def main():
    rng = random.Random(GA_SEED)
    population = [
        random_gene(rng)
        for _ in range(POPULATION_SIZE)
    ]
    best_seen = None

    print("Genetic Algorithm weight tuning")
    print(f"population={POPULATION_SIZE}, generations={GENERATIONS}")
    print(f"games/candidate={GAMES_PER_CANDIDATE}, max_pieces={MAX_PIECES}")
    print()

    for generation in range(1, GENERATIONS + 1):
        evaluated = evaluate_population(population)
        evaluated.sort(key=lambda result: result["fitness"], reverse=True)

        best = evaluated[0]
        if best_seen is None or best["fitness"] > best_seen["fitness"]:
            best_seen = best

        print_generation(generation, best, best_seen)
        population = breed_next_population(evaluated, rng)

    print_final(best_seen["weights"])


def random_gene(rng):
    return {
        key: rng.uniform(BOUNDS[key][0], BOUNDS[key][1])
        for key in GENE_KEYS
    }


def evaluate_population(population):
    return [
        evaluate_gene(gene)
        for gene in population
    ]


def evaluate_gene(gene):
    weights = weights_from_gene(gene)
    games = [
        run_game(EVALUATION_SEED + index, MAX_PIECES, weights=weights)
        for index in range(GAMES_PER_CANDIDATE)
    ]

    scores = [game["score"] for game in games]
    pieces = [game["pieces_placed"] for game in games]
    avg_score = mean(scores)
    avg_pieces = mean(pieces)

    return {
        "gene": gene,
        "weights": weights,
        "fitness": avg_score,
        "avg_score": avg_score,
        "best_score": max(scores),
        "worst_score": min(scores),
        "avg_pieces": avg_pieces,
    }


def weights_from_gene(gene):
    return {
        "completeLines": gene["completeLines"],
        "aggregateHeight": -gene["aggregateHeight"],
        "holes": -gene["holes"],
        "bumpiness": -gene["bumpiness"],
    }


def breed_next_population(evaluated, rng):
    next_population = [
        dict(result["gene"])
        for result in evaluated[:ELITE_COUNT]
    ]

    while len(next_population) < POPULATION_SIZE:
        parent_a = tournament_pick(evaluated, rng)["gene"]
        parent_b = tournament_pick(evaluated, rng)["gene"]
        child = crossover(parent_a, parent_b, rng)
        mutate(child, rng)
        next_population.append(child)

    return next_population


def tournament_pick(evaluated, rng):
    candidates = rng.sample(evaluated, TOURNAMENT_SIZE)
    return max(candidates, key=lambda result: result["fitness"])


def crossover(parent_a, parent_b, rng):
    child = {}

    for key in GENE_KEYS:
        alpha = rng.random()
        child[key] = alpha * parent_a[key] + (1.0 - alpha) * parent_b[key]

    return child


def mutate(gene, rng):
    for key in GENE_KEYS:
        if rng.random() > MUTATION_RATE:
            continue

        low, high = BOUNDS[key]
        mutation_amount = rng.gauss(0.0, (high - low) * MUTATION_SCALE)
        gene[key] = clamp(gene[key] + mutation_amount, low, high)


def print_generation(generation, best, best_seen):
    print(
        f"gen {generation:02d} | "
        f"avg_score={best['avg_score']:7.2f} | "
        f"best_score={best['best_score']:4d} | "
        f"avg_pieces={best['avg_pieces']:7.2f} | "
        f"best_so_far={best_seen['avg_score']:7.2f}"
    )


def print_final(weights):
    print()
    print("Best weights found")
    print("HEURISTIC_WEIGHTS = {")
    for key in ("aggregateHeight", "completeLines", "holes", "bumpiness"):
        print(f'    "{key}": {weights[key]:.9f},')
    print("}")

    print()
    print("Scaled constants for main.c")
    print(f"#define AI_LINE_WEIGHT {scaled_abs(weights['completeLines'])}")
    print(f"#define AI_HEIGHT_WEIGHT {scaled_abs(weights['aggregateHeight'])}")
    print(f"#define AI_HOLE_WEIGHT {scaled_abs(weights['holes'])}")
    print(f"#define AI_BUMPINESS_WEIGHT {scaled_abs(weights['bumpiness'])}")


def scaled_abs(value):
    return int(round(abs(value) * 1000000))


def clamp(value, low, high):
    return max(low, min(high, value))


if __name__ == "__main__":
    main()
