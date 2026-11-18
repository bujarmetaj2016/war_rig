# Owner disposition — D03 negative-ID count (18 Nov 2026)

Conflict: R3 §4 expects 59 NEG- ids from D03 file 02_NEGATIVE_GRAPH_COMPLEMENT_59_SOURCE_PRESERVED.json; the file holds 84 distinct NEG- ids
(59 source-preserved + 25 Master-derived). R3 §4 also states that 84 denied pairs are re-derived from these sources.

Disposition (interpretation, no count or source changed):
1. R3's "59 NEG- ids" means the 59 SOURCE-PRESERVED ids. The universe class NEG_PRESERVED must contain exactly 59, identified by the file's own
   provenance field (not by position or inference). Any other number is still BLOCKED_SOURCE_CONFLICT.
2. The 25 Master-derived ids form a separate class NEG_MASTER_DERIVED, which must contain exactly 25. They are claims to re-verify, not copied passes.
3. The denied-pair set must be re-derived mechanically from the V5 transition graph, independently of file 02. It must equal exactly 84 pairs, and
   its union with file 02's ids must match one-to-one (59 + 25). Any extra, missing or mismatched pair is a real conflict: report it, do not adjust it.
4. Traceability holds one row per id in both classes. The universe total rises by the 25 derived ids, with the reason cited to this file.
5. R3 itself is not edited; this file is the controlled disposition R3's conflict rule calls for.
