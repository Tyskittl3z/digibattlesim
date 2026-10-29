(function (root) {
  'use strict';
  const LIMIT = 1000000;
  const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

  function parseDeck(raw, catalog = {}) {
    const errors = [], grouped = new Map();
    if (typeof raw !== 'string' || raw.length > LIMIT) {
      return {raw: typeof raw === 'string' ? raw : '', entries: [], errors: [{line: 0, message: 'Use a text decklist smaller than 1 MB.'}]};
    }
    raw.replace(/^\uFEFF/, '').split(/\r?\n/).forEach((source, offset) => {
      const line = source.trim();
      if (!line || /^(\/\/|#|;)/.test(line)) return;
      if (/^\[?(main(?: deck)?|deck|digi[- ]?eggs?(?: deck)?)\]?:?$/i.test(line)) return;
      let count, body, leading = false;
      let match = line.match(/^(\d+)\s*[x×]?\s+(.+)$/i);
      if (match) { count = Number(match[1]); body = match[2]; leading = true; }
      else {
        match = line.match(/^(.+?)\s+[x×]\s*(\d+)$/i) || line.match(/^([A-Z][A-Z0-9]*-\d{2,3})\s+(\d+)$/i);
        if (match) { count = Number(match[2]); body = match[1]; }
      }
      const ids = body ? [...body.matchAll(/(?<![A-Z0-9_-])([A-Z][A-Z0-9]*-\d{2,3})(?![A-Z0-9_-])/gi)] : [];
      const tail = ids.length === 1 ? body.slice(ids[0].index + ids[0][0].length).trim() : '';
      const extraQuantity = leading && (/^[\])}]*\s*(?:[x×]\s*)?\d+\s*$/i.test(tail) || /^[x×]\s*\d+\b/i.test(body));
      if (!Number.isSafeInteger(count) || count < 1 || count > 999 || ids.length !== 1 || extraQuantity) {
        errors.push({line: offset + 1, text: source, message: 'Expected one quantity and one card code, e.g. 4 Elecmon BT24-031.'});
        return;
      }
      const id = ids[0][1].toUpperCase();
      const suppliedName = body.replace(ids[0][0], '').replace(/\(\s*\)|\[\s*\]/g, '').trim();
      const entry = grouped.get(id) || {id, count: 0, supplied_name: suppliedName || id, lines: []};
      entry.count += count;
      entry.lines.push(offset + 1);
      grouped.set(id, entry);
    });
    const entries = [...grouped.values()].sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true}));
    if (!entries.length && !errors.length) errors.push({line: 0, message: 'No card entries found.'});
    return {raw, entries, errors};
  }

  function summarize(deck, catalog = {}) {
    const value = {total: 0, distinct: deck.entries.length, known_main_count: 0, known_egg_count: 0,
      unknown_count: 0, unknown_ids: [], types: {}, colors: {}, levels: {}, cost_known_count: 0, average_play_cost: null};
    let cost = 0;
    for (const card of deck.entries) {
      value.total += card.count;
      if (!own(catalog, card.id)) { value.unknown_count += card.count; value.unknown_ids.push(card.id); continue; }
      const info = catalog[card.id];
      if (info.type === 'Digi-Egg') { value.known_egg_count += card.count; continue; }
      value.known_main_count += card.count;
      value.types[info.type] = (value.types[info.type] || 0) + card.count;
      for (const color of info.colors || []) value.colors[color] = (value.colors[color] || 0) + card.count;
      if (Number.isInteger(info.level)) value.levels[info.level] = (value.levels[info.level] || 0) + card.count;
      if (Number.isInteger(info.play_cost)) { cost += info.play_cost * card.count; value.cost_known_count += card.count; }
    }
    value.main_count = value.unknown_count ? null : value.known_main_count;
    value.egg_count = value.unknown_count ? null : value.known_egg_count;
    if (value.cost_known_count) value.average_play_cost = Math.round(cost / value.cost_known_count * 100) / 100;
    return value;
  }

  function compare(a, b, catalog = {}) {
    if (a.errors.length || b.errors.length) throw new Error('Fix invalid decklist rows before comparing.');
    const left = new Map(a.entries.map(c => [c.id, c]));
    const right = new Map(b.entries.map(c => [c.id, c]));
    let shared = 0, sharedDistinct = 0;
    const rows = [...new Set([...left.keys(), ...right.keys()])].sort((x, y) => x.localeCompare(y, undefined, {numeric: true})).map(id => {
      const x = left.get(id), y = right.get(id), ac = x ? x.count : 0, bc = y ? y.count : 0;
      if (ac && bc) { shared += Math.min(ac, bc); sharedDistinct++; }
      const info = own(catalog, id) ? catalog[id] : null;
      return {id, name: info ? info.name : (x || y).supplied_name, A: ac, B: bc, delta: bc - ac,
        data_available: Boolean(info), type: info ? info.type : null,
        level: info ? info.level : null, colors: info ? info.colors : [],
        play_cost: info ? info.play_cost : null};
    });
    return {shared_copies: shared, shared_distinct: sharedDistinct, rows};
  }

  function composition(deck) { return deck.entries.map(c => [c.id, c.count]).sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0); }

  function simulationStatus(a, b, metadata) {
    const base = {matches_played: 0, wins: null, losses: null, win_rate: null, first_player_split: null,
      seeds: [], logs: [], historical_results_reused: false, supported_pairing: false};
    if (a.errors.length || b.errors.length) return {...base, status: 'INPUT_ERRORS', message: 'Fix the decklist rows before checking simulation support.'};
    const key = d => JSON.stringify(composition(d));
    const samples = metadata.samples;
    const sa = key(parseDeck(samples.A.text, metadata.catalog)), sb = key(parseDeck(samples.B.text, metadata.catalog));
    const samePair = (key(a) === sa && key(b) === sb) || (key(a) === sb && key(b) === sa);
    return {...base, supported_pairing: samePair,
      status: samePair ? 'RULES_UNVERIFIED' : 'UNSUPPORTED_PAIRING',
      message: samePair ? 'This pairing still has unresolved gameplay interactions. Verified win rates are not available yet.'
        : 'Gameplay support has not been verified for this pairing. You can compare its deck contents and available card statistics.',
      blockers: samePair ? ['Unresolved gameplay interactions', 'Rules and format verification incomplete', 'Strategy review and frozen runner pending']
        : ['This pairing needs its own verified card mechanics, pilots and match evidence']};
  }

  async function hash(text) {
    if (!root.crypto || !root.crypto.subtle) return null;
    const bytes = await root.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(bytes)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function buildReport(inputA, inputB, metadata) {
    const a = parseDeck(inputA.text, metadata.catalog), b = parseDeck(inputB.text, metadata.catalog);
    const inputs = {};
    for (const [seat, input, deck] of [['A', inputA, a], ['B', inputB, b]]) {
      inputs[seat] = {filename: input.filename || 'Pasted deck ' + seat, raw_text: input.text,
        raw_sha256: await hash(input.text), composition_sha256: await hash(JSON.stringify(composition(deck))),
        original_file_sha256: input.file_sha256 || null, input_kind: input.kind || 'PASTE',
        text_encoding: input.encoding || null,
        entries: deck.entries, errors: deck.errors};
    }
    return {schema: 'digimon-deck-comparison-report-v1', app_version: metadata.version,
      created_at_utc: new Date().toISOString(), inputs,
      statistics: a.errors.length || b.errors.length ? null : {A: summarize(a, metadata.catalog), B: summarize(b, metadata.catalog), comparison: compare(a, b, metadata.catalog)},
      simulation: simulationStatus(a, b, metadata),
      data_provenance: {source_files: metadata.source_files, official_rule_verification: 'UNVERIFIED', known_card_ids: Object.keys(metadata.catalog)},
      limitations: ['Statistics use the supplied card metadata; unknown cards stay unclassified.',
        'Printed play-cost averages cover known main cards only; multicolor cards count in each color.',
        'No head-to-head matches were played for this comparison. No previous matchup results or pilots were reused.',
        'Card composition and statistics do not certify format legality or predict a match winner.',
        'Null simulation results are unavailable, not zero wins or a zero-percent win rate.'],
      hash_status: inputs.A.raw_sha256 && inputs.B.raw_sha256 ? 'SHA256_RECORDED' : 'SHA256_UNAVAILABLE_IN_THIS_BROWSER'};
  }

  function reportHtml(report) {
    const esc = value => String(value == null ? 'Unavailable' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const statistics = report.statistics;
    const statRows = statistics ? ['total', 'main_count', 'egg_count', 'distinct', 'unknown_count', 'average_play_cost'].map(key =>
      `<tr><th>${esc(key.replaceAll('_',' '))}</th><td>${esc(statistics.A[key])}</td><td>${esc(statistics.B[key])}</td></tr>`).join('') : '';
    const rows = statistics ? statistics.comparison.rows.map(row => `<tr><td>${esc(row.id)}</td><td>${esc(row.name)}</td><td>${row.A}</td><td>${row.B}</td><td>${row.delta}</td></tr>`).join('') : '';
    const inputs = ['A','B'].map(seat => {
      const input = report.inputs[seat];
      return `<section><h2>Deck ${seat}: ${esc(input.filename)}</h2><p>Input kind: ${esc(input.input_kind)}. Uploaded-file SHA-256: <code>${esc(input.original_file_sha256)}</code></p><p>Preserved-text SHA-256: <code>${esc(input.raw_sha256)}</code></p><p>Composition SHA-256: <code>${esc(input.composition_sha256)}</code></p>${input.errors.map(e => `<p>Line ${e.line}: ${esc(e.message)}</p>`).join('')}<pre>${esc(input.raw_text)}</pre></section>`;
    }).join('');
    const json = JSON.stringify(report, null, 2);
    return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Digimon deck comparison after-report</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#182832;max-width:1050px;margin:40px auto;padding:0 24px}h1,h2{line-height:1.2}section{margin:30px 0}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{text-align:left;padding:9px;border-bottom:1px solid #dce3e3}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f5;padding:18px;border-radius:8px}code{overflow-wrap:anywhere}.notice{padding:18px;border-left:4px solid #d99a33;background:#fff5e4}small{color:#52646b}@media print{details{display:block}body{margin:0}}</style><h1>Deck comparison after-report</h1><small>Created ${esc(report.created_at_utc)} · App ${esc(report.app_version)}</small><p class="notice"><strong>Head-to-head: no verified result.</strong> ${esc(report.simulation.message)} Matches played: 0. Win rate: unavailable.</p>${statistics ? `<h2>Numerical comparison</h2><table><tr><th>Metric</th><th>Deck A</th><th>Deck B</th></tr>${statRows}</table><p>Shared copies: ${statistics.comparison.shared_copies}. Shared distinct cards: ${statistics.comparison.shared_distinct}.</p><h2>Full card comparison</h2><table><tr><th>Code</th><th>Card</th><th>A</th><th>B</th><th>B − A</th></tr>${rows}</table>` : '<p>Import errors prevented calculation of comparison statistics.</p>'}${inputs}<h2>Data limits</h2><ul>${report.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><details><summary>Complete machine-readable evidence, provenance and unavailable fields</summary><pre>${esc(json)}</pre></details><script type="application/json" id="report-data">${json.replace(/</g,'\\u003c')}</script></html>`;
  }

  const api = {parseDeck, summarize, compare, composition, simulationStatus, buildReport, reportHtml};
  root.DeckCompare = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
