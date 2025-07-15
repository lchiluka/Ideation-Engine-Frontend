# ---------------------------------------------------------------------------

# utils.pptx_import.py - load concept cards from PPTX slides
# ---------------------------------------------------------------------------
"""Load one or more concept cards from a PPTX deck.

Each slide is expected to contain a title and a two‑column table
with rows ``Field`` | ``Value``.  Field names are lower‑cased and
converted to snake_case so that a slide exported with
``pptx_export.build_pptx_from_df`` round‑trips cleanly.
"""
from pptx import Presentation
from typing import List, Dict, Any, IO

__all__ = ["read_concept_cards"]

def read_concept_cards(stream: IO[bytes]) -> List[Dict[str, Any]]:
    """Return a list of concept dicts extracted from a PPTX file."""
    prs = Presentation(stream)
    cards: List[Dict[str, Any]] = []

    for slide in prs.slides:
        card: Dict[str, Any] = {}
        # grab slide title
        if slide.shapes.title:
            card["title"] = slide.shapes.title.text.strip()

        # look for the first table on the slide
        for shape in slide.shapes:
            if not getattr(shape, "has_table", False):
                continue

            tbl = shape.table
            # turn the RowCollection into a plain list so we can slice
            all_rows = list(tbl.rows)
            # skip the header row at index 0
            for row in all_rows[1:]:
                key = row.cells[0].text.strip().lower().replace(" ", "_")
                val = row.cells[1].text.strip()
                card[key] = val
            break  # only process the first table on a slide

        cards.append(card)

    return cards
