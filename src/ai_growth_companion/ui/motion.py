"""Pointer-aware ambient glow for the persistent glass chrome.

A tiny same-origin helper mirrors the pointer position into CSS custom
properties on the toolbar. Every guard fails closed: without a fine pointer,
or when reduced motion is requested, no listener is attached at all.
"""

import streamlit.components.v1 as components

POINTER_GLOW_SNIPPET = """
<script>
(function () {
  var win = window;
  var doc = null;
  try {
    doc = window.parent.document;
    win = window.parent;
  } catch (err) {
    return;
  }
  try {
    if (win.__selflearnerGlowAttached) {
      return;
    }
    var fine = win.matchMedia("(hover: hover) and (pointer: fine)");
    var calm = win.matchMedia("(prefers-reduced-motion: reduce)");
    if (!fine.matches || calm.matches) {
      return;
    }
    win.__selflearnerGlowAttached = true;
    var frame = 0;
    doc.addEventListener(
      "pointermove",
      function (event) {
        if (frame) {
          return;
        }
        frame = win.requestAnimationFrame(function () {
          frame = 0;
          var el = doc.querySelector(".st-key-app_toolbar");
          if (!el) {
            return;
          }
          var rect = el.getBoundingClientRect();
          el.style.setProperty("--glow-x", (event.clientX - rect.left).toFixed(1) + "px");
          el.style.setProperty("--glow-y", (event.clientY - rect.top).toFixed(1) + "px");
        });
      },
      { passive: true }
    );
  } catch (err) {
    /* The glow is decorative; any failure keeps the default static chrome. */
  }
})();
</script>
"""


def render_pointer_glow() -> None:
    """Attach the pointer-follow glow once; it never affects layout or data."""
    components.html(POINTER_GLOW_SNIPPET, height=0)
