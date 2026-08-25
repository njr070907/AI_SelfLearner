"""Semantic Apple-inspired theme and accent tokens for the Streamlit UI."""

from collections.abc import Mapping

import streamlit as st

from ai_growth_companion.ui.state import AccentTheme, ThemeMode, UiPreferences

LIGHT_TOKENS = {
    "color-scheme": "light",
    "canvas": "#f3f6fb",
    "surface": "rgba(255, 255, 255, .88)",
    "surface-solid": "#fbfcfe",
    "surface-elevated": "#ffffff",
    "surface-muted": "#f0f4f9",
    "glass": "rgba(247, 250, 254, .72)",
    "glass-strong": "rgba(250, 252, 255, .86)",
    "ink": "#172033",
    "ink-soft": "#435169",
    "ink-muted": "#75839a",
    "line": "rgba(99, 120, 151, .16)",
    "line-strong": "rgba(91, 112, 143, .27)",
    "glass-highlight": "rgba(255, 255, 255, .78)",
    "shadow-raised": "0 18px 48px rgba(64, 83, 116, .09)",
    "shadow-floating": "0 18px 48px rgba(58, 77, 110, .14)",
    "success": "#247e61",
    "success-soft": "#e9f6f0",
    "warning": "#98691f",
    "warning-soft": "#fbf2e3",
    "danger": "#b64b4f",
    "danger-soft": "#fff0f1",
}

DARK_TOKENS = {
    "color-scheme": "dark",
    "canvas": "#10151d",
    "surface": "rgba(25, 32, 43, .9)",
    "surface-solid": "#171e28",
    "surface-elevated": "#1c2430",
    "surface-muted": "#202936",
    "glass": "rgba(20, 27, 37, .74)",
    "glass-strong": "rgba(25, 32, 43, .88)",
    "ink": "#f3f6fb",
    "ink-soft": "#c7d0de",
    "ink-muted": "#919eb0",
    "line": "rgba(179, 197, 224, .13)",
    "line-strong": "rgba(179, 197, 224, .23)",
    "glass-highlight": "rgba(255, 255, 255, .11)",
    "shadow-raised": "0 20px 52px rgba(0, 0, 0, .23)",
    "shadow-floating": "0 20px 56px rgba(0, 0, 0, .34)",
    "success": "#6bc4a4",
    "success-soft": "rgba(57, 143, 111, .18)",
    "warning": "#dfb568",
    "warning-soft": "rgba(171, 119, 42, .19)",
    "danger": "#f08d91",
    "danger-soft": "rgba(178, 66, 72, .18)",
}

ACCENT_TOKENS: Mapping[AccentTheme, Mapping[str, str]] = {
    AccentTheme.BLUE: {
        "accent": "#3b78ee",
        "accent-secondary": "#4d88f2",
        "accent-contrast": "#ffffff",
        "accent-soft": "rgba(59, 120, 238, .12)",
        "accent-soft-strong": "rgba(59, 120, 238, .18)",
        "focus-ring": "rgba(59, 120, 238, .34)",
        "glow-hover": "rgba(59, 120, 238, .3)",
        "glow-pressed": "rgba(59, 120, 238, .18)",
        "ambient-primary": "rgba(104, 165, 255, .18)",
        "ambient-secondary": "rgba(128, 186, 255, .08)",
        "glass-accent": "rgba(91, 151, 245, .08)",
    },
    AccentTheme.PURPLE: {
        "accent": "#795fdf",
        "accent-secondary": "#8a70e8",
        "accent-contrast": "#ffffff",
        "accent-soft": "rgba(121, 95, 223, .12)",
        "accent-soft-strong": "rgba(121, 95, 223, .18)",
        "focus-ring": "rgba(121, 95, 223, .34)",
        "glow-hover": "rgba(121, 95, 223, .29)",
        "glow-pressed": "rgba(121, 95, 223, .17)",
        "ambient-primary": "rgba(164, 132, 241, .17)",
        "ambient-secondary": "rgba(191, 157, 247, .08)",
        "glass-accent": "rgba(147, 115, 232, .08)",
    },
    AccentTheme.GREEN: {
        "accent": "#27856d",
        "accent-secondary": "#3c9a7f",
        "accent-contrast": "#ffffff",
        "accent-soft": "rgba(39, 133, 109, .12)",
        "accent-soft-strong": "rgba(39, 133, 109, .18)",
        "focus-ring": "rgba(39, 133, 109, .34)",
        "glow-hover": "rgba(39, 133, 109, .28)",
        "glow-pressed": "rgba(39, 133, 109, .17)",
        "ambient-primary": "rgba(91, 174, 143, .16)",
        "ambient-secondary": "rgba(130, 194, 165, .08)",
        "glass-accent": "rgba(67, 151, 122, .08)",
    },
    AccentTheme.BLUE_PURPLE: {
        "accent": "#3f76ee",
        "accent-secondary": "#7b65e8",
        "accent-contrast": "#ffffff",
        "accent-soft": "rgba(78, 103, 229, .12)",
        "accent-soft-strong": "rgba(78, 103, 229, .18)",
        "focus-ring": "rgba(74, 104, 235, .34)",
        "glow-hover": "rgba(84, 95, 227, .3)",
        "glow-pressed": "rgba(84, 95, 227, .18)",
        "ambient-primary": "rgba(104, 162, 255, .17)",
        "ambient-secondary": "rgba(170, 139, 245, .13)",
        "glass-accent": "rgba(111, 117, 236, .08)",
    },
    AccentTheme.GRAPHITE: {
        "accent": "#596577",
        "accent-secondary": "#727d8e",
        "accent-contrast": "#ffffff",
        "accent-soft": "rgba(83, 96, 115, .12)",
        "accent-soft-strong": "rgba(83, 96, 115, .18)",
        "focus-ring": "rgba(91, 106, 128, .34)",
        "glow-hover": "rgba(72, 85, 104, .25)",
        "glow-pressed": "rgba(72, 85, 104, .16)",
        "ambient-primary": "rgba(130, 145, 167, .13)",
        "ambient-secondary": "rgba(158, 169, 186, .07)",
        "glass-accent": "rgba(105, 119, 139, .07)",
    },
}

APP_CSS = """
<style>
:root {
  --radius-window: 24px;
  --radius-panel: 20px;
  --radius-control: 12px;
  --radius-small: 9px;
  --motion-fast: 160ms;
  --motion-normal: 240ms;
  --motion-page: 340ms;
  --motion-expand: 320ms;
  --motion-press: 90ms;
  --ease-standard: cubic-bezier(.22, .8, .25, 1);
  --ease-emphasized: cubic-bezier(.32, .72, 0, 1);
  --ease: var(--ease-standard);
  --sidebar-width: 268px;
  interpolate-size: allow-keywords;
}

/* One shared motion language: content rises softly and settles in layers.
   The container itself stays still; children carry the staggered entrance. */
@keyframes view-enter-soft {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: none; }
}
@keyframes view-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: none; }
}
@keyframes view-pop {
  from { opacity: 0; transform: translateY(-4px) scale(.985); }
  to { opacity: 1; transform: none; }
}
[class*="st-key-view-"] > * {
  animation: view-rise var(--motion-page) var(--ease-emphasized) both;
}
[class*="st-key-view-"] > :nth-child(2) { animation-delay: 40ms; }
[class*="st-key-view-"] > :nth-child(3) { animation-delay: 80ms; }
[class*="st-key-view-"] > :nth-child(4) { animation-delay: 120ms; }
[class*="st-key-view-"] > :nth-child(5) { animation-delay: 160ms; }
[class*="st-key-view-"] > :nth-child(n + 6) { animation-delay: 160ms; }

html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
html { background: var(--canvas); color-scheme: var(--color-scheme); }
body { color: var(--ink); }
html { scrollbar-color: color-mix(in srgb, var(--ink-muted) 38%, transparent) transparent; }
[data-testid="stAppViewContainer"] ::-webkit-scrollbar { width: 10px; height: 10px; }
[data-testid="stAppViewContainer"] ::-webkit-scrollbar-thumb {
  border: 3px solid transparent;
  border-radius: 8px;
  background: color-mix(in srgb, var(--ink-muted) 34%, transparent);
  background-clip: padding-box;
}
[data-testid="stAppViewContainer"] ::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--ink-muted) 55%, transparent);
  background-clip: padding-box;
}
[data-testid="stAppViewContainer"] ::-webkit-scrollbar-track { background: transparent; }
[data-testid="stAppViewContainer"] {
  background-color: var(--canvas);
  background-image:
    radial-gradient(ellipse 58% 46% at -10% -8%, var(--ambient-primary), transparent 72%),
    radial-gradient(ellipse 46% 42% at 108% 22%, var(--ambient-secondary), transparent 75%);
  background-attachment: fixed;
  transition: background-color var(--motion-normal) var(--ease);
}
[data-testid="stHeader"] { background: transparent; pointer-events: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stMainBlockContainer"] {
  max-width: 1160px;
  padding: 1.05rem 3.6rem 6rem;
}

/* Persistent Liquid Glass application chrome. */
[data-testid="stSidebar"] {
  top: 12px;
  left: 12px;
  width: var(--sidebar-width) !important;
  min-width: var(--sidebar-width) !important;
  height: calc(100vh - 24px) !important;
  border: 1px solid var(--line);
  border-radius: var(--radius-window);
  background:
    linear-gradient(145deg, var(--glass-highlight), transparent 24%),
    linear-gradient(135deg, var(--glass-accent), transparent 58%),
    var(--glass);
  box-shadow: var(--shadow-floating), inset 0 1px 0 var(--glass-highlight);
  -webkit-backdrop-filter: saturate(1.18) blur(24px);
  backdrop-filter: saturate(1.18) blur(24px);
  overflow: hidden;
  transition: width var(--motion-normal) var(--ease), min-width var(--motion-normal) var(--ease),
    background-color var(--motion-normal) var(--ease),
    border-color var(--motion-normal) var(--ease);
}
[data-testid="stSidebarContent"] { padding: 1.2rem 1rem 1rem; }
[data-testid="stSidebarCollapseButton"] { display: none; }

.brand {
  display: flex;
  align-items: center;
  gap: .72rem;
  min-height: 38px;
  margin: .15rem .45rem .55rem;
  color: var(--ink);
  font-size: .96rem;
  font-weight: 735;
  letter-spacing: -.025em;
  white-space: nowrap;
}
.brand-mark {
  display: inline-grid;
  flex: 0 0 34px;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: var(--accent-contrast);
  box-shadow: 0 9px 24px var(--glow-hover), inset 0 1px 0 rgba(255, 255, 255, .34);
  font-size: .78rem;
  font-weight: 800;
}
.nav-section-label {
  margin: 1.2rem .72rem .42rem;
  color: var(--ink-muted);
  font-size: .68rem;
  font-weight: 720;
  letter-spacing: .09em;
  text-transform: uppercase;
}
.st-key-sidebar_toggle button,
[class*="st-key-nav_"] button {
  justify-content: flex-start;
  width: 100%;
  min-height: 44px;
  padding: .55rem .72rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--ink-soft);
  box-shadow: none;
  transition: background-color var(--motion-fast) var(--ease),
    border-color var(--motion-fast) var(--ease),
    box-shadow var(--motion-normal) var(--ease), transform var(--motion-press) ease-out;
}
.st-key-sidebar_toggle button { color: var(--ink-muted); }
.st-key-sidebar_toggle button:hover,
[class*="st-key-nav_"] button:hover {
  border-color: var(--line);
  background: color-mix(in srgb, var(--glass-strong) 78%, var(--accent-soft));
  color: var(--ink);
  box-shadow: 0 8px 22px color-mix(in srgb, var(--glow-hover) 35%, transparent);
}
[class*="st-key-nav_"] button[kind="primary"] {
  border-color: color-mix(in srgb, var(--accent) 22%, var(--line));
  background: var(--accent-soft-strong);
  color: var(--accent);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--accent-contrast) 26%, transparent),
    0 8px 22px color-mix(in srgb, var(--glow-hover) 36%, transparent);
}
[class*="st-key-nav_"] button p,
.st-key-sidebar_toggle button p {
  color: currentColor !important;
  font-size: .9rem;
  font-weight: 650;
}
[class*="st-key-nav_"] button:active,
.st-key-sidebar_toggle button:active { transform: translateY(1px) scale(.992); }

.sidebar-status {
  display: flex;
  align-items: flex-start;
  gap: .55rem;
  margin: 2rem .55rem 0;
  padding: 1rem .1rem 0;
  border-top: 1px solid var(--line);
  color: var(--ink-muted);
  font-size: .73rem;
  line-height: 1.65;
}
.status-dot {
  flex: 0 0 7px;
  width: 7px;
  height: 7px;
  margin-top: .35rem;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 4px var(--success-soft);
}

body:has(.sidebar-collapse-marker) [data-testid="stSidebar"] {
  --sidebar-width: 88px;
}
body:has(.sidebar-collapse-marker) [data-testid="stSidebarContent"] { padding-inline: .72rem; }
body:has(.sidebar-collapse-marker) .brand { justify-content: center; margin-inline: 0; }
body:has(.sidebar-collapse-marker) .brand-copy,
body:has(.sidebar-collapse-marker) .nav-section-label,
body:has(.sidebar-collapse-marker) .sidebar-status-copy,
body:has(.sidebar-collapse-marker) [class*="st-key-nav_"] button p,
body:has(.sidebar-collapse-marker) .st-key-sidebar_toggle button p { display: none; }
body:has(.sidebar-collapse-marker) [class*="st-key-nav_"] button,
body:has(.sidebar-collapse-marker) .st-key-sidebar_toggle button {
  justify-content: center;
  min-width: 44px;
  padding-inline: 0;
}
body:has(.sidebar-collapse-marker) .sidebar-status {
  justify-content: center;
  margin-inline: .2rem;
  padding-inline: 0;
}

.st-key-app_toolbar {
  position: sticky;
  top: .75rem;
  z-index: 900;
  isolation: isolate;
  margin: 0 0 2.8rem;
  padding: .58rem .62rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
  background:
    linear-gradient(150deg, var(--glass-highlight), transparent 30%),
    linear-gradient(110deg, var(--glass-accent), transparent 54%),
    var(--glass);
  box-shadow: var(--shadow-floating), inset 0 1px 0 var(--glass-highlight);
  -webkit-backdrop-filter: saturate(1.2) blur(22px);
  backdrop-filter: saturate(1.2) blur(22px);
  transition: background-color var(--motion-normal) var(--ease),
    border-color var(--motion-normal) var(--ease);
}
.st-key-app_toolbar::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: radial-gradient(circle at 68% -40%, var(--accent-soft), transparent 44%);
  pointer-events: none;
}
/* Pointer-aware ambient glow: follows the cursor, fades in only while hovering. */
.st-key-app_toolbar::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: radial-gradient(
    240px circle at var(--glow-x, 50%) var(--glow-y, -30%),
    color-mix(in srgb, var(--glow-hover) 42%, transparent),
    transparent 72%
  );
  opacity: 0;
  transition: opacity var(--motion-normal) var(--ease);
  pointer-events: none;
}
.st-key-app_toolbar:hover::after { opacity: 1; }
.toolbar-location {
  display: flex;
  align-items: center;
  gap: .55rem;
  min-height: 42px;
  padding-inline: .65rem;
  color: var(--ink);
  font-size: .84rem;
  font-weight: 680;
  white-space: nowrap;
}
.toolbar-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-soft);
}
.st-key-app_toolbar [data-baseweb="base-input"],
.st-key-app_toolbar [data-baseweb="select"] > div,
.st-key-app_toolbar .react-aria-ComboBox [role="group"] {
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--glass-strong) 84%, var(--glass-accent));
  box-shadow: inset 0 1px 0 var(--glass-highlight), 0 4px 14px rgba(50, 68, 98, .05);
  transition: border-color var(--motion-fast) var(--ease),
    box-shadow var(--motion-normal) var(--ease), background-color var(--motion-fast) var(--ease);
}
.st-key-app_toolbar [data-testid="stTextInputRootElement"],
.st-key-app_toolbar [data-baseweb="select"] > div,
.st-key-app_toolbar .react-aria-ComboBox [role="group"] {
  border-color: var(--line) !important;
  background: color-mix(in srgb, var(--glass-strong) 84%, var(--glass-accent)) !important;
  color: var(--ink) !important;
}
.st-key-app_toolbar [data-baseweb="select"] [role="combobox"],
.st-key-app_toolbar [data-baseweb="select"] p,
.st-key-app_toolbar [data-baseweb="select"] svg,
.st-key-app_toolbar .react-aria-ComboBox input[role="combobox"],
.st-key-app_toolbar .react-aria-ComboBox button {
  color: var(--ink-soft) !important;
}
.st-key-app_toolbar [data-baseweb="base-input"]:hover,
.st-key-app_toolbar [data-baseweb="select"] > div:hover,
.st-key-app_toolbar .react-aria-ComboBox [role="group"]:hover {
  border-color: color-mix(in srgb, var(--accent) 30%, var(--line-strong));
  box-shadow: inset 0 1px 0 var(--glass-highlight),
    0 7px 20px color-mix(in srgb, var(--glow-hover) 22%, transparent);
}
.st-key-app_toolbar [data-baseweb="base-input"]:has(input:focus),
.st-key-app_toolbar [data-testid="stTextInputRootElement"]:focus-within,
.st-key-app_toolbar [data-baseweb="select"] > div:focus-within,
.st-key-app_toolbar .react-aria-ComboBox [role="group"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--focus-ring),
    0 10px 26px color-mix(in srgb, var(--glow-hover) 42%, transparent),
    inset 0 1px 0 var(--glass-highlight);
}
.st-key-theme_toggle button {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--glass-strong) 88%, var(--glass-accent));
  color: var(--ink-soft);
  box-shadow: inset 0 1px 0 var(--glass-highlight);
}
.st-key-theme_toggle button:hover {
  border-color: color-mix(in srgb, var(--accent) 28%, var(--line-strong));
  color: var(--ink);
  box-shadow: 0 7px 20px color-mix(in srgb, var(--glow-hover) 22%, transparent),
    inset 0 1px 0 var(--glass-highlight);
}
.st-key-theme_toggle button p { color: currentColor !important; font-size: .8rem; }

.st-key-search_results {
  position: relative;
  z-index: 850;
  margin: -2rem 0 2.6rem;
  padding: 1rem 1.15rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
  background: var(--glass-strong);
  box-shadow: var(--shadow-floating), inset 0 1px 0 var(--glass-highlight);
  -webkit-backdrop-filter: saturate(1.15) blur(18px);
  backdrop-filter: saturate(1.15) blur(18px);
  animation: view-enter-soft var(--motion-normal) var(--ease-emphasized) both;
}
.search-results-title {
  margin: .1rem 0 .65rem;
  color: var(--ink);
  font-size: .82rem;
  font-weight: 700;
}
.search-results-title span { margin-left: .3rem; color: var(--ink-muted); font-weight: 560; }
.search-result-row { display: flex; flex-direction: column; gap: .18rem; padding: .48rem .35rem; }
.search-result-row strong { color: var(--ink); font-size: .88rem; }
.search-result-row span { color: var(--ink-muted); font-size: .76rem; }
.st-key-search_results .stButton button { min-height: 38px; border-color: var(--line); }

h1, h2, h3,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
  color: var(--ink) !important;
  letter-spacing: -.035em;
}
p, li { color: var(--ink-soft); }
.hero-title {
  max-width: 820px;
  margin: .2rem 0 .8rem;
  font-size: clamp(2.45rem, 5vw, 4.15rem);
  line-height: 1.03;
  font-weight: 730;
  letter-spacing: -.055em;
}
.hero-title a { display: none; }
.hero-copy {
  max-width: 670px;
  margin: 0 0 2.4rem;
  color: var(--ink-muted);
  font-size: 1.03rem;
  line-height: 1.8;
}
.eyebrow, .section-label, .question-kicker {
  color: var(--accent);
  font-size: .73rem;
  font-weight: 750;
  letter-spacing: .085em;
  text-transform: uppercase;
}
.section-label { margin: 0 0 .8rem; }
.rule { height: 1px; margin: 2.7rem 0; background: var(--line); }

/* Reading and task surfaces remain opaque. */
.empty-state, .question-panel, .diagnosis-panel,
.progress-row, .status-row, [data-testid="stForm"] {
  background: var(--surface-solid);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-raised);
  transition: border-color var(--motion-fast) var(--ease),
    box-shadow var(--motion-normal) var(--ease), transform var(--motion-fast) var(--ease);
}
@media (hover: hover) and (pointer: fine) {
  /* Layered, restrained card response: border light, deeper shadow, no scale. */
  .empty-state:hover, .question-panel:hover, .diagnosis-panel:hover, [data-testid="stForm"]:hover {
    border-color: color-mix(in srgb, var(--accent) 15%, var(--line-strong));
    box-shadow: var(--shadow-raised), 0 0 0 1px var(--accent-soft),
      0 22px 52px color-mix(in srgb, var(--glow-hover) 12%, transparent);
  }
  .progress-row:hover, .status-row:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--accent) 16%, var(--line-strong));
    box-shadow: 0 14px 34px color-mix(in srgb, var(--glow-hover) 16%, rgba(50, 68, 98, .08)),
      inset 0 1px 0 var(--glass-highlight);
  }
}
.empty-state {
  max-width: 760px;
  padding: 2.25rem;
  margin: 1rem 0 1.2rem;
  border-radius: var(--radius-panel);
}
.empty-state h2 { margin: .5rem 0; font-size: 1.55rem; }
.empty-state p { max-width: 590px; margin: 0; color: var(--ink-muted); line-height: 1.75; }
.question-panel {
  padding: 1.5rem 1.65rem;
  margin: 1.2rem 0 1.5rem;
  border-radius: 16px;
}
.question-panel p { margin: .7rem 0 0; color: var(--ink); font-size: 1.12rem; line-height: 1.65; }
[data-testid="stForm"] { padding: 1.55rem; border-radius: var(--radius-panel); }

.diagnosis-panel {
  overflow: hidden;
  margin: 1.2rem 0 1.5rem;
  border-radius: var(--radius-panel);
  animation: view-enter-soft var(--motion-normal) var(--ease-emphasized) both;
}
.diagnosis-head { padding: 1.75rem 1.85rem 1.45rem; }
.diagnosis-head h2 { margin: .6rem 0 .35rem; font-size: 1.7rem; }
.diagnosis-head p { margin: 0; color: var(--ink-muted); line-height: 1.65; }
.diagnosis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.diagnosis-cell { padding: 1.55rem 1.85rem; }
.diagnosis-cell + .diagnosis-cell { border-left: 1px solid var(--line); }
.diagnosis-cell h3 { margin: 0 0 .8rem; font-size: .98rem; letter-spacing: -.01em; }
.diagnosis-cell ul { margin: 0; padding-left: 1.1rem; }
.diagnosis-cell li { margin: .48rem 0; line-height: 1.55; }
.next-step { padding: 1.55rem 1.85rem 1.7rem; background: var(--accent-soft); }
.next-step strong { color: var(--ink); font-size: 1rem; }
.next-step p { margin: .35rem 0 0; color: var(--ink-soft); }

.badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 26px;
  padding: .25rem .64rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: .74rem;
  font-weight: 740;
}
.badge-warn { background: var(--warning-soft); color: var(--warning); }
.badge-good { background: var(--success-soft); color: var(--success); }
.badge-danger { background: var(--danger-soft); color: var(--danger); }
.progress-row, .status-row {
  display: grid;
  align-items: center;
  gap: 1rem;
  margin: .65rem 0;
  padding: 1rem 1.15rem;
  border-radius: 15px;
  box-shadow: none;
}
.progress-row { grid-template-columns: minmax(180px, 1.4fr) .7fr 1fr 1fr; }
.status-row { grid-template-columns: minmax(150px, .75fr) 1fr auto; }
.row-title { color: var(--ink); font-weight: 680; }
.row-meta { color: var(--ink-muted); font-size: .84rem; line-height: 1.55; }
.error-panel {
  margin: 1rem 0;
  padding: 1.35rem 1.5rem;
  border: 1px solid color-mix(in srgb, var(--danger) 28%, transparent);
  border-left: 4px solid var(--danger);
  border-radius: 15px;
  background: var(--danger-soft);
}
.error-panel h3 { margin: 0 0 .35rem; color: var(--danger); }
.error-panel p { margin: 0; color: var(--ink-soft); }

/* Important actions share one accent-aware light contract. */
.stMain .stButton button, .stMain .stFormSubmitButton button {
  min-height: 44px;
  border-radius: var(--radius-control);
  font-weight: 680;
  transition: background-color var(--motion-fast) var(--ease),
    border-color var(--motion-fast) var(--ease),
    box-shadow var(--motion-normal) var(--ease), transform var(--motion-press) ease-out;
}
.stMain .stButton button[kind="primary"],
.stMain .stFormSubmitButton button[kind^="primary"] {
  position: relative;
  overflow: hidden;
  border-color: color-mix(in srgb, var(--accent) 72%, transparent);
  background: linear-gradient(112deg, var(--accent), var(--accent-secondary));
  color: var(--accent-contrast);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .32),
    0 3px 10px color-mix(in srgb, var(--glow-hover) 40%, transparent);
}
/* Same pointer-aware light as the toolbar, derived from the live accent. */
.stMain .stButton button[kind="primary"]::after,
.stMain .stFormSubmitButton button[kind^="primary"]::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    130px circle at var(--glow-x, 50%) var(--glow-y, 120%),
    color-mix(in srgb, var(--accent-contrast) 30%, transparent),
    transparent 72%
  );
  opacity: 0;
  transition: opacity var(--motion-normal) var(--ease);
  pointer-events: none;
}
.stMain .stButton button[kind="primary"]:not(:disabled):hover::after,
.stMain .stFormSubmitButton button[kind^="primary"]:not(:disabled):hover::after { opacity: 1; }
.stMain .stButton button[kind="primary"] p,
.stMain .stFormSubmitButton button[kind^="primary"] p { color: var(--accent-contrast) !important; }
@media (hover: hover) and (pointer: fine) {
  .stMain .stButton button[kind="primary"]:not(:disabled):hover,
  .stMain .stFormSubmitButton button[kind^="primary"]:not(:disabled):hover {
    border-color: color-mix(in srgb, var(--accent-contrast) 36%, var(--accent));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .48),
      0 11px 30px var(--glow-hover), 0 0 0 1px var(--accent-soft);
    filter: brightness(1.035) saturate(1.03);
  }
  .stMain .stButton button[kind="tertiary"]:not(:disabled):hover {
    border-color: var(--line);
    background: color-mix(in srgb, var(--glass-strong) 78%, var(--accent-soft));
    color: var(--ink);
    box-shadow: 0 8px 22px color-mix(in srgb, var(--glow-hover) 30%, transparent);
  }
}
.stMain .stButton button:active,
.stMain .stFormSubmitButton button:active {
  transform: translateY(1px) scale(.992);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, .13), 0 4px 12px var(--glow-pressed);
}
.stButton button:focus-visible, .stFormSubmitButton button:focus-visible,
input:focus-visible, textarea:focus-visible, [role="combobox"]:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--focus-ring);
}
.stButton > button:disabled { filter: saturate(.35); opacity: .58; }
[data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
  border-color: var(--line-strong);
  border-radius: var(--radius-control);
  background: var(--surface-elevated);
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-baseweb="input"]:has(input:focus),
[data-baseweb="textarea"]:has(textarea:focus),
.react-aria-ComboBox [role="group"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--focus-ring) !important;
}
input, textarea { color: var(--ink) !important; caret-color: var(--accent); }
[data-testid="stExpander"] {
  overflow: hidden;
  border-color: var(--line);
  border-radius: 15px;
  background: var(--surface-solid);
}
/* Unfold like a soft-cover folder: geometry leads, content gently follows. */
[data-testid="stExpander"] details::details-content {
  block-size: 0;
  overflow: clip;
  transition:
    block-size var(--motion-expand) var(--ease-emphasized),
    content-visibility var(--motion-expand) allow-discrete;
}
[data-testid="stExpander"] details[open]::details-content { block-size: auto; }
[data-testid="stExpander"] details[open] [data-testid="stExpanderDetails"] {
  animation: view-enter-soft var(--motion-expand) var(--ease-standard) 40ms both;
}
[data-testid="stSelectboxVirtualDropdown"] {
  animation: view-pop var(--motion-fast) var(--ease-standard) both;
  transform-origin: top;
}
[data-testid="stAlert"] { border-radius: 15px; }

@media (max-width: 980px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem 2rem 5rem; }
  .hero-title { font-size: clamp(2.25rem, 6vw, 3.4rem); }
  .progress-row { grid-template-columns: minmax(180px, 1.4fr) 1fr 1fr; }
  .progress-row > :last-child { grid-column: 3; }
  .st-key-app_toolbar [data-testid="stColumn"]:first-child { display: none; }
  [data-testid="stSidebar"] { --sidebar-width: 88px; }
  [data-testid="stSidebarContent"] { padding-inline: .72rem; }
  .brand { justify-content: center; margin-inline: 0; }
  .brand-copy, .nav-section-label, .sidebar-status-copy,
  [class*="st-key-nav_"] button p,
  .st-key-sidebar_toggle button p { display: none; }
  [class*="st-key-nav_"] button,
  .st-key-sidebar_toggle button {
    justify-content: center;
    min-width: 44px;
    padding-inline: 0;
  }
  .sidebar-status { justify-content: center; margin-inline: .2rem; padding-inline: 0; }
}

@media (max-width: 760px) {
  [data-testid="stAppViewContainer"] {
    background-image:
      radial-gradient(ellipse 96% 32% at 0 -5%, var(--ambient-primary), transparent 76%),
      radial-gradient(ellipse 78% 28% at 112% 19%, var(--ambient-secondary), transparent 80%);
  }
  [data-testid="stHeader"] {
    min-height: 3.5rem;
    border-bottom: 1px solid var(--line);
    background: var(--glass);
    pointer-events: auto;
    -webkit-backdrop-filter: saturate(1.12) blur(16px);
    backdrop-filter: saturate(1.12) blur(16px);
  }
  [data-testid="stSidebar"] {
    top: 0;
    left: 0;
    width: min(300px, 100vw) !important;
    min-width: min(300px, 100vw) !important;
    height: 100vh !important;
    border-radius: 0 22px 22px 0;
  }
  [data-testid="stSidebarCollapseButton"] { display: flex; }
  .brand-copy, .nav-section-label, .sidebar-status-copy,
  [class*="st-key-nav_"] button p,
  .st-key-sidebar_toggle button p { display: initial; }
  [class*="st-key-nav_"] button,
  .st-key-sidebar_toggle button { justify-content: flex-start; padding-inline: .72rem; }
  .brand { justify-content: flex-start; margin-inline: .45rem; }
  .sidebar-status { justify-content: flex-start; margin-inline: .55rem; }
  body:has(.sidebar-collapse-marker) .brand-copy,
  body:has(.sidebar-collapse-marker) .nav-section-label,
  body:has(.sidebar-collapse-marker) .sidebar-status-copy,
  body:has(.sidebar-collapse-marker) [class*="st-key-nav_"] button p,
  body:has(.sidebar-collapse-marker) .st-key-sidebar_toggle button p { display: initial; }
  body:has(.sidebar-collapse-marker) [class*="st-key-nav_"] button,
  body:has(.sidebar-collapse-marker) .st-key-sidebar_toggle button {
    justify-content: flex-start;
    padding-inline: .72rem;
  }
  body:has(.sidebar-collapse-marker) .brand { justify-content: flex-start; margin-inline: .45rem; }
  body:has(.sidebar-collapse-marker) .sidebar-status {
    justify-content: flex-start;
    margin-inline: .55rem;
  }
  [data-testid="stMainBlockContainer"] { padding: 4.35rem 1rem 4rem; }
  .st-key-app_toolbar {
    top: .55rem;
    margin-bottom: 2.1rem;
    padding: .5rem;
    border-radius: 17px;
    -webkit-backdrop-filter: saturate(1.12) blur(16px);
    backdrop-filter: saturate(1.12) blur(16px);
  }
  .st-key-app_toolbar [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .45rem; }
  .st-key-app_toolbar [data-testid="stColumn"] { min-width: 0; }
  .st-key-app_toolbar [data-testid="stColumn"]:first-child { display: none; }
  .st-key-app_toolbar [data-testid="stColumn"]:nth-child(2) { flex: 1 1 100%; width: 100%; }
  .st-key-app_toolbar [data-testid="stColumn"]:nth-child(3) { flex: 1 1 34%; width: auto; }
  .st-key-app_toolbar [data-testid="stColumn"]:nth-child(4) { flex: 1 1 58%; width: auto; }
  .hero-title { font-size: clamp(2.15rem, 11vw, 3rem); line-height: 1.05; }
  .hero-copy { margin-bottom: 1.8rem; font-size: .97rem; line-height: 1.7; }
  .empty-state, .question-panel, .diagnosis-head, .diagnosis-cell, .next-step {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }
  .diagnosis-grid { grid-template-columns: 1fr; }
  .diagnosis-cell + .diagnosis-cell { border-top: 1px solid var(--line); border-left: 0; }
  .progress-row { grid-template-columns: 1fr 1fr; gap: .8rem; }
  .progress-row > :last-child { grid-column: auto; }
  .status-row { grid-template-columns: 1fr; gap: .35rem; }
  .stMain .stButton button,
  .stMain .stFormSubmitButton button { width: 100%; min-height: 48px; }
  .rule { margin: 2.2rem 0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
    transition-delay: .01ms !important;
    animation-duration: .01ms !important;
    animation-delay: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}
@media (prefers-contrast: more) {
  :root { --line: rgba(105, 124, 151, .52); --line-strong: rgba(88, 106, 134, .74); }
}
@media (prefers-reduced-transparency: reduce) {
  [data-testid="stSidebar"], .st-key-app_toolbar, .st-key-search_results,
  [data-testid="stHeader"] {
    background: var(--surface-elevated);
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
  }
}
</style>
"""


def token_css(preferences: UiPreferences) -> str:
    """Return complete light/dark and accent tokens for one UI state."""
    tokens = dict(LIGHT_TOKENS if preferences.theme is ThemeMode.LIGHT else DARK_TOKENS)
    tokens.update(ACCENT_TOKENS[preferences.accent])
    declarations = "\n".join(f"  --{name}: {value};" for name, value in tokens.items())
    return f"<style>\n:root {{\n{declarations}\n}}\n</style>"


def design_system_css(preferences: UiPreferences) -> str:
    return f"{token_css(preferences)}\n{APP_CSS}"


def apply_design_system(preferences: UiPreferences) -> None:
    """Apply stable semantic tokens before rendering the persistent shell."""
    st.markdown(design_system_css(preferences), unsafe_allow_html=True)
