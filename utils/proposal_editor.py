
from __future__ import annotations

import streamlit as st
import json
import re
from typing import Any, Dict, Callable
from streamlit_quill import st_quill
import html2text

# Converter for rich-text fields
h2t = html2text.HTML2Text()
h2t.ignore_links = False

__all__ = ["ProposalEditor"]

# CSS for highlighting regenerated sections
HIGHLIGHT_CSS = """
<style>
.flash-border {border-left:6px solid gold !important; padding-left:4px;}
.flash-text   {background:#FFF8E5;}
</style>
"""

class ProposalEditor:
    _SSKEY = "__proposal_drafts__"

    @staticmethod
    def _drafts() -> Dict[str, Dict[str, Any]]:
        """Retrieve or initialize saved drafts in session state."""
        return st.session_state.setdefault(ProposalEditor._SSKEY, {})

    def save(self, draft_json: dict) -> None:
        """
        Save or update a full proposal draft JSON under its title.
        The draft JSON can contain arbitrary keys; the editor will render fields dynamically.
        """
        title = draft_json.get("title") or f"Untitled-{len(self._drafts())+1}"
        self._drafts()[title] = draft_json

    def render(self) -> None:
        """
        Render the interactive proposal editor. Fields are generated from the JSON keys.
        Each field is editable and has its own regenerate button.
        """
        drafts = self._drafts()
        if not drafts:
            return

        # Inject CSS and header
        st.markdown(HIGHLIGHT_CSS, unsafe_allow_html=True)
        st.header("📝 Interactive Proposal Editor")

        # Snapshot for diffing
        prev = json.loads(json.dumps(drafts))
        st.session_state["_previous_draft"] = prev
        flash = set(st.session_state.get("flash_sections", []))
        last_diff = st.session_state.get("last_diff")
        if last_diff:
            with st.expander("🗒️ Changes applied in last regeneration", expanded=True):
                st.code(last_diff, language="json")

        dirty = False
        for title, draft in drafts.items():
            safe_title = re.sub(r'[^A-Za-z0-9_]', "_", title)
            with st.expander(title, expanded=False):
                # Preview button
                if st.button("👁 Preview this draft", key=f"preview_{safe_title}"):
                    st.session_state["_current_title"] = title

                # Dynamically render each field
                for field, val in draft.items():
                    label = field.replace("_", " ").title()

                    # ── LOCK DOWN THE TITLE ─────────────────────────────────────────
                    if field == "title":
                        st.markdown(f"**{label}**")
                        st.text_input("", value=val, key=f"{safe_title}__{field}", disabled=True, label_visibility="collapsed")
                        st.markdown("---")
                        continue
                    # Highlight regenerated fields
                    if field in flash:
                        st.markdown(
                            f'<div class="flash-border"><span class="flash-text">**{label} ✨**</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"**{label}**")

                    # Unique widget key
                    safe_field = re.sub(r'[^A-Za-z0-9_]', "_", field)
                    widget_key = f"{safe_title}__{safe_field}"

                    # Render appropriate widget
                    new_val = self._widget_for(widget_key, val)
                    if new_val != val:
                        draft[field] = new_val
                        dirty = True

                    # Regenerate button for this field
                    if st.button("↻ Regenerate", key=f"{widget_key}__regen"):
                        st.session_state["_regen_payload"] = {"draft": draft, "field": field}
                        st.rerun()

                    st.markdown("---")

        if dirty:
            st.success("✅ Edits saved – click a ↻ button to propagate changes.")

        # Clear flash state and diff
        st.session_state.pop("flash_sections", None)
        st.session_state.pop("last_diff", None)

    def preview(self, build_docx_report_fn: Callable[[list[dict]], None]) -> None:
        """
        Show a live DOCX-to-HTML preview of the selected draft.
        """
        drafts = self._drafts()
        if not drafts:
            st.info("No proposal drafted yet – edit something first!")
            return

        current = st.session_state.get("_current_title") or next(iter(drafts))
        if current not in drafts:
            current = next(iter(drafts))
        st.session_state["_current_title"] = current

        try:
            import mammoth, streamlit.components.v1 as components
        except ImportError:
            st.warning("Install **mammoth** to enable live Word preview.")
            return

        from io import BytesIO
        bio = BytesIO()
        build_docx_report_fn([drafts[current]], bio)
        bio.seek(0)
        html = mammoth.convert_to_html(bio).value
        components.html(html, height=800, scrolling=True)

    def _widget_for(self, widget_key: str, value: Any) -> Any:
        """
        Render an editable widget based on the Python type of value.
        Supports: str, int, float, list[str], dict (editable JSON), fallback text.
        """
        # String
        if isinstance(value, str):
            if "\n" in value or len(value) > 120 or '<' in value:
                html = h2t.handle(value) if '<' in value else value
                return st_quill(html, key=widget_key)
            return st.text_input("", value=value, key=widget_key, label_visibility="collapsed")

        # Number
        if isinstance(value, (int, float)):
            return st.number_input("", value=value, key=widget_key, label_visibility="collapsed")

        # List of strings
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            joined = "\n".join(value)
            new_txt = st.text_area(""Proposal text"", value=joined, key=widget_key, label_visibility="collapsed")
            return [ln.strip() for ln in new_txt.splitlines() if ln.strip()]

        # Dict: editable JSON
        if isinstance(value, dict):
            json_str = json.dumps(value, indent=2)
            new_str = st.text_area(
                "",
                value=json_str,
                height=150,
                key=widget_key,
                label_visibility="collapsed"
            )
            try:
                return json.loads(new_str)
            except json.JSONDecodeError:
                st.error("Invalid JSON format – reverting.")
                return value

        # Fallback: render repr
        text = repr(value)
        return st.text_area("", value=text, key=widget_key, label_visibility="collapsed")

