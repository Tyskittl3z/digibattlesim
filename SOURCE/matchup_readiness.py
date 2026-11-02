"""Inspect an imported matchup without inventing games or approving evidence.

Exit 2 means blocked; this command is not the historical final evaluation gate.
Printed text units inventory card content, not complete interaction branches.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from context_evolution import printed_evolution_options, UnsupportedEvolutionCondition
from match_context import CardDefinition, DeckDefinition, MatchContext, require, digest
from selected_mechanics import build_selected_registry, ORIENTATION_LINE, ORIENTATION_EFFECT, INHERITED_REACTIONS, PHASE_EFFECTS
from search_effects import SEARCH_SPECS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT = ROOT / 'ARTIFACTS/ex13-engine-2026-10-30/context.json'


def load_context_bytes(body):
    """Parse one immutable byte snapshot; provenance must hash these same bytes."""
    bundle = json.loads(body)
    raw = bundle['context']
    require(raw.get('schema') == 'imported-matchup-context-v1', 'Unknown matchup context schema')
    context = MatchContext.create(DeckDefinition.from_dict(raw['decks']['A']),
                                  DeckDefinition.from_dict(raw['decks']['B']),
                                  {k: CardDefinition.from_dict(v) for k, v in raw['cards'].items()},
                                  raw['rules'])
    require(bundle.get('matchup_id') == context.matchup_id, 'Matchup context hash mismatch')
    return context


def load_context_file(path):
    return load_context_bytes(Path(path).read_bytes())


def inspect_readiness(context, registry, root=ROOT):
    root = Path(root).resolve()
    inventory, conflicts, source_checks, blockers = [], [], [], []

    def block(code, detail):
        blockers.append({'code': code, 'detail': detail})

    rules = context.to_dict()['rules']
    if not rules.get('region'):
        block('REGION_UNSELECTED', 'EX13 and English are source labels; applicable tournament region is unconfirmed.')
    block('RULES_SNAPSHOT_UNREVIEWED', 'Official bytes retrieved; edition/effective-date pins and independent rules review remain required.')
    block('FULL_MATCH_ENGINE_UNIMPLEMENTED', 'Turn switching, scoped battlefield actions, explicit attack windows and plain security battles exist. Remaining card effects, stacked/modified battlefields, counters, Options and end triggers prevent complete selected-pair gameplay.')
    block('MECHANIC_PACK_UNREVIEWED', 'Experimental software bindings have no independent judge approval.')
    block('NO_CURRENT_FACT_FINDING_COHORT', 'Zero full current-context matches; require 60+ judge-valid matches with balanced starts and reviewed branch coverage.')
    block('ROADMAPS_UNAPPROVED', 'No current-context pilots, evaluated legal alternatives or approved best/medium/worst roadmaps.')
    block('NO_EVALUATION_FREEZE', 'No eligible context-bound freeze or final evaluation exists.')
    manifests = registry.manifest()
    bound = {(b['card_number'], b['effect_id']) for b in manifests}
    for card in context.cards:
        raw = card.to_dict()
        source = raw.get('official_source')
        try:
            require(isinstance(source, dict), 'Missing official card source')
            path = (root / source['file']).resolve()
            require(path.is_relative_to((root/'RULES').resolve()) and path.is_relative_to(root),
                    'Official source escapes RULES')
            require(path.stat().st_size > 0 and hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'],
                    'Official card source hash mismatch')
            source_checks.append({'card_number': card.number, 'status': 'HASH_MATCHED_NOT_JUDGE_CERTIFIED',
                                  'sha256': source['sha256']})
        except (ValueError, OSError, KeyError) as exc:
            block('OFFICIAL_SOURCE_UNAVAILABLE', card.number + ': ' + str(exc))
            source_checks.append({'card_number': card.number, 'status': 'UNVERIFIED'})
        for conflict in raw.get('metadata_conflicts', []):
            conflicts.append({'card_number': card.number, **conflict})
            try:
                path = (root / conflict['image_file']).resolve()
                require(path.is_relative_to((root/'RULES').resolve()) and path.is_relative_to(root),
                        'Official image source escapes RULES')
                require(hashlib.sha256(path.read_bytes()).hexdigest() == conflict['image_sha256'],
                        'Official image source hash mismatch')
            except (ValueError, OSError, KeyError) as exc:
                block('OFFICIAL_SOURCE_UNAVAILABLE', card.number + ' image: ' + str(exc))
        for field in ('main_text', 'inherited_text', 'security_text'):
            for index, line in enumerate(raw[field].splitlines()):
                if not line.strip():
                    continue
                handler = None
                if card.number == 'EX13-023' and field == 'main_text' and line == ORIENTATION_LINE:
                    handler = ORIENTATION_EFFECT
                inherited = INHERITED_REACTIONS.get(card.number)
                if field == 'inherited_text' and inherited and line == inherited[1]:
                    handler = inherited[0]
                phase_effect = PHASE_EFFECTS.get(card.number)
                if field == 'main_text' and phase_effect and line == phase_effect[2]:
                    handler = phase_effect[0]
                search = SEARCH_SPECS.get(card.number)
                if field == 'main_text' and search and line == search[1]:
                    handler = search[0]
                implemented = handler is not None and (card.number,handler) in bound
                inventory.append({'card_number': card.number, 'field': field, 'line_index': index,
                                  'printed_text': line, 'text_sha256': hashlib.sha256(line.encode()).hexdigest(),
                                  'software_handler': handler if implemented else None,
                                  'status': 'EXPERIMENTAL_UNREVIEWED' if implemented else 'UNIMPLEMENTED',
                                  'judge_review': None})
        for kind, text in raw.get('special_conditions', {}).items():
            if text:
                inventory.append({'card_number': card.number, 'field': kind, 'printed_text': text,
                                  'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                  'software_handler': None, 'status': 'UNIMPLEMENTED', 'judge_review': None})
    if conflicts:
        block('METADATA_CONFLICTS_REQUIRE_REVIEW', f'{len(conflicts)} official HTML type conflicts; selected official image values retained for review.')
    unsupported = sum(e['status'] == 'UNIMPLEMENTED' for e in inventory)
    block('PRINTED_MECHANICS_UNIMPLEMENTED', f'{unsupported} printed-text units lack complete handlers; this is not an interaction branch count.')
    routes, route_gaps = {}, []
    for seat in ('A', 'B'):
        cards = [n for n, _ in context.deck(seat).main + context.deck(seat).eggs]
        rows = []
        for base in cards:
            for target in cards:
                try:
                    for route in printed_evolution_options(context, seat, base, target):
                        rows.append({'base': base, 'target': target, **asdict(route)})
                except UnsupportedEvolutionCondition as exc:
                    route_gaps.append({'seat': seat, 'base': base, 'target': target, 'reason': str(exc)})
        routes[seat] = rows
    if route_gaps:
        block('PRINTED_EVOLUTION_SYNTAX_UNSUPPORTED', f'{len(route_gaps)} candidate base/target checks halted.')
    code = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        Path(__file__), Path(__file__).with_name('match_context.py'),
        Path(__file__).with_name('context_runtime.py'), Path(__file__).with_name('context_evolution.py'),
        Path(__file__).with_name('selected_mechanics.py'),Path(__file__).with_name('effect_scheduler.py'),
        Path(__file__).with_name('match_preparation.py'),Path(__file__).with_name('phase_flow.py'),
        Path(__file__).with_name('main_actions.py'),Path(__file__).with_name('breeding_evolution.py'),
        Path(__file__).with_name('search_effects.py'),Path(__file__).with_name('turn_flow.py'),
        Path(__file__).with_name('battlefield_scope.py'),Path(__file__).with_name('attack_flow.py'),
        Path(__file__).with_name('printed_triggers.py'),Path(__file__).with_name('selected_contexts.py')]}
    return {'schema': 'imported-matchup-readiness-v1', 'status': 'BLOCKED',
            'context_id': context.matchup_id, 'engine_source_sha256': code,
            'decks': {s: context.deck(s).to_dict() for s in ('A', 'B')},
            'counts': {'distinct_cards': len(context.cards),
                       'main_cards': {s: sum(q for _,q in context.deck(s).main) for s in ('A','B')},
                       'digi_eggs': {s: sum(q for _,q in context.deck(s).eggs) for s in ('A','B')},
                       'software_only_mechanic_bindings': len(manifests),
                       'printed_text_units': len(inventory), 'unsupported_printed_text_units': unsupported,
                       'fact_finding_attempts': 0, 'judge_valid_fact_finding_matches': 0,
                       'approved_roadmap_lanes': 0, 'final_matches': 0},
            'requirements': {'fact_finding_minimum': 60, 'fact_finding_starts_each': 30,
                             'final_matches': 10000, 'final_starts_each': 5000},
            'blockers': blockers, 'source_checks': source_checks, 'metadata_conflicts': conflicts,
            'experimental_packs': manifests, 'printed_text_inventory': inventory,
            'printed_evolution_candidates': routes, 'printed_evolution_gaps': route_gaps,
            'note': 'No historical matches, pilots or roadmaps were imported. Inventory and scenarios count as zero full matches.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        context = load_context_file(args.context)
        report = inspect_readiness(context, build_selected_registry(context, args.root), args.root)
        if args.out:
            # Existing records are immutable evidence. Request a new output name.
            with args.out.open('x', encoding='utf-8') as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
                handle.write('\n')
        print(json.dumps({'status': report['status'], 'context_id': context.matchup_id,
                          'counts': report['counts'], 'blockers': report['blockers']}, indent=2))
        return 2
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'status': 'BLOCKED_INPUT_ERROR', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
