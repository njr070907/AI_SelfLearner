"""One restrained visual system shared by all Streamlit pages."""

import streamlit as st

APP_CSS = """
<style>
:root {
  --canvas: #f5f7fa;
  --surface: #ffffff;
  --surface-muted: #f8f9fc;
  --ink: #111827;
  --ink-muted: #64748b;
  --line: #dce2eb;
  --line-strong: #cbd5e1;
  --accent: #5868e8;
  --accent-soft: #eef0ff;
  --success: #15803d;
  --warning: #a16207;
  --danger: #b42318;
  --radius: 14px;
  --radius-small: 9px;
}

html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Microsoft YaHei", sans-serif;
}

[data-testid="stAppViewContainer"] { background: var(--canvas); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] {
  max-width: 1080px;
  padding-top: 3.25rem;
  padding-bottom: 5rem;
}

[data-testid="stSidebar"] {
  background: #121722;
  border-right: 1px solid #202838;
}
[data-testid="stSidebar"] * { color: #d7deeb; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .25rem; }
[data-testid="stSidebar"] label[data-baseweb="radio"] {
  padding: .65rem .75rem;
  border-radius: var(--radius-small);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
  background: #252d3d;
}

h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
p, li { color: #41506a; }

.brand {
  display: flex;
  align-items: center;
  gap: .65rem;
  color: white;
  font-weight: 750;
  margin: .25rem 0 1.4rem;
}
.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--accent);
  color: white;
  font-weight: 800;
}
.sidebar-status {
  margin-top: 2.4rem;
  padding-top: 1rem;
  border-top: 1px solid #2a3344;
  color: #93a4bf !important;
  font-size: .78rem;
  line-height: 1.7;
}
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 99px;
  background: #5ee0a0;
  margin-right: .4rem;
}

.eyebrow {
  color: #5a6a86;
  font-size: .82rem;
  font-weight: 650;
  letter-spacing: .025em;
  margin-bottom: .6rem;
}
.hero-title {
  color: var(--ink);
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.08;
  letter-spacing: -.045em;
  font-weight: 780;
  margin: 0 0 .75rem;
}
.hero-copy {
  color: #64748b;
  font-size: 1.02rem;
  line-height: 1.8;
  max-width: 680px;
  margin: 0 0 1.7rem;
}
.section-label {
  color: #52617a;
  font-size: .82rem;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  margin-bottom: .55rem;
}
.rule { border-top: 1px solid var(--line); margin: 2rem 0; }

.empty-state {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 2rem 0;
}
.empty-state h2 { margin: 0 0 .75rem; font-size: 1.55rem; }
.empty-state p { max-width: 590px; line-height: 1.75; margin: 0 0 1.15rem; }

.question-panel, .diagnosis-panel, .system-panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.question-panel { padding: 1.4rem 1.55rem; margin: .5rem 0 1.4rem; }
.question-panel p { margin: 0; font-size: 1.08rem; line-height: 1.75; color: #243047; }
.question-kicker { color: var(--accent); font-size: .8rem; font-weight: 750; margin-bottom: .6rem; }

.diagnosis-panel { border-left: 4px solid var(--accent); margin: 1rem 0 1.25rem; }
.diagnosis-head { padding: 1.35rem 1.5rem 1.25rem; border-bottom: 1px solid var(--line); }
.diagnosis-head h2 { margin: 0 0 .45rem; font-size: 1.5rem; }
.diagnosis-head p { margin: 0; line-height: 1.65; }
.diagnosis-grid { display: grid; grid-template-columns: 1fr 1fr; }
.diagnosis-cell { padding: 1.25rem 1.5rem; min-height: 150px; }
.diagnosis-cell + .diagnosis-cell { border-left: 1px solid var(--line); }
.diagnosis-cell h3 { margin: 0 0 .65rem; font-size: .95rem; }
.diagnosis-cell ul { padding-left: 1.15rem; margin: 0; }
.diagnosis-cell li { margin: .55rem 0; line-height: 1.55; }
.next-step {
  background: var(--accent-soft);
  padding: 1.15rem 1.5rem;
  border-top: 1px solid #dfe3ff;
}
.next-step strong { display: block; color: #242f65; margin-bottom: .3rem; }
.next-step p { margin: 0; color: #56628e; }

.badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: .3rem .65rem;
  background: var(--accent-soft);
  color: #4453c7;
  font-size: .76rem;
  font-weight: 700;
}
.badge-warn { background: #fff4df; color: var(--warning); }
.badge-good { background: #eaf8f0; color: var(--success); }
.badge-danger { background: #fff0ee; color: var(--danger); }

.progress-row, .status-row {
  display: grid;
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid var(--line);
  padding: 1rem 0;
}
.progress-row { grid-template-columns: minmax(180px, 1.4fr) .7fr 1fr 1fr; }
.status-row { grid-template-columns: minmax(150px, .75fr) 1fr auto; }
.row-title { color: var(--ink); font-weight: 700; }
.row-meta { color: var(--ink-muted); font-size: .88rem; }

.error-panel {
  border: 1px solid #efc8c3;
  border-left: 4px solid var(--danger);
  border-radius: var(--radius);
  background: #fffafa;
  padding: 1.3rem 1.5rem;
  margin: 1rem 0;
}
.error-panel h3 { color: #7f1d1d; margin: 0 0 .4rem; }
.error-panel p { margin: 0; color: #7f3b35; }

.stButton > button, .stFormSubmitButton > button {
  border-radius: var(--radius-small);
  min-height: 42px;
  font-weight: 700;
  box-shadow: none;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--accent);
  border-color: var(--accent);
}
[data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
  border-radius: var(--radius-small);
  border-color: var(--line-strong);
  background: var(--surface);
}

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding-top: 2rem; }
  .diagnosis-grid { grid-template-columns: 1fr; }
  .diagnosis-cell + .diagnosis-cell { border-left: 0; border-top: 1px solid var(--line); }
  .progress-row { grid-template-columns: 1fr 1fr; }
  .status-row { grid-template-columns: 1fr; gap: .35rem; }
}
</style>
"""


def apply_design_system() -> None:
    """Apply the shared visual tokens once per Streamlit rerun."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
