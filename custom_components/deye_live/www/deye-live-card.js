/* Deye Live 0.1.0 — self-contained, read-only Lovelace card. */
export const finite = value => typeof value === "number" && Number.isFinite(value) ? value : null;
export const power = value => finite(value) === null ? "—" : Math.abs(value) >= 1000
  ? `${(Math.abs(value) / 1000).toFixed(2)} kW` : `${Math.round(Math.abs(value))} W`;
export function freshness(entity, now = Date.now()) {
  if (!entity || ["unavailable", "unknown"].includes(entity.state)) return { state: "offline", age: null };
  const sampled = Date.parse(entity.attributes?.sampled_at || entity.state);
  const age = (now - sampled) / 1000;
  const interval = finite(entity.attributes?.poll_interval) ?? 5;
  if (!Number.isFinite(age) || age < -5) return { state: "offline", age: null };
  return { state: age > Math.max(15, interval * 3) ? "stale" : "live", age: Math.max(0, Math.floor(age)) };
}
export function flow(value, kind, live = true) {
  if (!live || finite(value) === null) return "unknown";
  if (Math.abs(value) < 10) return "idle";
  if (kind === "grid") return value > 0 ? "import" : "export";
  if (kind === "battery") return value > 0 ? "discharge" : "charge";
  return "generating";
}
const EN = {
  title: "Home energy", eyebrow: "DEYE · LOCAL", live: "Live", stale: "Delayed", offline: "Offline",
  solar: "Solar", grid: "Grid", home: "Home", battery: "Battery", generating: "Generating",
  idle: "Idle", import: "Importing", export: "Exporting", discharge: "Discharging", charge: "Charging",
  unknown: "No fresh reading", consumption: "Using now", reserve: "Battery level", limits: "Battery limits",
  low: "Low battery", shutdown: "Shutdown", restart: "Restart", maxCharge: "Max. charge", maxDischarge: "Max. discharge",
  schedule: "Scheduled targets", scheduleOff: "Schedule disabled", scheduleNote: "Scheduled SOC targets are operating targets, not a hard maximum charge cutoff.",
  readonly: "Read only", updated: "Updated", ago: "s ago", local: "Local · every", seconds: "s",
  missing: "Choose a Deye Live snapshot sensor in the card editor.", missingLimits: "Limits unavailable",
  source: "Snapshot sensor", cardTitle: "Card title", showSolar: "Show solar", showLimits: "Show battery limits",
  awaiting: "Waiting for a fresh local reading", cached: "Last reading is delayed. Flow animation is paused.",
  liveNote: "Live local responses; the logger does not provide a measurement acquisition timestamp.",
};
const ZH = {
  ...EN, title: "家居能源", eyebrow: "DEYE · 本地", live: "即時", stale: "延遲", offline: "離線",
  solar: "太陽能", grid: "電網", home: "家居", battery: "電池", generating: "發電中", idle: "待機",
  import: "輸入中", export: "輸出中", discharge: "放電中", charge: "充電中", unknown: "沒有新數據",
  consumption: "目前用電", reserve: "電池電量", limits: "電池保護與限制", low: "低電量", shutdown: "關機", restart: "重新啟動",
  maxCharge: "最大充電電流", maxDischarge: "最大放電電流", schedule: "排程目標", scheduleOff: "排程已停用",
  scheduleNote: "排程電量為運作目標，並非充電量的硬性上限。", readonly: "唯讀", updated: "更新於", ago: "秒前",
  local: "本地 · 每", seconds: "秒", missing: "請在卡片編輯器選擇 Deye Live 即時快照感測器。", missingLimits: "無法讀取限制",
  source: "即時快照感測器", cardTitle: "卡片標題", showSolar: "顯示太陽能", showLimits: "顯示電池限制",
  awaiting: "正在等候新的本地數據", cached: "數據更新延遲，電力流動動畫已暫停。", liveNote: "即時本地回應；記錄器沒有提供量測採集時間。",
};
const textFor = hass => (hass?.locale?.language || hass?.language || "en").startsWith("zh") ? ZH : EN;
const icons = {
  solar: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  grid: '<path d="M9 3h6l4 18M9 3L5 21M7 10h10M5.5 16h13M9 3l8 7M15 3l-8 7m0 0 11 6m-1-6L6 16m0 0 10 5m2-5L8 21"/>',
  home: '<path d="m3 11 9-8 9 8M5 10v11h14V10M9 21v-7h6v7"/>',
  battery: '<rect x="3" y="6" width="17" height="12" rx="3"/><path d="M22 10v4M7 10v4m4-4v4m4-4v4"/>',
  shield: '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${icons[name]}</svg>`;
const styles = `
  :host{display:block;--dl-ink:var(--primary-text-color,#193c37);--dl-muted:var(--secondary-text-color,#70827d);--dl-green:color-mix(in srgb,var(--primary-text-color,#193c37) 45%,#53a886);--dl-track:rgba(109,142,127,.17);font-family:var(--primary-font-family,Inter,ui-sans-serif,system-ui,sans-serif)}
  *{box-sizing:border-box}ha-card{display:block;overflow:hidden;border-radius:26px;border:1px solid var(--divider-color,rgba(33,76,60,.09));background:var(--ha-card-background,var(--card-background-color,#fcfdfb));color:var(--dl-ink);box-shadow:var(--ha-card-box-shadow,0 8px 36px rgba(30,70,52,.045));padding:24px 22px 17px;position:relative}
  header{display:flex;justify-content:space-between;align-items:center;gap:8px}.eyebrow{font-size:10px;letter-spacing:.16em;color:var(--dl-muted);font-weight:700;margin-bottom:7px}h2{margin:0;font-weight:620;font-size:21px;letter-spacing:-.65px}.status{font-size:11px;white-space:nowrap;border-radius:20px;padding:7px 10px;background:rgba(38,132,106,.09);color:var(--dl-green);display:flex;gap:6px;align-items:center;font-weight:600}.dot{width:6px;height:6px;border-radius:50%;background:currentColor}.status[data-state="stale"]{color:#bd8333;background:rgba(189,131,51,.1)}.status[data-state="offline"]{color:var(--dl-muted);background:var(--dl-track)}
  .stage{position:relative;height:286px;margin:16px -6px 0}.wires{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}.wire{stroke:var(--dl-track);stroke-width:2;fill:none}.moving{stroke:var(--dl-green);stroke-width:2.5;stroke-dasharray:2 19;stroke-linecap:round;fill:none;animation:travel 2.5s linear infinite;opacity:0}.moving.active{opacity:.65}.moving.reverse{animation-direction:reverse}.solar-wire.active{stroke:#c39132}.node{position:absolute;transform:translateX(-50%);width:29%;border:0;background:none;color:inherit;font:inherit;display:flex;flex-direction:column;align-items:center;padding:0;cursor:pointer;gap:0;min-height:118px}.node:focus-visible{outline:2px solid var(--dl-green);border-radius:16px;outline-offset:5px}.solar{left:50%;top:4px}.grid{left:15%;top:137px}.home{left:50%;top:130px}.battery{left:85%;top:137px}.orb{display:flex;justify-content:center;align-items:center;width:62px;height:62px;border-radius:50%;background:var(--ha-card-background,var(--card-background-color,#fcfdfb));border:1px solid var(--dl-track);box-shadow:0 0 0 7px var(--ha-card-background,var(--card-background-color,#fcfdfb))}.orb svg{width:27px;height:27px}.solar .orb{width:54px;height:54px;color:#b68728;background:color-mix(in srgb,var(--ha-card-background,var(--card-background-color,#fcfdfb)) 93%,#d6ac4f)}.home .orb{height:76px;width:76px;background:#214e42;color:#f4faf6;border-color:transparent;box-shadow:0 0 0 7px var(--ha-card-background,var(--card-background-color,#fcfdfb)),0 0 0 8px var(--dl-track)}.home .orb svg{width:32px;height:32px}.battery .orb{color:var(--dl-green)}.node-name{font-size:11px;color:var(--dl-muted);margin-top:10px}.watts{font-size:19px;letter-spacing:-.5px;font-weight:650;line-height:1.55;font-variant-numeric:tabular-nums}.home .watts{font-size:22px}.direction{font-size:10px;color:var(--dl-muted);line-height:1.6}.solar .node-name{margin-top:7px}.solar .watts{font-size:17px;line-height:1.5}.solar .direction{display:none}.stage.no-solar{height:175px;margin-top:15px}.stage.no-solar .solar{display:none}.stage.no-solar .grid,.stage.no-solar .battery{top:17px}.stage.no-solar .home{top:10px}.stage.no-solar .wires{transform:translateY(-120px);height:286px}
  .battery-level{border-top:1px solid var(--dl-track);padding-top:17px;margin-top:5px}.level-header{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:11px}.level-label{font-size:12px;color:var(--dl-muted)}.soc{font-size:27px;font-weight:600;letter-spacing:-1px;font-variant-numeric:tabular-nums}.soc small{font-size:14px;margin-left:2px;letter-spacing:0;color:var(--dl-muted)}.track{height:7px;background:var(--dl-track);border-radius:8px;position:relative;overflow:hidden}.fill{height:100%;border-radius:inherit;background:linear-gradient(90deg,#428d71,#77b79a);transition:width .7s ease}.threshold{position:absolute;top:0;width:2px;height:7px;background:var(--ha-card-background,var(--card-background-color,#fff));opacity:.9}.soc.low{color:#b36c33}.fill.low{background:#b78643}
  details{margin-top:17px;border-top:1px solid var(--dl-track);padding-top:14px}summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:7px;font-size:12px;min-height:24px}summary::-webkit-details-marker{display:none}summary>svg{height:16px;width:16px;color:var(--dl-muted)}.summary-value{margin-left:auto;color:var(--dl-muted);font-size:11px}.chevron{height:7px;width:7px;border-right:1.5px solid var(--dl-muted);border-bottom:1.5px solid var(--dl-muted);transform:rotate(45deg);margin:0 3px 4px 7px}details[open] .chevron{transform:rotate(225deg);margin-top:6px}.limits-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px 18px;margin:16px 0}.limit{display:flex;flex-direction:column;gap:4px}.limit span{font-size:10px;color:var(--dl-muted)}.limit strong{font-size:15px;font-weight:600}.note{color:var(--dl-muted);font-size:10px;line-height:1.6;margin:10px 0 0}.schedule-slots{font-size:10px;color:var(--dl-muted);display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}.schedule-slots span{padding:6px;border-radius:6px;background:var(--dl-track);text-align:center}
  footer{display:flex;justify-content:space-between;gap:8px;margin-top:16px;font-size:9px;color:var(--dl-muted);letter-spacing:.015em}.notice{display:none;font-size:11px;color:var(--dl-muted);padding:12px 0 0;line-height:1.5}.notice.visible{display:block}.offline .stage{opacity:.45}.stale .stage{opacity:.65}.offline .fill,.stale .fill{background:var(--dl-muted)}.offline .moving,.stale .moving{animation:none;opacity:0}.empty{font-size:13px;line-height:1.6;color:var(--dl-muted);padding:20px 0}.hidden{display:none!important}
  @keyframes travel{to{stroke-dashoffset:-42}}@media(prefers-reduced-motion:reduce){.moving{animation:none}.fill{transition:none}}@media(max-width:360px){ha-card{padding:20px 16px 15px}.watts{font-size:17px}.home .watts{font-size:20px}.summary-value{font-size:10px}h2{font-size:19px}}
`;
const BaseElement = typeof HTMLElement === "undefined" ? class {} : HTMLElement;
export class DeyeLiveCard extends BaseElement {
  static getConfigElement() { return document.createElement("deye-live-card-editor"); }
  static getStubConfig(hass) {
    return { entity: Object.values(hass?.states || {}).find(e => e.attributes?.deye_live)?.entity_id || "", show_solar: true, show_limits: true };
  }
  setConfig(config) {
    if (!config || typeof config.entity !== "string") throw new Error("Select a Deye Live snapshot sensor");
    this._config = { show_solar: true, show_limits: true, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.build(); this.render();
  }
  set hass(value) { this._hass = value; this.render(); }
  connectedCallback() { clearInterval(this._timer); this._timer = setInterval(() => this.render(), 1000); this.render(); }
  disconnectedCallback() { clearInterval(this._timer); }
  getCardSize() { return this._config?.show_solar === false ? 4 : 6; }
  getGridOptions() { return { columns: 12, min_columns: 12, rows: "auto" }; }
  build() {
    const node = name => `<button class="node ${name}" data-node="${name}"><span class="orb">${icon(name)}</span><span class="node-name" id="${name}-name"></span><span class="watts" id="${name}-power"></span><span class="direction" id="${name}-direction"></span></button>`;
    this.shadowRoot.innerHTML = `<style>${styles}</style><ha-card><header><div><div class="eyebrow" id="eyebrow"></div><h2 id="title"></h2></div><span class="status" id="status"><i class="dot"></i><span id="status-text"></span></span></header><div class="empty hidden" id="empty"></div><main id="main"><div class="stage" id="stage"><svg class="wires" viewBox="0 0 400 286" preserveAspectRatio="none" aria-hidden="true"><path class="wire" d="M60 168H340"/><path class="wire solar-path" d="M200 31V168"/><path id="grid-flow" class="moving" d="M60 168H200"/><path id="battery-flow" class="moving" d="M340 168H200"/><path id="solar-flow" class="moving solar-wire solar-path" d="M200 31V168"/></svg>${node("solar")}${node("grid")}${node("home")}${node("battery")}</div><section class="battery-level"><div class="level-header"><span class="level-label" id="level-label"></span><span class="soc" id="soc"></span></div><div class="track" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div class="fill" id="fill"></div><i class="threshold" id="threshold"></i></div></section><details id="limits"><summary>${icon("shield")}<span id="limits-title"></span><span class="summary-value" id="limits-summary"></span><i class="chevron"></i></summary><div class="limits-grid">${["maxCharge","maxDischarge","low","shutdown","restart","schedule"].map(k => `<div class="limit"><span id="label-${k}"></span><strong id="value-${k}"></strong></div>`).join("")}</div><div class="schedule-slots" id="slots"></div><p class="note" id="schedule-note"></p><p class="note" id="limits-age"></p></details><div class="notice" id="notice"></div><footer><span id="footer-source"></span><span id="footer-age"></span></footer></main></ha-card>`;
    this.shadowRoot.querySelectorAll("[data-node]").forEach(el => el.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId: this._config.entity } }));
    }));
  }
  render() {
    if (!this.shadowRoot || !this._config || !this._hass) return;
    const $ = id => this.shadowRoot.getElementById(id);
    const put = (id, value) => { $(id).textContent = value; };
    const t = textFor(this._hass), e = this._hass.states?.[this._config.entity];
    const f = freshness(e), live = f.state === "live", offline = f.state === "offline";
    const r = !offline ? e?.attributes?.readings || {} : {};
    const rawLimits = e?.attributes?.limits || {};
    const limitAge = (Date.now() - Date.parse(e?.attributes?.limits_read_at)) / 1000;
    const scheduleAge = (Date.now() - Date.parse(rawLimits.schedule_read_at)) / 1000;
    const limits = !offline && limitAge >= -5 && limitAge < 180 ? rawLimits : {};
    const schedule = !offline && scheduleAge >= -5 && scheduleAge < 180 ? rawLimits : {};
    this.shadowRoot.querySelector("ha-card").className = f.state;
    put("eyebrow", t.eyebrow); put("title", this._config.title || t.title);
    $("status").dataset.state = f.state; $("status").title = t.liveNote; put("status-text", t[f.state]);
    $("main").classList.toggle("hidden", !e); $("empty").classList.toggle("hidden", !!e); put("empty", t.missing);
    $("stage").classList.toggle("no-solar", !this._config.show_solar);
    this.shadowRoot.querySelectorAll(".solar-path").forEach(el => el.classList.toggle("hidden", !this._config.show_solar));
    const readings = { solar: r.solar_power, grid: r.grid_power, home: r.load_power, battery: r.battery_power };
    for (const [name, value] of Object.entries(readings)) {
      const direction = name === "home" ? (live ? "consumption" : "unknown") : flow(value, name, live);
      put(`${name}-name`, t[name]); put(`${name}-power`, power(value)); put(`${name}-direction`, t[direction]);
      this.shadowRoot.querySelector(`[data-node="${name}"]`).setAttribute("aria-label", `${t[name]}: ${power(value)}, ${t[direction]}`);
      if (name !== "home") $(name + "-flow").setAttribute("class", `moving ${name === "solar" ? "solar-wire solar-path" : ""} ${!["unknown", "idle"].includes(direction) ? "active" : ""} ${["export", "charge"].includes(direction) ? "reverse" : ""} ${name === "solar" && !this._config.show_solar ? "hidden" : ""}`);
    }
    const soc = finite(r.battery_soc), low = finite(limits.low_soc);
    put("level-label", t.reserve); put("soc", soc === null ? "—" : `${soc}%`);
    $("soc").classList.toggle("low", soc !== null && low !== null && soc <= low);
    $("fill").classList.toggle("low", soc !== null && low !== null && soc <= low);
    $("fill").style.width = `${Math.max(0, Math.min(100, soc || 0))}%`;
    const track = this.shadowRoot.querySelector(".track");
    track.setAttribute("aria-label", t.reserve); track.setAttribute("aria-valuetext", soc === null ? t.unknown : `${soc}%`);
    if (soc === null) track.removeAttribute("aria-valuenow"); else track.setAttribute("aria-valuenow", soc);
    $("threshold").style.left = `${low ?? 0}%`; $("threshold").classList.toggle("hidden", low === null);
    $("limits").classList.toggle("hidden", !this._config.show_limits); put("limits-title", t.limits);
    const unit = (n, u) => finite(n) === null ? "—" : `${n}${u}`;
    put("limits-summary", low !== null ? `${t.low} ${low}%` : t.missingLimits);
    const values = { maxCharge: unit(limits.max_charge_current, " A"), maxDischarge: unit(limits.max_discharge_current, " A"),
      low: unit(limits.low_soc, "%"), shutdown: unit(limits.shutdown_soc, "%"), restart: unit(limits.restart_soc, "%"),
      schedule: schedule.schedule_enabled === false ? t.scheduleOff : finite(schedule.schedule_target_min) === null ? "—" : `${schedule.schedule_target_min}–${schedule.schedule_target_max}%` };
    for (const [key, value] of Object.entries(values)) { put(`label-${key}`, t[key]); put(`value-${key}`, value); }
    const slots = $("slots"), signature = JSON.stringify(schedule.schedule || []);
    if (slots.dataset.signature !== signature) {
      slots.replaceChildren(...(schedule.schedule || []).map(slot => { const el = document.createElement("span"); el.textContent = `${slot.start} · ${slot.target_soc}%`; return el; }));
      slots.dataset.signature = signature;
    }
    put("schedule-note", t.scheduleNote);
    put("limits-age", `${t.readonly}${Number.isFinite(limitAge) && Object.keys(limits).length ? ` · ${t.updated} ${new Date(e.attributes.limits_read_at).toLocaleTimeString()}` : ""}`);
    $("notice").classList.toggle("visible", !live); put("notice", offline ? t.awaiting : t.cached);
    put("footer-source", `${t.local} ${e?.attributes?.poll_interval || 5}${t.seconds} · ${t.readonly}`);
    put("footer-age", f.age === null ? "—" : `${t.updated} ${f.age}${t.ago}`);
  }
}

class DeyeLiveCardEditor extends BaseElement {
  setConfig(config) { this._config = config; this.draw(); }
  set hass(hass) { this._hass = hass; this.draw(); }
  draw() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    // Do not rebuild while the user types or HA sends unrelated entity updates.
    if (this.shadowRoot.childElementCount) return;
    const t = textFor(this._hass);
    const style = document.createElement("style"); style.textContent = `label{display:block;margin:15px 0;font:14px system-ui;color:var(--primary-text-color)}select,input[type=text]{display:block;width:100%;padding:12px;margin-top:8px;border:1px solid var(--divider-color,#aaa);border-radius:8px;box-sizing:border-box;background:var(--card-background-color,#fff);color:inherit;font:inherit}input[type=checkbox]{margin-right:10px}`;
    this.shadowRoot.append(style);
    const select = document.createElement("select");
    const blank = document.createElement("option"); blank.value = ""; blank.textContent = t.source; select.append(blank);
    for (const entity of Object.values(this._hass.states).filter(e => e.attributes?.deye_live)) {
      const option = document.createElement("option"); option.value = entity.entity_id; option.textContent = entity.attributes.friendly_name || entity.entity_id; select.append(option);
    }
    this.field(t.source, select, "entity"); select.value = this._config.entity || "";
    const title = document.createElement("input"); title.type = "text"; title.value = this._config.title || ""; title.placeholder = t.title;
    this.field(t.cardTitle, title, "title");
    for (const [key, label] of [["show_solar", t.showSolar], ["show_limits", t.showLimits]]) {
      const input = document.createElement("input"); input.type = "checkbox"; input.checked = this._config[key] !== false; this.field(label, input, key);
    }
  }
  field(text, control, key) {
    const label = document.createElement("label"); label.append(document.createTextNode(text), control); this.shadowRoot.append(label);
    control.addEventListener("change", () => {
      this._config = { ...this._config, [key]: control.type === "checkbox" ? control.checked : control.value };
      this.dispatchEvent(new CustomEvent("config-changed", { bubbles: true, composed: true, detail: { config: this._config } }));
    });
  }
}
if (typeof customElements !== "undefined") {
  if (!customElements.get("deye-live-card")) customElements.define("deye-live-card", DeyeLiveCard);
  if (!customElements.get("deye-live-card-editor")) customElements.define("deye-live-card-editor", DeyeLiveCardEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.some(c => c.type === "deye-live-card")) window.customCards.push({ type: "deye-live-card", name: "Deye Live", description: "Local power flow, battery percentage and read-only battery limits", preview: true });
}
