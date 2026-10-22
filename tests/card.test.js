import test from 'node:test';
import assert from 'node:assert/strict';
import { finite, power, freshness, flow } from '../custom_components/deye_live/www/deye-live-card.js';

test('missing readings never turn into zero watts', () => {
  for (const n of [null, undefined, NaN, Infinity, '0', 'unavailable']) assert.equal(power(n), '—');
  assert.equal(power(0), '0 W'); assert.equal(power(-1820), '1.82 kW');
});
test('freshness follows successful sample time, not unchanged power or entity change time', () => {
  const now = Date.now();
  const entity = { state: 'valid', last_changed: '2000-01-01', attributes: { sampled_at: new Date(now - 4000).toISOString(), poll_interval: 5 } };
  assert.equal(freshness(entity, now).state, 'live');
  assert.equal(freshness(entity, now + 16000).state, 'stale');
  assert.equal(freshness({...entity,state:'unavailable'},now).state, 'offline');
  assert.equal(freshness({state:'garbage'},now).state, 'offline');
  assert.equal(freshness({state:new Date(now+60000).toISOString()},now).state, 'offline');
});
test('all signed power directions and idle deadband', () => {
  assert.equal(flow(900,'grid'), 'import'); assert.equal(flow(-900,'grid'), 'export');
  assert.equal(flow(900,'battery'), 'discharge'); assert.equal(flow(-900,'battery'), 'charge');
  assert.equal(flow(0,'grid'), 'idle'); assert.equal(flow(9,'battery'), 'idle');
  assert.equal(flow(900,'battery',false), 'unknown'); assert.equal(flow(null,'grid'), 'unknown');
});
