"""Apple-inspired visual baseline shared by all Streamlit pages."""

import streamlit as st

APP_CSS = """
<style>
:root {
  color-scheme: light dark;
  --canvas: #f3f6fb;
  --surface: rgba(255, 255, 255, .9);
  --surface-solid: #fbfcfe;
  --surface-muted: #f3f6fa;
  --glass: rgba(246, 249, 253, .74);
  --ink: #152033;
  --ink-soft: #3d4b62;
  --ink-muted: #718097;
  --line: rgba(105, 125, 154, .18);
  --line-strong: rgba(92, 112, 142, .28);
  --accent: #3773e8;
  --accent-2: #7067e8;
  --accent-soft: rgba(74, 112, 232, .1);
  --success: #248362;
  --success-soft: #eaf7f1;
  --warning: #9a6924;
  --warning-soft: #fbf3e6;
  --danger: #b74b4d;
  --danger-soft: #fff1f1;
  --ambient-blue: rgba(116, 171, 255, .18);
  --ambient-violet: rgba(171, 151, 255, .13);
  --radius-lg: 22px;
  --radius-md: 15px;
  --radius-sm: 11px;
  --shadow-soft: 0 20px 55px rgba(70, 89, 121, .09);
  --focus: 0 0 0 3px rgba(55, 115, 232, .24);
  --ease: cubic-bezier(.22, .8, .25, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --canvas: #0d1118;
    --surface: rgba(25, 31, 42, .92);
    --surface-solid: #171d27;
    --surface-muted: #1b222e;
    --glass: rgba(18, 24, 34, .74);
    --ink: #f1f4fa;
    --ink-soft: #c8d0dd;
    --ink-muted: #929fb1;
    --line: rgba(176, 195, 223, .13);
    --line-strong: rgba(176, 195, 223, .22);
    --accent: #6798ff;
    --accent-2: #9687ff;
    --accent-soft: rgba(104, 143, 255, .14);
    --success: #6cc7a6;
    --success-soft: rgba(62, 146, 116, .17);
    --warning: #e2b867;
    --warning-soft: rgba(181, 127, 46, .18);
    --danger: #f28d90;
    --danger-soft: rgba(184, 70, 74, .17);
    --ambient-blue: rgba(62, 117, 211, .2);
    --ambient-violet: rgba(113, 81, 197, .16);
    --shadow-soft: 0 22px 60px rgba(0, 0, 0, .22);
  }
}

html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
    "SF Pro Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
html { background: var(--canvas); }
body { color: var(--ink); }
[data-testid="stAppViewContainer"] {
  background-color: var(--canvas);
  background-image:
    radial-gradient(ellipse 55% 44% at -8% -6%, var(--ambient-blue), transparent 70%),
    radial-gradient(ellipse 45% 40% at 108% 25%, var(--ambient-violet), transparent 74%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1.2rem; }
[data-testid="stMainBlockContainer"] {
  max-width: 1120px;
  padding: 4.3rem 3.5rem 6rem;
}

/* Glass is reserved for navigation chrome. */
[data-testid="stSidebar"] {
  background: var(--glass);
  border-right: 1px solid var(--line);
  box-shadow: 10px 0 38px rgba(63, 82, 113, .05);
  -webkit-backdrop-filter: saturate(1.15) blur(22px);
  backdrop-filter: saturate(1.15) blur(22px);
}
[data-testid="stSidebarContent"] { padding: 1.7rem 1rem 1.4rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .32rem; }
[data-testid="stSidebar"] label[data-baseweb="radio"] {
  min-height: 44px;
  padding: .66rem .8rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
  min-height: 44px;
  padding: .66rem .8rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
  background: rgba(255, 255, 255, .35);
  border-color: var(--line);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
  background: rgba(255, 255, 255, .35);
  border-color: var(--line);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
  background: var(--surface);
  border-color: var(--line);
  box-shadow: 0 8px 22px rgba(67, 86, 117, .08);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
  background: var(--surface);
  border-color: var(--line);
  box-shadow: 0 8px 22px rgba(67, 86, 117, .08);
}
[data-testid="stSidebar"] label[data-baseweb="radio"] p {
  color: var(--ink-soft);
  font-size: .92rem;
  font-weight: 620;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
  color: var(--ink-soft);
  font-size: .92rem;
  font-weight: 620;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p { color: var(--ink); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
  color: var(--ink);
}
[data-testid="stSidebar"] input[type="radio"] { accent-color: var(--accent); }
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
  background-color: var(--accent);
  border-color: var(--accent);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) input + div {
  background-color: var(--accent);
  border-color: var(--accent);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]
  > div > div > div:first-child {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}

.brand {
  display: flex;
  align-items: center;
  gap: .68rem;
  color: var(--ink);
  font-size: .98rem;
  font-weight: 760;
  letter-spacing: -.02em;
  margin: .15rem .35rem 1.65rem;
}
.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border-radius: 9px;
  background: linear-gradient(145deg, var(--accent), var(--accent-2));
  color: white;
  box-shadow: 0 8px 20px rgba(72, 102, 224, .2);
  font-size: .82rem;
  font-weight: 800;
}
.sidebar-status {
  margin: 2rem .35rem 0;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
  color: var(--ink-muted);
  font-size: .76rem;
  line-height: 1.65;
}
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: .45rem;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 4px var(--success-soft);
}

h1, h2, h3 { color: var(--ink); letter-spacing: -.035em; }
p, li { color: var(--ink-soft); }
.hero-title {
  max-width: 820px;
  margin: .2rem 0 .8rem;
  font-size: clamp(2.45rem, 5vw, 4.2rem);
  line-height: 1.03;
  font-weight: 730;
  letter-spacing: -.055em;
}
.hero-copy {
  max-width: 670px;
  margin: 0 0 2.4rem;
  color: var(--ink-muted);
  font-size: 1.04rem;
  line-height: 1.8;
}
.eyebrow, .section-label, .question-kicker {
  color: var(--accent);
  font-size: .74rem;
  font-weight: 760;
  letter-spacing: .09em;
  text-transform: uppercase;
}
.section-label { margin: 0 0 .8rem; }
.rule { height: 1px; margin: 2.7rem 0; background: var(--line); }

/* Reading and task surfaces stay opaque and calm. */
.empty-state, .question-panel, .diagnosis-panel,
.progress-row, .status-row, [data-testid="stForm"] {
  background: var(--surface-solid);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-soft);
}
.empty-state {
  max-width: 760px;
  padding: 2.25rem;
  margin: 1rem 0 1.2rem;
  border-radius: var(--radius-lg);
}
.empty-state h2 { margin: .5rem 0; font-size: 1.55rem; }
.empty-state p { max-width: 590px; margin: 0; color: var(--ink-muted); line-height: 1.75; }
.question-panel {
  padding: 1.5rem 1.65rem;
  margin: 1.2rem 0 1.5rem;
  border-radius: var(--radius-md);
}
.question-panel p { margin: .7rem 0 0; color: var(--ink); font-size: 1.12rem; line-height: 1.65; }
[data-testid="stForm"] { padding: 1.55rem; border-radius: var(--radius-lg); }

.diagnosis-panel {
  overflow: hidden;
  margin: 1.2rem 0 1.5rem;
  border-radius: var(--radius-lg);
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
  border-radius: var(--radius-md);
  box-shadow: none;
}
.progress-row { grid-template-columns: minmax(180px, 1.4fr) .7fr 1fr 1fr; }
.status-row { grid-template-columns: minmax(150px, .75fr) 1fr auto; }
.row-title { color: var(--ink); font-weight: 680; }
.row-meta { color: var(--ink-muted); font-size: .84rem; line-height: 1.55; }
.error-panel {
  margin: 1rem 0;
  padding: 1.35rem 1.5rem;
  border: 1px solid rgba(183, 75, 77, .25);
  border-left: 4px solid var(--danger);
  border-radius: var(--radius-md);
  background: var(--danger-soft);
}
.error-panel h3 { margin: 0 0 .35rem; color: var(--danger); }
.error-panel p { margin: 0; color: var(--ink-soft); }

.stButton > button, .stFormSubmitButton > button {
  min-height: 44px;
  border-radius: var(--radius-sm);
  font-weight: 680;
  box-shadow: none;
  transition: background-color 150ms var(--ease), border-color 150ms var(--ease),
    box-shadow 170ms var(--ease), transform 90ms ease-out;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  border-color: transparent;
  background: linear-gradient(112deg, var(--accent), var(--accent-2));
  color: white;
}
.stButton > button[kind="primary"] p,
.stFormSubmitButton > button[kind="primary"] p { color: white !important; }
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
  border-color: transparent;
  box-shadow: 0 10px 26px rgba(72, 104, 230, .24);
  filter: brightness(1.045);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: scale(.99); }
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible,
input:focus-visible, textarea:focus-visible, [role="combobox"]:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
.stButton > button:disabled { filter: saturate(.35); opacity: .58; }
[data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
  border-color: var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-solid);
}
input, textarea { color: var(--ink) !important; caret-color: var(--accent); }
[data-testid="stExpander"] {
  overflow: hidden;
  border-color: var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-solid);
}
[data-testid="stAlert"] { border-radius: var(--radius-md); }

@media (max-width: 980px) {
  [data-testid="stMainBlockContainer"] { padding: 3.7rem 2.2rem 5rem; }
  .hero-title { font-size: clamp(2.25rem, 6vw, 3.4rem); }
  .progress-row { grid-template-columns: minmax(180px, 1.4fr) 1fr 1fr; }
  .progress-row > :last-child { grid-column: 3; }
}

@media (max-width: 760px) {
  [data-testid="stAppViewContainer"] {
    background-image:
      radial-gradient(ellipse 95% 30% at 0 -4%, var(--ambient-blue), transparent 74%),
      radial-gradient(ellipse 75% 25% at 110% 20%, var(--ambient-violet), transparent 78%);
  }
  [data-testid="stHeader"] {
    min-height: 3.6rem;
    border-bottom: 1px solid var(--line);
    background: var(--glass);
    -webkit-backdrop-filter: saturate(1.1) blur(18px);
    backdrop-filter: saturate(1.1) blur(18px);
  }
  [data-testid="stHeader"]::after {
    content: "AI SelfLearner";
    position: absolute;
    top: 1rem;
    left: 4rem;
    color: var(--ink);
    font-size: .88rem;
    font-weight: 730;
    letter-spacing: -.02em;
  }
  [data-testid="stToolbar"] { display: none; }
  [data-testid="stMainBlockContainer"] { padding: 5rem 1.1rem 4rem; }
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
  .stButton > button, .stFormSubmitButton > button { width: 100%; min-height: 48px; }
  .rule { margin: 2.2rem 0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}

@media (prefers-contrast: more) {
  :root { --line: rgba(73, 91, 118, .5); --line-strong: rgba(62, 80, 107, .72); }
}

@media (prefers-reduced-transparency: reduce) {
  [data-testid="stSidebar"], [data-testid="stHeader"] {
    background: var(--surface-solid);
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
  }
}
</style>
"""


def apply_design_system() -> None:
    """Apply stable semantic tokens once per Streamlit rerun."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
