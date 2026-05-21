from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fc24eda.data_loader import load_challenges, load_players, select_price_bounds
from fc24eda.eda_solver import build_structured_slot_domains
from fc24eda.fitness import evaluate_solution, explain_unmet_requirements
from fc24eda.sbc_core import player_name, repair_duplicate_names_deterministic


def test_evaluate_first_challenge_with_first_players():
    players = load_players()
    challenge = load_challenges()[0]
    bounds = select_price_bounds("club")
    result = evaluate_solution(list(range(11)), players, challenge, bounds)
    assert result.team_price >= 0
    assert result.unmet_requirements >= 0
    assert len(result.indices) == 11


def test_repair_duplicate_names_keeps_unique_names():
    players = load_players()
    repaired = repair_duplicate_names_deterministic([15, 15, 15] + list(range(8)), players)
    names = [player_name(players[idx]) for idx in repaired]
    assert len(names) == len(set(names))


def test_structured_domains_match_slots_and_size():
    players = load_players()
    challenge = load_challenges()[0]
    domains = build_structured_slot_domains(players, challenge, domain_size=50)
    assert len(domains) == len(challenge["positions"])
    assert all(len(domain) == 50 for domain in domains)
    assert all(0 <= idx < len(players) for domain in domains for idx in domain)


def test_explain_unmet_requirements_matches_unmet_count():
    players = load_players()
    challenge = load_challenges()[0]
    bounds = select_price_bounds("club")
    result = evaluate_solution(list(range(11)), players, challenge, bounds)
    details = explain_unmet_requirements(result.team_info, challenge["requirements"])
    assert len(details) == result.unmet_requirements
