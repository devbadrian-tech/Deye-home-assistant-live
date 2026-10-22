import test from 'node:test';
import assert from 'node:assert/strict';

const cardUrl = new URL('../custom_components/deye_live/www/deye-live-card.js', import.meta.url);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function registry() {
  const elements = new Map();
  return {
    get: name => elements.get(name),
    define(name, constructor) {
      assert.equal(elements.has(name), false, `duplicate registration: ${name}`);
      elements.set(name, constructor);
    },
  };
}
async function browserFixture(run) {
  const names = ['document', 'window', 'HTMLElement', 'customElements'];
  const original = new Map(names.map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  Object.assign(globalThis, {
    document: { readyState: 'complete', querySelector: () => ({}) },
    window: {}, HTMLElement: class NativeElement {}, customElements: registry(),
  });
  try { await run(); }
  finally {
    for (const [name, descriptor] of original) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
  }
}

test('early module waits for HA to replace both registry and HTMLElement', async () => {
  await browserFixture(async () => {
    const nativeRegistry = customElements;
    const importing = import(`${cardUrl}?startup=early`);
    await pause(20);
    const prematurelyRegistered = nativeRegistry.get('deye-live-card');
    const patchedRegistry = registry();
    class PatchedElement {}
    globalThis.HTMLElement = PatchedElement;
    globalThis.customElements = patchedRegistry;
    patchedRegistry.define('home-assistant', class extends PatchedElement {});
    const module = await importing;
    assert.equal(prematurelyRegistered, undefined);
    assert.equal(nativeRegistry.get('deye-live-card'), undefined);
    assert.equal(patchedRegistry.get('deye-live-card'), module.DeyeLiveCard);
    assert.ok(module.DeyeLiveCard.prototype instanceof PatchedElement);
    assert.ok(patchedRegistry.get('deye-live-card-editor').prototype instanceof PatchedElement);
  });
});

test('a ready frontend loads immediately and duplicate URLs keep one registration', async () => {
  await browserFixture(async () => {
    customElements.define('home-assistant', class extends HTMLElement {});
    const first = await import(`${cardUrl}?startup=ready`);
    await import(`${cardUrl}?startup=dashboard`);
    assert.equal(customElements.get('deye-live-card'), first.DeyeLiveCard);
    assert.equal(window.customCards.filter(card => card.type === 'deye-live-card').length, 1);
  });
});

test('standalone preview waits for DOM readiness without requiring Home Assistant', async () => {
  await browserFixture(async () => {
    let domReady;
    document.readyState = 'loading';
    document.querySelector = () => null;
    document.addEventListener = (event, callback) => {
      assert.equal(event, 'DOMContentLoaded');
      domReady = callback;
    };
    const importing = import(`${cardUrl}?startup=preview`);
    for (let i = 0; i < 20 && !domReady; i++) await pause(5);
    assert.equal(typeof domReady, 'function');
    assert.equal(customElements.get('deye-live-card'), undefined);
    document.readyState = 'interactive';
    domReady();
    const module = await importing;
    assert.equal(customElements.get('deye-live-card'), module.DeyeLiveCard);
  });
});
