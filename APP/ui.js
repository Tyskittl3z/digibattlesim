(function () {
  'use strict';
  const metadata = JSON.parse(document.getElementById('app-data').textContent);
  const core = window.DeckCompare, $ = id => document.getElementById(id);
  const names = {A: '', B: ''}, versions = {A: 0, B: 0};
  const fileMeta = {A: null, B: null}, kinds = {A: 'PASTE', B: 'PASTE'};
  let current = null, toastTimer;
  const make = (tag, text, cls) => { const node = document.createElement(tag); if (text != null) node.textContent = text; if (cls) node.className = cls; return node; };
  // Textareas normalize CRLF. Keep the original UTF-8 text separately until
  // the user edits it, so exported evidence preserves Windows files exactly.
  const input = seat => ({text: fileMeta[seat] ? fileMeta[seat].raw : $('text' + seat).value, filename: names[seat] || 'Pasted deck ' + seat,
    file_sha256: fileMeta[seat] ? fileMeta[seat].sha256 : null,
    encoding: fileMeta[seat] ? fileMeta[seat].encoding : null, kind: kinds[seat]});
  const announce = message => { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4500); };

  function refresh() {
    const a = core.parseDeck($('textA').value, metadata.catalog), b = core.parseDeck($('textB').value, metadata.catalog);
    for (const [seat, deck] of [['A', a], ['B', b]]) {
      const feedback = $('feedback' + seat); feedback.replaceChildren(); feedback.className = 'deck-feedback';
      $('meta' + seat).textContent = names[seat] || (deck.raw.trim() ? 'Pasted decklist' : 'No file loaded');
      if (!deck.raw.trim()) continue;
      if (deck.errors.length) {
        feedback.classList.add('error'); feedback.append(make('strong', deck.errors.length + ' row' + (deck.errors.length === 1 ? '' : 's') + ' to fix'));
        const list = make('ul'); deck.errors.slice(0, 3).forEach(e => list.append(make('li', (e.line ? 'Line ' + e.line + ': ' : '') + e.message))); feedback.append(list);
      } else {
        const stats = core.summarize(deck, metadata.catalog);
        feedback.textContent = stats.total + ' cards · ' + stats.distinct + ' distinct' + (stats.unknown_count ? ' · ' + stats.unknown_count + ' without card data' : ' · ' + stats.main_count + ' main + ' + stats.egg_count + ' eggs');
        if (stats.unknown_count || stats.main_count !== 50) feedback.classList.add('warning');
      }
    }
    $('save-report').disabled = !a.raw.trim() || !b.raw.trim();
    const ready = !a.errors.length && !b.errors.length;
    $('empty-state').hidden = ready; $('stats-content').hidden = !ready;
    const simulation = core.simulationStatus(a, b, metadata);
    $('simulation-message').textContent = !a.raw.trim() || !b.raw.trim() ? 'Add both decklists to check this pairing.' : simulation.message;
    $('simulation-blockers').replaceChildren(); (simulation.blockers || []).forEach(reason => $('simulation-blockers').append(make('li', reason)));
    if (!ready) {
      current = null;
      $('comparison-status').textContent = a.raw.trim() && b.raw.trim() ? 'Fix the highlighted rows. Your exact inputs can still be saved.' : 'Add two decklists to start comparing.';
      return;
    }
    const sa = core.summarize(a, metadata.catalog), sb = core.summarize(b, metadata.catalog);
    current = core.compare(a, b, metadata.catalog);
    $('comparison-status').textContent = 'Comparison updates automatically · ' + current.shared_copies + ' shared copies';
    $('stat-grid').replaceChildren();
    const stat = (title, av, bv, note) => {
      const box = make('div', null, 'stat'); box.append(make('span', title, 'stat-label'));
      const values = make('div', null, 'stat-values'); values.append(make('span', av == null ? '—' : av, 'a-text'), make('span', '/', 'sep'), make('span', bv == null ? '—' : bv, 'b-text'));
      box.append(values, make('small', note)); $('stat-grid').append(box);
    };
    stat('Cards imported', sa.total, sb.total, 'Deck A / Deck B · includes eggs');
    stat('Main-deck cards', sa.main_count, sb.main_count, 'Eggs: ' + (sa.egg_count == null ? '?' : sa.egg_count) + ' / ' + (sb.egg_count == null ? '?' : sb.egg_count));
    stat('Distinct cards', sa.distinct, sb.distinct, current.shared_distinct + ' distinct cards in common');
    stat('Average printed play cost', sa.average_play_cost, sb.average_play_cost, 'Known main cards only');
    const missing = [...new Set([...sa.unknown_ids, ...sb.unknown_ids])];
    $('data-note').className = 'data-note' + (missing.length ? ' warn' : '');
    $('data-note').textContent = missing.length ? 'Missing card details for ' + missing.length + ' code' + (missing.length === 1 ? '' : 's') + ': ' + missing.slice(0, 8).join(', ') + (missing.length > 8 ? '…' : '') + '. Quantities and differences are retained; unknown cards are excluded from composition breakdowns. Main/egg totals remain unclassified.'
      : 'All imported card codes have bundled data. These statistics do not certify format legality or predict a winner.';
    renderBars($('type-bars'), sa.types, sb.types, Math.max(sa.known_main_count, sb.known_main_count), false);
    renderBars($('level-bars'), sa.levels, sb.levels, Math.max(sa.known_main_count, sb.known_main_count), true);
    renderRows();
  }

  function renderBars(container, a, b, max, levels) {
    container.replaceChildren();
    const keys = [...new Set([...Object.keys(a), ...Object.keys(b)])].sort((x, y) => x.localeCompare(y, undefined, {numeric: true}));
    if (!keys.length) { container.append(make('p', 'Card details are needed for this breakdown.', 'small-note')); return; }
    for (const key of keys) {
      const row = make('div', null, 'bar-row'); row.append(make('span', levels ? 'Level ' + key : key));
      const track = make('div', null, 'bar-track');
      for (const [count, cls] of [[a[key] || 0, 'bar'], [b[key] || 0, 'bar b']]) { const bar = make('div', null, cls); bar.style.width = (max ? count / max * 100 : 0) + '%'; track.append(bar); }
      const values = make('div', null, 'bar-numbers'); values.append(make('span', a[key] || 0, 'a-text'), make('span', b[key] || 0, 'b-text')); row.append(track, values); container.append(row);
    }
  }

  function renderRows() {
    $('card-rows').replaceChildren();
    if (!current) return;
    const query = $('search').value.toLowerCase().trim();
    const rows = current.rows.filter(row => (!query || (row.name + ' ' + row.id).toLowerCase().includes(query)) && (!$('differences-only').checked || row.delta !== 0));
    for (const row of rows) {
      const tr = make('tr'), card = make('td'); card.append(make('strong', row.name), make('small', row.id)); tr.append(card);
      tr.append(make('td', row.type || 'Data missing', row.type ? '' : 'missing'), make('td', row.A, 'a-text'), make('td', row.B, 'b-text'), make('td', row.delta > 0 ? '+' + row.delta : row.delta)); $('card-rows').append(tr);
    }
    $('row-count').textContent = rows.length + ' of ' + current.rows.length + ' cards shown. The after-report always includes the full comparison.';
  }

  async function loadFile(seat, file) {
    const version = ++versions[seat];
    if (file.size > 1000000) { announce('Please use a plain-text decklist smaller than 1 MB.'); return; }
    try {
      const bytes = await file.arrayBuffer();
      const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
      let originalHash = null;
      if (window.crypto && window.crypto.subtle) {
        const hash = await window.crypto.subtle.digest('SHA-256', bytes);
        originalHash = [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
      }
      if (version !== versions[seat]) return;
      fileMeta[seat] = {sha256: originalHash, encoding: 'UTF-8', raw: text}; kinds[seat] = 'FILE';
      names[seat] = file.name; $('text' + seat).value = text; refresh();
    } catch (_) { announce('That file could not be read as UTF-8 text. Try pasting its decklist instead.'); }
  }

  function handleFiles(files, seat) {
    if (files.length === 2) { loadFile('A', files[0]); loadFile('B', files[1]); }
    else if (files.length === 1 && seat) loadFile(seat, files[0]);
    else announce('Drop one file into a deck panel, or drop exactly two files to fill both.');
  }

  for (const seat of ['A', 'B']) {
    $('text' + seat).addEventListener('input', () => { ++versions[seat]; names[seat] = ''; fileMeta[seat] = null; kinds[seat] = 'PASTE'; refresh(); });
    $('file' + seat).addEventListener('change', event => { handleFiles([...event.target.files], seat); event.target.value = ''; });
    const zone = document.querySelector('.drop-target[data-seat=' + seat + ']');
    zone.addEventListener('click', event => { if (event.target !== $('file' + seat)) $('file' + seat).click(); });
    zone.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); $('file' + seat).click(); } });
    zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragging'); });
    zone.addEventListener('dragleave', event => { if (!zone.contains(event.relatedTarget)) zone.classList.remove('dragging'); });
    zone.addEventListener('drop', event => { event.preventDefault(); event.stopPropagation(); zone.classList.remove('dragging'); handleFiles([...event.dataTransfer.files], seat); });
  }
  document.addEventListener('dragover', event => event.preventDefault());
  document.addEventListener('drop', event => { event.preventDefault(); handleFiles([...event.dataTransfer.files]); });
  document.querySelectorAll('.clear').forEach(button => button.addEventListener('click', () => { const seat = button.dataset.seat; ++versions[seat]; $('text' + seat).value = ''; names[seat] = ''; fileMeta[seat] = null; kinds[seat] = 'PASTE'; refresh(); }));
  $('examples').addEventListener('click', () => { for (const seat of ['A', 'B']) { ++versions[seat]; $('text' + seat).value = metadata.samples[seat].text; names[seat] = metadata.samples[seat].name + '.txt'; fileMeta[seat] = null; kinds[seat] = 'EXAMPLE'; } refresh(); });
  $('swap').addEventListener('click', () => {
    ++versions.A; ++versions.B;
    const a = input('A'), b = input('B'); $('textA').value = b.text; $('textB').value = a.text;
    [names.A, names.B] = [names.B, names.A]; [fileMeta.A, fileMeta.B] = [fileMeta.B, fileMeta.A]; [kinds.A, kinds.B] = [kinds.B, kinds.A]; refresh();
  });
  $('search').addEventListener('input', renderRows); $('differences-only').addEventListener('change', renderRows);
  const tabs = [$('tab-stats'), $('tab-simulation')];
  function selectTab(index) { tabs.forEach((tab, n) => { tab.classList.toggle('active', n === index); tab.setAttribute('aria-selected', n === index ? 'true' : 'false'); tab.tabIndex = n === index ? 0 : -1; }); $('stats-panel').hidden = index !== 0; $('simulation-panel').hidden = index !== 1; }
  tabs.forEach((tab, index) => { tab.addEventListener('click', () => selectTab(index)); tab.addEventListener('keydown', event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : 1 - index; selectTab(next); tabs[next].focus(); } }); });
  $('save-report').addEventListener('click', async () => {
    const a = input('A'), b = input('B'); $('save-report').disabled = true;
    try {
      const report = await core.buildReport(a, b, metadata);
      const blob = new Blob([core.reportHtml(report)], {type: 'text/html;charset=utf-8'});
      const url = URL.createObjectURL(blob), link = make('a'); link.href = url; link.download = 'Digimon-after-report-' + report.created_at_utc.slice(0, 19).replaceAll(':', '-') + '.html';
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
      announce('After-report saved: exact lists, hashes, full statistics and simulation status.');
    } catch (error) { announce('Report could not be saved: ' + error.message); }
    finally { $('save-report').disabled = !$('textA').value.trim() || !$('textB').value.trim(); }
  });
  refresh();
})();
