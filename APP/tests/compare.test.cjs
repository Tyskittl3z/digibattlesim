'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../compare.js');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'SOURCE/EXACT_CARD_MANIFEST.json')));
const costs = JSON.parse(fs.readFileSync(path.join(root, 'SOURCE/LOADED_EXACT_COSTS.json')));
const catalog = {};
for (const deck of Object.values(manifest.decks)) {
  for (const card of deck.card_manifest) catalog[card.card_number] = {...card, play_cost: costs[card.card_number].play_cost};
}
const rawA = fs.readFileSync(path.join(root, 'DECKS/JUPITERMON.txt'), 'utf8');
const rawB = fs.readFileSync(path.join(root, 'DECKS/AMATERASUMON_TOHO.txt'), 'utf8');
const metadata = {version: 'test', catalog, source_files: {}, samples: {
  A: {name: 'Jupitermon', text: rawA}, B: {name: 'Amaterasumon / Toho', text: rawB}
}};

test.beforeEach(() => assert.equal(typeof core.parseDeck, 'function', 'deck parser must exist'));

test('both supplied decks retain 50 main + 4 eggs and distinct card counts', () => {
  const a = core.summarize(core.parseDeck(rawA, catalog), catalog);
  const b = core.summarize(core.parseDeck(rawB, catalog), catalog);
  assert.equal(a.total, 54); assert.equal(a.main_count, 50); assert.equal(a.egg_count, 4); assert.equal(a.distinct, 20);
  assert.equal(b.total, 54); assert.equal(b.main_count, 50); assert.equal(b.egg_count, 4); assert.equal(b.distinct, 21);
});

test('common quantity/code formats aggregate duplicate physical counts', () => {
  const deck = core.parseDeck('\uFEFF// Example\r\n4 BT24-031\r\nBT24-031 x2\n2x Aegiomon BT24-034\n1 Dianamon (BT25-028)', catalog);
  assert.deepEqual(deck.errors, []);
  assert.equal(deck.entries.find(c => c.id === 'BT24-031').count, 6);
  assert.equal(core.summarize(deck, catalog).total, 9);
});

test('malformed and ambiguous rows are explicit errors, never silently compared', () => {
  for (const raw of ['0 Elecmon BT24-031', '-2 BT24-031', '4 BT24-031 BT24-034', '4 BT24-031 x2', '4 BT24-031-999', 'Elecmon maybe four', '']) {
    const a = core.parseDeck(raw, catalog);
    assert.ok(a.errors.length > 0, raw);
    assert.throws(() => core.compare(a, core.parseDeck(rawB, catalog), catalog));
  }
});

test('unknown cards preserve quantities without guessed metadata or main-deck size', () => {
  const deck = core.parseDeck('4 Agumon BT1-010\n4 Koromon BT1-001', catalog);
  const summary = core.summarize(deck, catalog);
  assert.equal(summary.total, 8);
  assert.equal(summary.unknown_count, 8);
  assert.equal(summary.main_count, null);
  assert.equal(summary.egg_count, null);
  assert.equal(summary.average_play_cost, null);
});

test('shared copies and deltas use quantities, and stay numerical', () => {
  const a = core.parseDeck('4 Elecmon BT24-031\n2 Aegiomon BT24-034', catalog);
  const b = core.parseDeck('3 Elecmon BT24-031\n4 Dianamon BT25-028', catalog);
  const comparison = core.compare(a, b, catalog);
  assert.equal(comparison.shared_copies, 3);
  assert.equal(comparison.shared_distinct, 1);
  assert.equal(comparison.rows.find(c => c.id === 'BT24-031').delta, -1);
  assert.equal(comparison.rows.find(c => c.id === 'BT25-028').delta, 4);
  assert.equal(comparison.rows.find(c => c.id === 'BT24-034').delta, -2);
});

test('after-report preserves exact input texts, hashes, full data and unavailable simulation', async () => {
  const report = await core.buildReport({text: rawA, filename: 'A.txt'}, {text: rawB, filename: 'B.txt'}, metadata);
  assert.equal(report.inputs.A.raw_text, rawA);
  assert.equal(report.inputs.B.filename, 'B.txt');
  assert.match(report.inputs.A.raw_sha256, /^[0-9a-f]{64}$/);
  assert.equal(report.statistics.comparison.rows.length, 41);
  assert.equal(report.simulation.supported_pairing, true);
  assert.equal(report.simulation.matches_played, 0);
  assert.equal(report.simulation.win_rate, null);
  assert.equal(report.simulation.wins, null);
  assert.deepEqual(report.simulation.logs, []);
  assert.equal(report.simulation.historical_results_reused, false);
  assert.deepEqual(report.simulation.judges.map(judge => judge.name), ['Justitia', 'Dike', 'Týr']);
  assert.deepEqual(report.simulation.judges.map(judge => judge.role),
    ['Runtime integrity', 'Independent rules', 'Final evidence audit']);
  assert.deepEqual(report.simulation.bots, [
    {name: 'Bot A', seat: 'A', deck: 'Jupitermon'},
    {name: 'Bot B', seat: 'B', deck: 'Amaterasumon / Toho'}
  ]);
});

test('changed matchup never inherits old pilots/results or simulation support', async () => {
  const report = await core.buildReport({text: '4 Agumon BT1-010', filename: 'new.txt'}, {text: rawB, filename: 'B.txt'}, metadata);
  assert.equal(report.simulation.supported_pairing, false);
  assert.equal(report.simulation.status, 'UNSUPPORTED_PAIRING');
  assert.equal(report.simulation.matches_played, 0);
  assert.equal(report.simulation.win_rate, null);
  assert.equal(report.statistics.A.unknown_count, 4);
});

test('invalid imports remain inspectable in after-report without partial results', async () => {
  const report = await core.buildReport({text: 'bad row', filename: 'broken.txt'}, {text: rawB}, metadata);
  assert.equal(report.inputs.A.raw_text, 'bad row');
  assert.ok(report.inputs.A.errors.length);
  assert.equal(report.statistics, null);
  assert.equal(report.simulation.status, 'INPUT_ERRORS');
});

test('readable report escapes uploaded markup and embeds the complete original evidence', async () => {
  assert.equal(typeof core.reportHtml, 'function');
  const raw = '4 <img src=x onerror=alert(1)> BT1-010';
  const report = await core.buildReport({text: raw, filename: '<script>bad</script>.txt'}, {text: rawB}, metadata);
  const html = core.reportHtml(report);
  assert.ok(html.includes('&lt;img'));
  assert.ok(!html.includes('<img src=x'));
  const embedded = html.match(/<script type="application\/json" id="report-data">([\s\S]*?)<\/script>/);
  assert.ok(embedded);
  assert.equal(JSON.parse(embedded[1]).inputs.A.raw_text, raw);
  assert.equal(JSON.parse(embedded[1]).inputs.A.filename, '<script>bad</script>.txt');
  assert.match(html, /Justitia/);
  assert.match(html, /Dike/);
  assert.match(html, /Týr/);
});
