"""Shared layout and navigation for Agent Playground multi-page app."""

import json

from nicegui import app, ui

NAV_ITEMS = [
    {"path": "/", "label": "Home", "icon": "home"},
    {"path": "/coach", "label": "Coach", "icon": "auto_awesome", "primary": True},
    {"path": "/gdpr-demo", "label": "GDPR Demo", "icon": "policy", "core": True},
    {"path": "/mass-effect-localization-demo", "label": "Mass Effect LQA", "icon": "translate", "core": True},
    {"path": "/coding", "label": "Annotations", "icon": "rate_review"},
    {"path": "/report", "label": "Evidence", "icon": "fact_check", "output": True},
    {"path": "/requirements", "label": "requirements.md", "icon": "description", "output": True},
    {"path": "/judge", "label": "Judge", "icon": "gavel", "output": True},
]

PROJECT_STATE_KEEP_KEYS = {"authenticated", "email", "oauth_tokens", "oauth_state"}


def _clear_project_state(storage: dict) -> None:
    """Clear the loaded project while preserving the current login state."""
    for key in list(storage.keys()):
        if key not in PROJECT_STATE_KEEP_KEYS:
            storage.pop(key, None)


BRAND_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg-base: #090b0f;
  --bg-surface-1: #101419;
  --bg-surface-2: #151a20;
  --bg-surface-3: #1b222a;
  --bg-hover: #202934;
  --border-subtle: rgba(204,219,226,0.07);
  --border-default: rgba(204,219,226,0.11);
  --border-strong: rgba(204,219,226,0.18);
  --text-primary: #f5f7f8;
  --text-secondary: #bac5ca;
  --text-tertiary: #7f8b92;
  --text-muted: #53616a;
  --accent: #1fb6a6;
  --accent-bright: #5ee0d2;
  --accent-tint: rgba(31,182,166,0.13);
  --green: #42bd73;
  --green-tint: rgba(66,189,115,0.13);
  --green-bright: #7ee59d;
  --yellow: #f4b860;
  --yellow-tint: rgba(244,184,96,0.13);
  --red: #f97066;
  --red-tint: rgba(249,112,102,0.12);
  --blue: #6aa9ff;
  --blue-tint: rgba(106,169,255,0.13);
  --violet: #b18cff;
  --violet-tint: rgba(177,140,255,0.13);
  --orange: #ff9f43;
  --orange-tint: rgba(255,159,67,0.13);
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
}

* { box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-size: 0.875rem;
  letter-spacing: 0;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* Override NiceGUI/Quasar defaults */
.q-page, .q-layout, .q-page-container, .nicegui-content {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
}
.q-card {
  background: var(--bg-surface-2) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  box-shadow: none !important;
}
.q-field__control {
  background: var(--bg-surface-1) !important;
  color: var(--text-primary) !important;
}
.q-field__label, .q-field__native, .q-field__input {
  color: var(--text-primary) !important;
}
.q-table { background: var(--bg-surface-2) !important; color: var(--text-primary) !important; }
.q-table th { color: var(--text-tertiary) !important; border-color: var(--border-subtle) !important; }
.q-table td { color: var(--text-secondary) !important; border-color: var(--border-subtle) !important; }
.q-linear-progress__track { background: var(--bg-hover) !important; }
.q-badge { font-weight: 500; }
.q-expansion-item { background: var(--bg-surface-2) !important; border-radius: var(--radius-xl) !important; }
.q-expansion-item__container { color: var(--text-primary) !important; }
.q-item__label { color: var(--text-primary) !important; }
.q-splitter__separator { background: var(--border-subtle) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

/* Brand */
.brand-title {
  font-size: 0.9rem; font-weight: 600; color: var(--text-primary);
  letter-spacing: 0;
}
.brand-subtitle { font-size: 0.75rem; color: var(--text-tertiary); }
.brand-stack { display: flex; flex-direction: column; gap: 0; line-height: 1.05; }
.brand-context {
  font-size: 0.62rem; color: var(--text-tertiary);
  letter-spacing: 0.05em; text-transform: uppercase;
}

/* Cards */
.page-card {
  background: var(--bg-surface-2);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-subtle);
  padding: 1.25rem;
  transition: border-color 150ms ease;
}
.page-card:hover { border-color: var(--border-default); }

/* Dynamic product pages */
.dynamic-page {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.25rem 1.5rem 2.75rem;
}
.dynamic-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 0.34fr);
  gap: 18px;
  align-items: stretch;
  padding: 20px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg, rgba(31,182,166,0.13), rgba(106,169,255,0.08) 48%, rgba(177,140,255,0.08)),
    var(--bg-surface-1);
}
.dynamic-hero::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-bright), var(--yellow), var(--blue), var(--violet));
}
.dynamic-kicker {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  width: fit-content;
  padding: 4px 9px;
  border-radius: 99px;
  border: 1px solid rgba(94,224,210,0.24);
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.64rem;
  font-weight: 760;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.dynamic-title {
  margin-top: 12px;
  max-width: 780px;
  font-size: 2rem;
  line-height: 1.12;
  font-weight: 760;
  color: var(--text-primary);
}
.dynamic-copy {
  margin-top: 9px;
  max-width: 760px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-secondary);
}
.dynamic-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 16px;
}
.dynamic-side-panel {
  padding: 14px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  background:
    linear-gradient(180deg, rgba(106,169,255,0.10), rgba(177,140,255,0.04)),
    var(--bg-surface-1);
}
.dynamic-side-label {
  font-size: 0.62rem;
  font-weight: 760;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--blue);
}
.dynamic-side-value {
  margin-top: 8px;
  font-size: 1.7rem;
  line-height: 1;
  font-weight: 780;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.dynamic-side-copy {
  margin-top: 7px;
  font-size: 0.74rem;
  line-height: 1.45;
  color: var(--text-tertiary);
}
.dynamic-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.68fr) minmax(260px, 0.32fr);
  gap: 16px;
  align-items: start;
  margin-top: 16px;
}
.dynamic-panel {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 15px;
  transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
}
.dynamic-panel:hover {
  border-color: var(--border-default);
  transform: translateY(-1px);
}
.dynamic-panel.accent-teal { border-top: 3px solid var(--accent-bright); }
.dynamic-panel.accent-amber { border-top: 3px solid var(--yellow); }
.dynamic-panel.accent-blue { border-top: 3px solid var(--blue); }
.dynamic-panel.accent-coral { border-top: 3px solid var(--red); }
.dynamic-panel.accent-violet { border-top: 3px solid var(--violet); }
.dynamic-panel-title {
  font-size: 0.92rem;
  font-weight: 720;
  color: var(--text-primary);
}
.dynamic-panel-copy {
  margin-top: 4px;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--text-tertiary);
}
.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.metric-tile {
  position: relative;
  overflow: hidden;
  min-height: 82px;
  padding: 12px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-1);
  --tile-color: var(--accent-bright);
}
.metric-tile::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: var(--tile-color);
}
.metric-tile:nth-child(2) { --tile-color: var(--yellow); }
.metric-tile:nth-child(3) { --tile-color: var(--blue); }
.metric-tile:nth-child(4) { --tile-color: var(--violet); }
.metric-tile-value {
  color: var(--tile-color);
  font-size: 1.4rem;
  font-weight: 780;
  font-variant-numeric: tabular-nums;
}
.metric-tile-label {
  margin-top: 3px;
  color: var(--text-tertiary);
  font-size: 0.64rem;
  font-weight: 720;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.document-preview {
  max-height: 72vh;
  overflow: auto;
  padding: 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: #0c1015;
}
.empty-state-panel {
  max-width: 560px;
  margin: 8vh auto 0;
  padding: 28px;
  text-align: center;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  background:
    linear-gradient(180deg, rgba(31,182,166,0.09), rgba(244,184,96,0.04)),
    var(--bg-surface-1);
}
.empty-state-panel .material-icons {
  color: var(--accent-bright);
  font-size: 2.4rem;
}
.empty-state-title {
  margin-top: 12px;
  font-size: 1.05rem;
  font-weight: 740;
  color: var(--text-primary);
}
.empty-state-copy {
  margin-top: 7px;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--text-secondary);
}

/* Section titles */
.section-title {
  font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.04em;
}

/* Code chips */
.code-chip {
  background: var(--accent-tint); color: var(--accent-bright);
  border-radius: var(--radius-sm); padding: 3px 9px;
  font-size: 0.75rem; font-weight: 500;
  display: inline-block; margin: 2px; cursor: pointer;
  border: 1px solid transparent;
  transition: all 150ms ease;
}
.code-chip:hover { background: rgba(94,106,210,0.2); border-color: var(--accent); }
.code-chip.selected { background: var(--accent); color: white; }

/* Paradigm slots */
.paradigm-slot {
  border: 1px dashed var(--border-default); border-radius: var(--radius-xl);
  min-height: 90px; padding: 12px; transition: border-color 200ms ease;
  background: var(--bg-surface-1);
}
.paradigm-slot:hover { border-color: var(--accent); }
.paradigm-slot.has-items { border-style: solid; border-color: var(--green); background: var(--green-tint); }

/* Pattern cards */
.pattern-card {
  background: var(--bg-surface-2); border-radius: var(--radius-xl);
  border-left: 3px solid var(--green); padding: 14px;
  border: 1px solid var(--border-subtle); border-left: 3px solid var(--green);
  margin-bottom: 10px;
}
.severity-high { border-left-color: var(--red); }
.severity-medium { border-left-color: var(--yellow); }
.severity-low { border-left-color: var(--green); }

/* Memo box */
.memo-box {
  background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.2);
  border-radius: var(--radius-lg); padding: 10px; font-size: 0.8rem;
}

/* Stat cards */
.stat-card {
  background: var(--bg-surface-2); border-radius: var(--radius-xl);
  padding: 16px; text-align: center; border: 1px solid var(--border-subtle);
}
.stat-value { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.stat-label { font-size: 0.65rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 2px; }

/* Buttons */
.q-btn { letter-spacing: 0 !important; }
.q-btn.bg-primary {
  background: var(--accent) !important;
  color: #071314 !important;
}
.q-btn.bg-primary:hover {
  background: var(--accent-bright) !important;
}
.q-btn.text-primary {
  color: var(--accent-bright) !important;
}

.app-header {
  min-height: 48px;
}
.app-nav-row {
  flex: 1;
  justify-content: center;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.app-nav-row::-webkit-scrollbar { display: none; }
.app-action-row {
  flex-shrink: 0;
}
.coach-nav-btn {
  color: #061314 !important;
  background: linear-gradient(135deg, rgba(94,224,210,0.95), rgba(244,184,96,0.72)) !important;
  border: 1px solid rgba(94,224,210,0.48) !important;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06), 0 0 18px rgba(31,182,166,0.18) !important;
}
.coach-nav-btn:hover {
  background: linear-gradient(135deg, rgba(94,224,210,1), rgba(255,207,119,0.86)) !important;
  border-color: var(--accent-bright) !important;
}
.core-nav-btn {
  color: var(--text-secondary) !important;
}
.output-nav-btn {
  color: var(--blue) !important;
  border: 1px solid rgba(106,169,255,0.22) !important;
  background: rgba(106,169,255,0.07) !important;
}

/* Active nav indicator */
.nav-active {
  border-bottom: 2px solid var(--accent-bright) !important;
  color: var(--text-primary) !important;
  background: rgba(31,182,166,0.08) !important;
  border-radius: 6px 6px 0 0 !important;
}

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.animate-in { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
.stagger-1 { animation-delay: 0s; }
.stagger-2 { animation-delay: 0.1s; opacity: 0; }
.stagger-3 { animation-delay: 0.2s; opacity: 0; }
.stagger-4 { animation-delay: 0.3s; opacity: 0; }
.stagger-5 { animation-delay: 0.4s; opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 900px) {
  .app-header {
    height: auto !important;
    min-height: 48px;
    padding: 0.35rem 0.75rem !important;
    gap: 0.35rem;
    flex-wrap: wrap;
  }
  .app-nav-row {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    padding-bottom: 0.1rem;
  }
  .app-nav-row .q-btn {
    flex-shrink: 0;
  }
  .coach-output-grid {
    grid-template-columns: 1fr;
  }
  .coach-step-grid {
    grid-template-columns: 1fr;
  }
  .coach-next-line {
    grid-template-columns: 1fr;
    gap: 3px;
  }
  .coach-led-stage {
    grid-template-columns: 1fr;
  }
  .dynamic-page {
    padding: 1rem 1rem 2rem;
  }
  .dynamic-hero,
  .dynamic-grid {
    grid-template-columns: 1fr;
  }
  .dynamic-title {
    font-size: 1.55rem;
  }
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .metric-strip {
    grid-template-columns: 1fr;
  }
}

/* ── Coach page ──────────────────────────────────────────────────────── */
.coach-product-panel {
  position: relative;
  overflow: hidden;
  width: 100%;
  padding: 20px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg, rgba(31,182,166,0.12), rgba(244,184,96,0.07) 48%, rgba(106,169,255,0.08)),
    var(--bg-surface-1);
}
.coach-product-panel::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-bright), var(--yellow), var(--blue), var(--violet));
}
.coach-product-kicker {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  padding: 4px 9px;
  border-radius: 99px;
  border: 1px solid rgba(94,224,210,0.24);
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.62rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.coach-product-title {
  margin-top: 10px;
  font-size: 1.45rem;
  line-height: 1.2;
  font-weight: 750;
  color: var(--text-primary);
}
.coach-product-copy {
  max-width: 820px;
  margin-top: 7px;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--text-secondary);
}
.coach-next-line {
  display: grid;
  grid-template-columns: 48px minmax(120px, 0.28fr) minmax(0, 1fr);
  gap: 12px;
  align-items: baseline;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: rgba(9,11,15,0.42);
}
.coach-next-line span {
  font-size: 0.62rem;
  font-weight: 760;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-bright);
}
.coach-next-line strong {
  font-size: 0.84rem;
  color: var(--text-primary);
}
.coach-next-line em {
  font-style: normal;
  font-size: 0.74rem;
  line-height: 1.45;
  color: var(--text-tertiary);
}
.coach-led-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 0.34fr);
  gap: 14px;
  align-items: stretch;
  margin-top: 14px;
}
.coach-led-stage.coach-led-single {
  grid-template-columns: minmax(0, 1fr);
}
.coach-led-current,
.coach-led-action {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: rgba(9,11,15,0.42);
  padding: 14px;
}
.coach-led-action {
  border-color: rgba(94,224,210,0.20);
}
.coach-led-label {
  font-size: 0.62rem;
  font-weight: 760;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-bright);
}
.coach-led-title {
  margin-top: 7px;
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 740;
}
.coach-led-copy {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 0.78rem;
  line-height: 1.5;
}
.coach-led-outcome {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  margin-top: 10px;
  padding: 5px 8px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(66,189,115,0.18);
  background: var(--green-tint);
  color: var(--green-bright);
}
.coach-led-outcome span {
  font-size: 0.58rem;
  font-weight: 760;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--green-bright);
}
.coach-led-outcome strong {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-primary);
}
.coach-led-prompt {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  color: var(--yellow);
  font-size: 0.76rem;
  line-height: 1.45;
}
.coach-output-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.coach-output-card {
  min-height: 118px;
  padding: 12px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
}
.coach-output-card .material-icons {
  color: var(--accent-bright);
  font-size: 1.05rem;
}
.coach-output-title {
  margin-top: 7px;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-primary);
}
.coach-output-copy {
  margin-top: 4px;
  font-size: 0.7rem;
  line-height: 1.42;
  color: var(--text-tertiary);
}
.coach-workbench-label {
  margin-top: 16px;
  font-size: 0.66rem;
  font-weight: 750;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.coach-step-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 9px;
  margin-top: 9px;
}
.coach-step-card {
  min-height: 154px;
  padding: 11px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
}
.coach-step-card.current {
  border-color: rgba(130,143,255,0.48);
  background: linear-gradient(180deg, rgba(94,106,210,0.13), var(--bg-surface-2));
}
.coach-step-card.done {
  border-color: rgba(74,222,128,0.26);
}
.coach-step-card.next {
  opacity: 0.82;
}
.coach-step-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.coach-step-num {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 99px;
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.66rem;
  font-weight: 760;
}
.coach-step-status {
  padding: 2px 6px;
  border-radius: 99px;
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  font-size: 0.54rem;
  font-weight: 760;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.coach-step-card.done .coach-step-status {
  color: var(--green-bright);
  border-color: rgba(74,222,128,0.22);
}
.coach-step-card.current .coach-step-status {
  color: var(--accent-bright);
  border-color: rgba(130,143,255,0.34);
}
.coach-step-title {
  margin-top: 10px;
  font-size: 0.77rem;
  font-weight: 700;
  color: var(--text-primary);
}
.coach-step-copy {
  margin-top: 5px;
  font-size: 0.68rem;
  line-height: 1.4;
  color: var(--text-tertiary);
}
.coach-step-output {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
  color: var(--green-bright);
  font-size: 0.64rem;
  line-height: 1.35;
}
.coach-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.coach-action-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(94,224,210,0.18);
  background: rgba(31,182,166,0.10);
  color: var(--text-secondary);
  font-size: 0.78rem;
}
.coach-action-note .material-icons {
  color: var(--accent-bright);
  font-size: 1rem;
}
.coach-action-note strong {
  color: var(--text-primary);
}
.chat-card {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(106,169,255,0.06), rgba(31,182,166,0.03)),
    var(--bg-surface-2);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
}
.chat-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, var(--blue), var(--accent-bright), var(--yellow));
}
.coach-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.coach-chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  font-size: 0.94rem;
  font-weight: 730;
}
.coach-chat-title .material-icons {
  color: var(--accent-bright);
  font-size: 1.05rem;
}
.coach-chat-copy {
  color: var(--text-tertiary);
  font-size: 0.73rem;
  line-height: 1.42;
}
.coach-input-row {
  padding: 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
}
.msg-user { background: var(--accent-tint); border: 1px solid rgba(94,224,210,0.22); border-radius: var(--radius-lg); padding: 12px 16px; margin: 6px 0; color: var(--text-primary); }
.msg-ai { background: var(--bg-surface-1); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--accent); color: var(--text-secondary); }
.msg-ai strong { color: var(--text-primary); }
.msg-error { background: var(--red-tint); border: 1px solid rgba(235,87,87,0.2); border-radius: var(--radius-lg); padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--red); color: var(--text-secondary); }
.input-box { border-radius: 10px !important; background: var(--bg-surface-1) !important; border: 1px solid var(--border-default) !important; font-size: 0.88rem !important; color: var(--text-primary) !important; transition: border-color 150ms ease !important; }
.input-box:focus-within { border-color: var(--accent) !important; }
.send-btn { background: var(--accent) !important; color: white !important; transition: opacity 150ms ease !important; }
.send-btn:hover { opacity: 0.85 !important; }

/* Progress tracker */
.progress-track { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin-bottom: 1rem; background: var(--bg-surface-2); border-radius: 10px; border: 1px solid var(--border-subtle); }
.progress-dot { display: flex; flex-direction: column; align-items: center; flex: 1; }
.dot-circle { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.72rem; font-weight: 600; background: var(--bg-hover); color: var(--text-muted); transition: all 0.3s ease; }
.progress-dot.active .dot-circle { background: var(--green-tint); color: var(--green-bright); }
.progress-dot.current .dot-circle { background: var(--accent); color: white; box-shadow: 0 0 12px rgba(94,106,210,0.4); }
.dot-label { font-size: 0.6rem; color: var(--text-muted); margin-top: 4px; font-weight: 500; }
.progress-dot.active .dot-label { color: var(--green-bright); }
.progress-dot.current .dot-label { color: var(--accent-bright); font-weight: 600; }

/* Sidebar */
.sidebar-panel { width: 320px; min-width: 320px; padding: 1.25rem 1rem; background: var(--bg-surface-2); border-radius: 12px; border: 1px solid var(--border-subtle); height: fit-content; position: sticky; top: 1rem; max-height: 90vh; overflow-y: auto; }
.sidebar-section { margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle); }
.sidebar-section:last-child { border-bottom: none; }
.sidebar-title { font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.sidebar-value { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
.sidebar-detail { font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4; }
.sidebar-empty { font-size: 0.75rem; color: var(--text-muted); }

/* Annotation labels */
.annotation-correct { color: var(--green-bright); }
.annotation-partial { color: var(--yellow); }
.annotation-incorrect { color: var(--red); }
"""


def page_layout(title: str = "", current_path: str = ""):
    """Apply shared page layout with the app header and progressive navigation."""
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    # Detect current path from title mapping if not provided
    if not current_path:
        for item in NAV_ITEMS:
            if item["label"].lower() in title.lower():
                current_path = item["path"]
                break

    with ui.header().classes("app-header items-center justify-between").style(
        "background: rgba(8,9,10,0.85); backdrop-filter: blur(20px); "
        "border-bottom: 1px solid rgba(255,255,255,0.06); "
        "padding: 0 1.5rem; height: 48px; "
    ):
        with ui.row().classes("items-center gap-sm"):
            ui.icon("rate_review").style("color: var(--accent-bright); font-size: 1.1rem")
            ui.html(
                '<span class="brand-stack">'
                '<span class="brand-title">GEDD</span>'
                '<span class="brand-context">SME Error Analysis → Annotations → Domain Driven Specs Development</span>'
                '</span>'
            )

        storage = app.storage.user
        session_data = storage.get("session_data", {})
        agent_spec = session_data.get("agent_spec", {}) if isinstance(session_data, dict) else {}
        has_domain = bool(agent_spec.get("domain_context") or agent_spec.get("name")) if isinstance(agent_spec, dict) else False
        has_queries = bool(session_data.get("golden_prompts")) if isinstance(session_data, dict) else False
        has_baseline_evidence = bool(storage.get("eval_results") or storage.get("coding_annotations"))
        has_annotations = bool(storage.get("coding_annotations"))
        has_outputs = bool(storage.get("codebook") or storage.get("_generated_judge_prompt"))

        def should_show_nav(path: str) -> bool:
            if path in {"/", "/coach", "/gdpr-demo", "/mass-effect-localization-demo"}:
                return True
            if path == "/coding":
                return current_path == path or has_queries or has_baseline_evidence
            if path == "/report":
                return current_path == path or has_annotations or has_outputs
            if path in {"/requirements", "/judge"}:
                return current_path == path or has_outputs
            return current_path == path or has_domain

        with ui.row().classes("app-nav-row items-center gap-xs"):
            for item in NAV_ITEMS:
                if not should_show_nav(item["path"]):
                    continue
                is_active = current_path == item["path"]
                button = ui.button(
                    item["label"], icon=item["icon"],
                    on_click=lambda p=item["path"]: ui.navigate.to(p),
                ).props("flat no-caps size=sm")
                if is_active:
                    button.classes("nav-active")
                elif item.get("primary"):
                    button.classes("coach-nav-btn").tooltip("Open Coach")
                elif item.get("output"):
                    button.classes("output-nav-btn").tooltip("Open generated output")
                elif item.get("core"):
                    button.classes("core-nav-btn")
                button.style(
                    "color: var(--text-tertiary); font-weight: 500; font-size: 0.8rem; "
                    "border-radius: 6px; padding: 4px 10px;"
                )

        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        def confirm_new_project():
            with ui.dialog() as dlg:
                dlg.open()
                with ui.card().style(
                    "min-width:320px; padding:1.5rem; background:var(--bg-surface-2); "
                    "border:1px solid var(--border-default); border-radius:12px"
                ):
                    ui.label("Start a New Project?").style(
                        "font-size:1rem; font-weight:600; color:var(--text-primary); margin-bottom:8px"
                    )
                    ui.label(
                        "This will clear your current session - domain profile, curated queries, "
                        "annotations, codebook, and all analysis. This cannot be undone."
                    ).style("font-size:0.82rem; color:var(--text-secondary); margin-bottom:16px")
                    with ui.row().classes("gap-2 justify-end"):
                        ui.button("Cancel", on_click=dlg.close).props("flat size=sm dark").style(
                            "color:var(--text-tertiary)"
                        )
                        def do_reset():
                            _clear_project_state(app.storage.user)
                            dlg.close()
                            ui.navigate.to("/")
                        ui.button("Start Fresh", icon="refresh", on_click=do_reset).props(
                            "size=sm color=negative"
                        )

        def open_session_dialog():
            with ui.dialog() as dlg:
                dlg.open()
                with ui.card().style(
                    "min-width:380px; padding:1.5rem; background:var(--bg-surface-2); "
                    "border:1px solid var(--border-default); border-radius:12px"
                ):
                    ui.label("Output Bundle").style(
                        "font-size:1rem; font-weight:600; color:var(--text-primary); "
                        "margin-bottom:8px"
                    )
                    ui.label(
                        "Export or import SME_error_analysis.md, the curated evidence handoff "
                        "behind Kiro requirements.md and the LLM-as-Judge prompt."
                    ).style("font-size:0.82rem; color:var(--text-secondary); margin-bottom:16px")

                    def export_session():
                        from grounded_evals.agent.tools import StateBundle
                        from grounded_evals.guide.session import Session
                        from grounded_evals.guide.session_io import (
                            build_session_payload,
                            validate_session_handoff,
                        )

                        storage = app.storage.user
                        session = Session.model_validate(storage.get("session_data", {}))
                        state = StateBundle(
                            session=session,
                            annotations=storage.get("annotations", []),
                            current_step=storage.get("current_step", session.current_step),
                            prompt_variants=storage.get("prompt_variants", []),
                        )
                        payload = build_session_payload(state, storage.get("messages", []))
                        validation = validate_session_handoff(state)
                        payload["handoff_validation"] = {
                            "errors": validation.errors,
                            "warnings": validation.warnings,
                        }
                        agent_name = (
                            session.agent_spec.name or "agent"
                        ).lower().replace(" ", "_")
                        ui.download(
                            json.dumps(payload, indent=2).encode(),
                            f"{agent_name}_handoff_session.json",
                        )

                    def import_session(e):
                        from grounded_evals.guide.session import Session

                        try:
                            payload = json.loads(e.content.read().decode())
                            session = Session.model_validate(payload["session"])
                        except Exception as exc:
                            ui.notify(f"Import failed: {exc}", type="negative")
                            return

                        storage = app.storage.user
                        storage["session_data"] = session.model_dump(mode="json")
                        storage["current_step"] = payload.get(
                            "current_step", session.current_step
                        )
                        storage["annotations"] = payload.get("annotations", [])
                        storage["messages"] = payload.get("messages", [])
                        storage["prompt_variants"] = payload.get("prompt_variants", [])
                        ui.notify("Session imported", type="positive")
                        dlg.close()
                        ui.navigate.to("/")

                    with ui.row().classes("gap-2 items-center"):
                        ui.button("Export", icon="download", on_click=export_session).props(
                            "size=sm outline dark"
                        )
                        ui.upload(
                            label="Import",
                            on_upload=import_session,
                            auto_upload=True,
                        ).props("accept=.json dense color=primary")

        with ui.row().classes("app-action-row items-center gap-xs"):
            ui.button(icon="refresh", on_click=confirm_new_project).props(
                "flat round size=sm"
            ).style("color: var(--text-muted)").tooltip("Reset project")

            ui.button(icon="ios_share", on_click=open_session_dialog).props(
                "flat round size=sm"
            ).style("color: var(--text-muted)").tooltip("Output bundle")

            ui.button(icon="logout", on_click=logout).props("flat round size=sm").style(
                "color: var(--text-muted)"
            ).tooltip("Logout")
