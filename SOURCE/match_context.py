"""Immutable, exact imported-matchup inputs. No legacy deck or pilot globals.

These definitions validate physical input structure, not tournament legality or
rules certification. Missing effect text must never silently become no effect.
"""
from dataclasses import dataclass
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def card_number(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9]*-\d+', value) is not None


@dataclass(frozen=True)
class CardDefinition:
    """Canonical JSON bytes keep arbitrary printed metadata deeply immutable."""
    _data: bytes

    @classmethod
    def from_dict(cls, data):
        require(isinstance(data, dict), 'Card definition must be an object')
        require(card_number(data.get('card_number')), 'Invalid card number')
        require(nonempty(data.get('name')), 'Card name required')
        require(data.get('type') in ('Digimon', 'Tamer', 'Option', 'Digi-Egg', 'Digimon/Tamer'),
                'Explicit supported card type required')
        for key in ('main_text', 'inherited_text', 'security_text'):
            require(isinstance(data.get(key), str), 'Explicit ' + key + ' required')
        for key in ('level', 'play_cost', 'dp'):
            value = data.get(key)
            require(value is None or type(value) is int and value >= 0, 'Invalid printed ' + key)
        colors = data.get('colors')
        require(isinstance(colors, list) and bool(colors) and len(colors) == len(set(colors))
                and all(c in ('Red', 'Blue', 'Yellow', 'Green', 'Black', 'Purple', 'White') for c in colors),
                'Explicit distinct printed colors required')
        return cls(canonical(data))

    def to_dict(self):
        return json.loads(self._data)

    @property
    def number(self):
        return self.to_dict()['card_number']

    @property
    def name(self):
        return self.to_dict()['name']

    @property
    def kind(self):
        return self.to_dict()['type']

    @property
    def definition_sha256(self):
        return hashlib.sha256(self._data).hexdigest()

    def effect_text(self, field):
        require(field in ('main_text', 'inherited_text', 'security_text'), 'Unknown effect field')
        return self.to_dict()[field]


@dataclass(frozen=True)
class DeckDefinition:
    label: str
    source_id: str
    main: tuple[tuple[str, int], ...]
    eggs: tuple[tuple[str, int], ...]

    @classmethod
    def from_dict(cls, data):
        require(isinstance(data, dict), 'Deck must be an object')
        require(nonempty(data.get('label')) and nonempty(data.get('source_id')),
                'Deck label/source identity required')
        zones = {}
        seen = set()
        for zone in ('main', 'eggs'):
            require(isinstance(data.get(zone), list), 'Explicit ' + zone + ' required')
            entries = []
            for entry in data[zone]:
                require(isinstance(entry, dict) and card_number(entry.get('card_number')),
                        'Invalid deck card number')
                number, qty = entry['card_number'], entry.get('quantity')
                require(type(qty) is int and qty > 0, 'Positive integer quantity required')
                require(number not in seen, 'Duplicate deck card: ' + number)
                seen.add(number)
                entries.append((number, qty))
            zones[zone] = tuple(sorted(entries))
        require(sum(q for _, q in zones['main']) == 50, 'Exactly 50 main cards required')
        require(sum(q for _, q in zones['eggs']) <= 5, 'At most 5 Digi-Eggs required')
        return cls(data['label'], data['source_id'], zones['main'], zones['eggs'])

    def to_dict(self):
        return {'label': self.label, 'source_id': self.source_id,
                **{zone: [{'card_number': n, 'quantity': q} for n, q in getattr(self, zone)]
                   for zone in ('main', 'eggs')}}

    @property
    def composition_sha256(self):
        return digest({'main': self.main, 'eggs': self.eggs})

    def inventory(self):
        return tuple((n, i) for n, q in self.main + self.eggs for i in range(1, q + 1))


@dataclass(frozen=True)
class MatchContext:
    deck_a: DeckDefinition
    deck_b: DeckDefinition
    cards: tuple[CardDefinition, ...]
    _rules: bytes

    @classmethod
    def create(cls, deck_a, deck_b, cards, rules):
        require(isinstance(deck_a, DeckDefinition) and isinstance(deck_b, DeckDefinition),
                'Validated deck definitions required')
        # Defensively reconstruct public dataclasses; direct construction cannot
        # smuggle malformed quantities or mutable containers past validation.
        deck_a = DeckDefinition.from_dict(deck_a.to_dict())
        deck_b = DeckDefinition.from_dict(deck_b.to_dict())
        require(isinstance(cards, dict), 'Card definitions must be keyed by card number')
        definitions = {}
        required = {n for deck in (deck_a, deck_b) for n, _ in deck.main + deck.eggs}
        for number in sorted(required):
            require(number in cards, 'Missing card definition: ' + number)
            card = cards[number]
            require(isinstance(card, CardDefinition), 'Validated card definition required')
            card = CardDefinition.from_dict(card.to_dict())
            require(card.number == number, 'Card definition key mismatch')
            definitions[number] = card
        for deck in (deck_a, deck_b):
            for number, _ in deck.main:
                require(definitions[number].kind != 'Digi-Egg', 'Digi-Egg in main zone')
            for number, _ in deck.eggs:
                require(definitions[number].kind == 'Digi-Egg', 'Non-Digi-Egg in egg zone')
        require(isinstance(rules, dict), 'Explicit rules/format selection required')
        for key in ('name', 'region', 'language', 'as_of_date'):
            require(key in rules and (rules[key] is None or nonempty(rules[key])),
                    'Rules field must be explicit: ' + key)
        return cls(deck_a, deck_b, tuple(definitions.values()), canonical(rules))

    def deck(self, seat):
        require(seat in ('A', 'B'), 'Unknown seat')
        return self.deck_a if seat == 'A' else self.deck_b

    def inventory(self, seat):
        return self.deck(seat).inventory()

    def card(self, seat, number):
        require(number in {n for n, _ in self.deck(seat).main + self.deck(seat).eggs},
                'Card not in seated deck: ' + number)
        return next(c for c in self.cards if c.number == number)

    def to_dict(self):
        return {'schema': 'imported-matchup-context-v1',
                'decks': {'A': self.deck_a.to_dict(), 'B': self.deck_b.to_dict()},
                'cards': {c.number: c.to_dict() for c in self.cards},
                'rules': json.loads(self._rules)}

    @property
    def matchup_id(self):
        # Labels and source IDs aid traceability but do not change the physical
        # matchup. Seats, card metadata and exact rules selections do.
        return digest({'decks': {'A': self.deck_a.composition_sha256,
                                 'B': self.deck_b.composition_sha256},
                       'cards': {c.number: c.definition_sha256 for c in self.cards},
                       'rules': json.loads(self._rules)})
