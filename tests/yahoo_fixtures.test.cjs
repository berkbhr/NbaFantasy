const {test} = require('node:test');
const assert = require('node:assert/strict');
const {parseYahooFantasyPeriod: period} = require('../src/yahoo_fixtures.js');

test('Yahoo dates cross calendar years using the captured season', () => {
  assert.deepEqual(period('Week 10 (Dec 28 - Jan 3)', '2026_27'), ['2026-12-28', '2027-01-03']);
});
test('a scoring period can last two weeks instead of seven days', () => {
  assert.deepEqual(period('Week 17: Feb 8 – 21', '2026_27'), ['2027-02-08', '2027-02-21']);
});
test('explicit years cannot be silently replaced by the current season', () => {
  assert.equal(period('Nov 2, 2025 - Nov 8, 2025', '2026_27'), null);
  assert.deepEqual(period('Nov 2, 2026 - Nov 8, 2026', '2026_27'), ['2026-11-02', '2026-11-08']);
});
test('missing dates, season and impossible calendar dates fail closed', () => {
  for (const label of ['Week 2', 'Nov 31 - Dec 6', 'Nov 8 - Nov 2']) assert.equal(period(label, '2026_27'), null);
  assert.equal(period('Nov 2 - Nov 8', ''), null);
  assert.equal(period('Nov 2 - Nov 8', '2026_28'), null);
});
test('explicit ISO dates still require the correct season and period length', () => {
  assert.deepEqual(period('2026-11-02 - 2026-11-08', '2026_27'), ['2026-11-02', '2026-11-08']);
  assert.equal(period('2025-11-02 - 2025-11-08', '2026_27'), null);
  assert.equal(period('2026-11-02 - 2026-12-08', '2026_27'), null);
});
