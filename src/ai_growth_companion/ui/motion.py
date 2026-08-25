"""Pointer-aware ambient glow for the persistent glass chrome.

A tiny same-origin helper mirrors the pointer position into CSS custom
properties on the toolbar and on primary actions. Every guard fails closed:
without a fine pointer, or when reduced motion is requested, no listener is
attached at all. All work is rAF-throttled and never touches React state.
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
    var lastX = -1;
    var lastY = -1;
    var place = function (el, x, y) {
      var rect = el.getBoundingClientRect();
      el.style.setProperty("--glow-x", (x - rect.left).toFixed(1) + "px");
      el.style.setProperty("--glow-y", (y - rect.top).toFixed(1) + "px");
    };
    var apply = function () {
      frame = 0;
      var toolbar = doc.querySelector(".st-key-app_toolbar");
      if (toolbar) {
        place(toolbar, lastX, lastY);
      }
      var hit = doc.elementFromPoint(lastX, lastY);
      var button = hit ? hit.closest(".stMain button[kind='primary']") : null;
      if (button) {
        place(button, lastX, lastY);
      }
    };
    var queue = function () {
      if (!frame) {
        frame = win.requestAnimationFrame(apply);
      }
    };
    doc.addEventListener(
      "pointermove",
      function (event) {
        lastX = event.clientX;
        lastY = event.clientY;
        queue();
      },
      { passive: true }
    );
    doc.addEventListener("scroll", queue, { passive: true });
  } catch (err) {
    /* The glow is decorative; any failure keeps the default static chrome. */
  }
})();
</script>
"""


def render_pointer_glow() -> None:
    """Attach the pointer-follow glow once; it never affects layout or data."""
    components.html(POINTER_GLOW_SNIPPET, height=0)
