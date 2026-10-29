"""Strict current runner and reproducible evidence for the loaded pair only.

Historical V12 reports remain reproducible; they are not rules certificates.
"""
from collections import Counter
from dataclasses import fields, is_dataclass
import gzip
import hashlib
import json
from pathlib import Path
import random
import re
import sys

from loaded_digivolution import BY_SEAT, MANIFEST
from loaded_effects import Copy, JudgeHalt
from matchup_v12_attack_sources import MatchV12
from full_match_attempt import Player, src
from seeded_opening_probe import _select_main_action


class EvidenceMatch(MatchV12):
    """Adds software integrity checks; never claims rules certification."""
    SCORER_ID = 'loaded-pair-v13-integrity-evidence'

    def _log_choice(self, choice_type, seat, candidates, chosen, **fields):
        players = {}
        for owner, player in self.ps.items():
            players[owner] = {
                'battle': [c.key() for c in player.z.battle],
                'stacks': _state_value(player.stacks),
                'breeding': [c.key() for c in player.breeding],
                'trash': [c.key() for c in player.z.trash],
                'statuses': _state_value(player.z.statuses),
                'suspended': sorted(player.suspended), 'sick': sorted(player.sick),
                'once_used': sorted(player.once_used),
                'security_count': len(player.z.security),
                'deck_count': len(player.z.deck), 'hand_count': len(player.z.hand),
            }
        position = {'memory': self.mem, 'active': self.active, 'players': players,
                    'own_hand': [c.key() for c in self.ps[seat].z.hand]}
        super()._log_choice(choice_type, seat, candidates, chosen, position=position, **fields)

    def event(self, typ, **fields):
        if getattr(self, '_terminal_event', False) and typ != 'JUDGE_HALT':
            raise JudgeHalt('EVENT_AFTER_GAME_END: ' + typ)
        super().event(typ, **fields)
        if typ in ('GAME_END', 'WIN_DRAW_PHASE_DECKOUT'):
            self._terminal_event = True

    def hard_play(self, player):
        chosen = self.selected_main_card or _select_main_action(player.z)
        if chosen is None or chosen.card not in ('EX12-062', 'EX12-026', 'BT26-013'):
            return super().hard_play(player)
        # These three legacy On Play paths delegate to a MatchZones helper
        # whose documented contract is a plain, single-card opening board.
        # Reject violations BEFORE calling it, not after losing a stack.
        for owner in self.ps.values():
            for top in owner.digimon():
                stack = owner.stacks.get(top.key(), [top])
                if len(stack) > 1:
                    raise JudgeHalt('PREFIX_HANDLER_STACK_UNSUPPORTED: '
                                    + chosen.card + ' target=' + top.key())
                if owner.z.statuses.get(top.key()):
                    # The prefix helper uses printed DP and Shellmon replaces
                    # the whole status map. Neither is safe in a full-match
                    # state already carrying temporary effects.
                    raise JudgeHalt('PREFIX_HANDLER_STATUS_UNSUPPORTED: '
                                    + chosen.card + ' source=' + top.key())
                main = src(owner.seat, top.card)['card_text'].partition('[Inherited Effect]')[0]
                if 'would leave' in main or '＜Decode' in main:
                    raise JudgeHalt('PREFIX_HANDLER_REPLACEMENT_UNVERIFIED: '
                                    + chosen.card + ' source=' + top.key())
        result = super().hard_play(player)
        # A plain card sacrificed by its own On Play effect is already in
        # trash. FullMatch must not register a ghost stack after that effect.
        for owner in self.ps.values():
            present = {c.key() for c in owner.z.battle}
            for anchor in list(owner.stacks):
                if anchor not in present:
                    stack = owner.stacks[anchor]
                    if len(stack) != 1 or stack[0] not in owner.z.trash:
                        raise JudgeHalt('PREFIX_HANDLER_UNEXPECTED_ZONE_CHANGE: ' + anchor)
                    del owner.stacks[anchor]
                    owner.suspended.discard(anchor)
                    owner.sick.discard(anchor)
                    owner.z.statuses.pop(anchor, None)
        return result

    def verify(self):
        if type(self.mem) is not int or not -10 <= self.mem <= 10:
            raise JudgeHalt(f'MEMORY_GAUGE_INVALID: {self.mem!r}')
        for seat, player in self.ps.items():
            battle = {c.key(): c for c in player.z.battle}
            for anchor, stack in player.stacks.items():
                if not stack or anchor not in battle or stack[-1] != battle[anchor]:
                    raise JudgeHalt(f'STACK_ANCHOR_MISMATCH: {seat} {anchor}')
            physical = []
            for zone in ('deck', 'hand', 'trash', 'security', 'battle'):
                physical.extend(getattr(player.z, zone))
            physical.extend(player.eggdeck)
            physical.extend(player.breeding)
            for stack in player.stacks.values():
                physical.extend(stack[:-1])
            expected = Counter(Copy(card, i)
                               for card, data in BY_SEAT[seat].items()
                               for i in range(1, data['qty'] + 1))
            observed = Counter(physical)
            if expected != observed:
                missing = sorted(c.key() for c in (expected - observed).elements())
                excess = sorted(c.key() for c in (observed - expected).elements())
                raise JudgeHalt(f'PHYSICAL_CARD_MISMATCH: {seat} missing={missing} excess={excess}')


ROOT = Path(__file__).resolve().parent.parent
DECK_NAMES = {'A': 'JUPITERMON.txt', 'B': 'AMATERASUMON_TOHO.txt'}


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _state_value(value):
    if isinstance(value, Copy):
        return value.key()
    if isinstance(value, Player):
        return {'player_ref': value.seat}
    if isinstance(value, random.Random):
        return _state_value(value.getstate())
    if is_dataclass(value):
        return {f.name: _state_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: _state_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_state_value(v) for v in value]
    if isinstance(value, set):
        return sorted(_state_value(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError('Unrecorded match-state type: ' + type(value).__name__)


def snapshot_match(match):
    """Copy every persistent player/runtime field, including pending queues.

    Private zone contents are audit data only and must not feed pilot choices.
    The RNG state and initial snapshot permit deterministic reproduction.
    """
    players = {}
    for seat, player in match.ps.items():
        players[seat] = {k: _state_value(v) for k, v in vars(player).items() if k != 'z'}
        players[seat]['zones'] = _state_value(player.z)
    return {
        'players': players,
        'rng_state': _state_value(match.rng),
        'runtime': {k: _state_value(v) for k, v in vars(match).items()
                    if k not in ('ps', 'rng', 'events', 'checks')},
    }


def validate_locked_inputs(root=ROOT):
    """Validate the supplied physical decks; format restrictions need a judge."""
    report = {'format_restrictions': 'UNVERIFIED'}
    for seat, filename in DECK_NAMES.items():
        locked = (root / 'DECKS' / filename).read_bytes()
        if locked != (root / 'SOURCE' / filename).read_bytes():
            raise ValueError('LOCKED_DECK_COPY_MISMATCH: ' + filename)
        listed = Counter()
        for line in locked.decode('utf-8').splitlines():
            if not line.strip() or line.startswith('//'):
                continue
            m = re.fullmatch(r'(\d+) .+ ([A-Z0-9]+-\d+)', line)
            if not m:
                raise ValueError('INVALID_DECK_LINE: ' + line)
            listed[m[2]] += int(m[1])
        manifest = Counter({c['card_number']: c['qty']
                            for c in MANIFEST['decks'][seat]['card_manifest']})
        if listed != manifest:
            raise ValueError('DECK_MANIFEST_MISMATCH: ' + seat)
        main = sum(c['qty'] for c in MANIFEST['decks'][seat]['card_manifest'] if c['zone'] == 'main')
        eggs = sum(c['qty'] for c in MANIFEST['decks'][seat]['card_manifest'] if c['zone'] == 'eggs')
        if (main, eggs) != (50, 4):
            raise ValueError('INVALID_LOADED_DECK_COUNTS: ' + seat)
        for card, info in BY_SEAT[seat].items():
            actual = hashlib.sha256(info['card_text'].encode('utf-8')).hexdigest()
            if actual != info['card_text_sha256']:
                raise ValueError('CARD_TEXT_HASH_MISMATCH: ' + card)
        report[seat] = {'main': main, 'eggs': eggs, 'deck_sha256': hashlib.sha256(locked).hexdigest()}
    return report


def provenance(root=ROOT):
    paths = sorted(p for p in (root / 'SOURCE').glob('*.py') if not p.name.startswith('test_'))
    paths += sorted((root / 'SOURCE').glob('*.json'))
    paths += [root / folder / filename for folder in ('DECKS', 'SOURCE') for filename in DECK_NAMES.values()]
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    bundle = digest(hashes)
    return {
        'schema': 'loaded-pair-provenance-v1', 'files': hashes,
        'bundle_sha256': bundle, 'locked_decks': validate_locked_inputs(root),
        'pilots': {seat: {'policy_id': EvidenceMatch.SCORER_ID,
                          'sha256': digest({'seat': seat, 'bundle': bundle, 'policy': EvidenceMatch.SCORER_ID})}
                   for seat in ('A', 'B')},
        'rules_status': 'UNVERIFIED',
        'python_version': sys.version.split()[0],
    }


def record_match(index, provenance_sha256):
    match = EvidenceMatch(index)
    initial = snapshot_match(match)
    result = match.run()
    try:
        match.verify()
        integrity = {'status': 'PASS'}
    except JudgeHalt as exc:
        integrity = {'status': 'FAIL', 'reason': str(exc)}
    return {
        'schema': 'loaded-pair-match-evidence-v1',
        'index': index, 'seed': result['seed'], 'first': result['first'],
        'status': 'SOFTWARE_COMPLETED' if result['status'] == 'VALID_COMPLETE_GAME' else 'HALT',
        'rule_check_status': 'UNVERIFIED', 'judge_certified': False,
        'provenance_sha256': provenance_sha256, 'physical_integrity': integrity,
        'initial_state': initial, 'final_state': snapshot_match(match), 'transcript': result,
    }


def run_evidence_cohort(output, count=60):
    """Stream records and verify full seed replays; no certified-game credit."""
    if type(count) is not int or count <= 0 or count % 2:
        raise ValueError('Cohort count must be a positive even integer')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    inputs = provenance()
    inputs_hash = digest(inputs)
    (output / 'provenance.json').write_bytes(canonical_bytes(inputs))
    entries = []
    statuses, starts, halts, unmodeled = Counter(), Counter(), Counter(), Counter()
    for index in range(count):
        record = record_match(index, inputs_hash)
        raw = canonical_bytes(record)
        replay = record_match(index, inputs_hash)
        if raw != canonical_bytes(replay):
            raise RuntimeError('NONDETERMINISTIC_REPLAY: ' + str(index))
        filename = f'MATCH_{index + 1:03d}.json.gz'
        compressed = gzip.compress(raw, mtime=0)
        (output / filename).write_bytes(compressed)
        entries.append({'index': index, 'file': filename, 'seed': record['seed'],
                        'first': record['first'], 'status': record['status'],
                        'record_sha256': hashlib.sha256(raw).hexdigest(),
                        'file_sha256': hashlib.sha256(compressed).hexdigest(),
                        'replay_verified': True})
        statuses[record['status']] += 1
        starts[record['first']] += 1
        reason = record['transcript']['halt_reason']
        if reason:
            halts[reason] += 1
        for event in record['transcript']['events']:
            if event.get('kind') == 'TOP_ATTACK_OPTIONAL_UNMODELED_DECLINED':
                unmodeled[event['card']] += 1
    if provenance() != inputs:
        raise RuntimeError('INPUTS_CHANGED_DURING_COHORT')
    summary = {
        'schema': 'loaded-pair-cohort-evidence-v1', 'attempted': count,
        'software_completed': statuses['SOFTWARE_COMPLETED'], 'halted': statuses['HALT'],
        'judge_certified': 0, 'valid_fact_finding_matches': 0,
        'replays_verified': count, 'starts': dict(starts), 'halts': dict(halts),
        'unmodeled_optional_attacks': dict(unmodeled),
        'provenance_sha256': inputs_hash, 'records': entries,
    }
    (output / 'cohort.json').write_bytes(canonical_bytes(summary))
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--count', type=int, default=60)
    args = parser.parse_args()
    summary = run_evidence_cohort(args.out, args.count)
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}, indent=2))
