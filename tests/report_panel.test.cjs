const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function panel() {
  function element() {
    return {children: [], style: {}, textContent: '', hidden: false,
      append(child) { this.children.push(child); },
      replaceChildren(...children) { this.children = children; }};
  }
  const elements = new Map();
  const document = {
    hidden: true,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element,
  };
  const context = vm.createContext({document, setInterval() {},
    fetch: () => new Promise(() => {}), URL});
  const html = fs.readFileSync(path.join(__dirname, '../src/report_panel.html'), 'utf8');
  vm.runInContext(html.split('<script>')[1].split('</script>')[0], context);
  return {elements, render(report) {
    context.state = {report, report_matches_snapshot: true, pipeline: {status: 'idle'}};
    vm.runInContext('render(state)', context);
  }};
}

function forecast(extra = {}) {
  return {weekly_forecast_available: true, display_mode: 'valid',
    categories: {}, recommendations: [{add_name: 'Example A', drop_name: 'Example B', delta_objective_value: 0.24}],
    ...extra};
}

function rows(ui) {
  return ui.elements.get('moves').children.map(row => row.children.map(cell => cell.textContent));
}

test('valid current forecast shows canonical add/drop choices and gain', () => {
  const ui = panel(); ui.render(forecast());
  assert.equal(ui.elements.get('movesCard').hidden, false);
  assert.deepEqual(rows(ui), [['Example A', 'Example B', '0.24']]);
});

test('blocked forecast explains unavailability and clears prior actionable moves', () => {
  const ui = panel(); ui.render(forecast());
  ui.render(forecast({weekly_forecast_available: false, display_mode: 'blocked'}));
  assert.equal(ui.elements.get('movesCard').hidden, false);
  assert.equal(rows(ui).length, 1);
  assert.match(rows(ui)[0][0], /tahmin durdurulduğu için/);
  assert.doesNotMatch(rows(ui)[0][0], /Example A/);
});

test('archived forecast cannot resurrect old actionable choices', () => {
  const ui = panel(); ui.render(forecast({display_mode: 'last_valid_forecast'}));
  assert.equal(ui.elements.get('movesCard').hidden, false);
  assert.match(rows(ui)[0][0], /Eski raporun hamleleri/);
  assert.doesNotMatch(rows(ui)[0][0], /Example A/);
});

test('valid forecast without choices distinguishes no candidate from blocked calculation', () => {
  const ui = panel(); ui.render(forecast({recommendations: []}));
  assert.deepEqual(rows(ui), [['Uygun hamle önerisi yok']]);
});
