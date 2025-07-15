import time
from utils.query_generator import generate_academic_search_query

# Paste your longest example text here:
long_concept = """
Add thin U-shaped PIR ‘shield ribs’ around each VIP tile before lamination; ribs are 3 mm higher than the tile so cutters and screws bear on foam first, avoiding envelope puncture (Principles 3, 15).
Use laser-welded stainless micro-shell VIPs with edge crimps rolled inward; allows boards to be gang-sawn without exposing a foil seam (Principle 7).
Integrate helium leak-test station inline; defective tiles are picked out before foaming (Principle 24).
Specify modular 12 × 12 in tile pattern so any field cut removes whole tiles cleanly, limiting random breaches (Principle 1).
"""

start = time.time()
try:
    short_q = generate_academic_search_query(long_concept, max_keywords=8)
    took = time.time() - start
    print(f"LLM helper returned in {took:.1f} seconds:", short_q)
except Exception as e:
    print("LLM helper raised:", e)
