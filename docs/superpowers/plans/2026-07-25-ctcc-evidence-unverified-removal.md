# CTCC Evidence Unverified-Claim Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to run this plan — one Composer 2.5 subagent per batch, dispatched **sequentially** (not in parallel), reviewed between batches.

**Goal:** For each of the 42 CTCC evidence files with `unverified > 0` from the `verify-evidence-retroactive.js --profile ctcc` run (2026-07-26T00:29–01:37Z), remove every item whose `quote_verified === false`, and correspondingly edit the paired synthesis note so it no longer asserts, tabulates, or quotes anything that was just removed.

**Architecture:** No removal script. Each batch (a discrete, non-overlapping subset of the 42 files) is handed to one Composer 2.5 subagent as a self-contained content-curation task: edit the evidence JSON (drop unverified items, log what was dropped) and edit the paired synthesis note (delete/repair Quotables lines and any prose that depended only on the dropped claim). Subagents run one at a time; the parent reviews each batch's diff before dispatching the next.

**Tech Stack:** Plain JSON + Markdown editing (Read/StrReplace tools only). No new dependencies.

## Global Constraints

- Scope: **only** the 42 files listed below (all have `unverified > 0` from the completed verification run). The three `0/0` files (`SunZia ROD...`, `SunZia_ROD_Appendix_E...`, `aci-25u-03...`) and the 19 skipped files (missing PDF / parse failure / corrupted JSON) are explicitly **out of scope** — addressed in a later pass.
- Only these evidence-JSON fields are ever touched: `key_claims`, `definitions`, `results`, `limitations` (per `verify-evidence.js`'s `QUOTE_FIELDS`). Never touch `methods_assumptions` (no `quote` field there — never verified, never dropped) or `wikipedia_context`.
- Match items to drop **by quote text + page**, never by the `field[idx]` string from `unverified_items` — indices shift as soon as one item in the same array is removed, so index-based removal after the first deletion in an array is a correctness bug. The quote string is unique enough within a paper's evidence file to match on directly.
- After dropping items from a file, do not just silently shrink `_verification` — rewrite it explicitly so the drop is auditable (see Reconciliation Procedure, step 3).
- **Batching is by discrete file, balanced by total unverified-claim count**, not by fixed file-count-per-batch. 9 batches total, computed via LPT (longest-processing-time-first) bin packing over the 42 files' unverified counts, targeting even sums per batch. The two highest-count files (86 and 47) each individually exceed the ~43/batch average, so they are necessarily solo batches; the remaining 40 files split into 7 batches of 5–6 files landing at 36–37 claims each. See per-batch tables in Tasks 2–10.
- Model: `composer-2.5-fast` for every subagent dispatch. `run_in_background: false`, one batch at a time, in the order given below (Batch 1 → Batch 9).
- Evidence dir: `Projects/CTCC/evidence/`. Synthesis dir: `Projects/CTCC/synthesis/`. Note filename = `CTCC - <paper_id>.md` where `paper_id` is the evidence filename minus `.json` (confirmed via `apply-verification-to-notes.js`'s `note_filename_prefix` logic and by direct inspection of the WPR evidence/note pair).
- The synthesis notes' pre-existing `[unverified]` tags (from a stale prior run of `apply-verification-to-notes.js`, which also points at the old `Knowledge/Synthesis/_evidence/` path rather than the current `Projects/CTCC/evidence/` path) are **not** ground truth — some quotes tagged `[unverified]` in notes today were actually re-verified via OCR fallback in the 2026-07-26 run. Subagents must work from each evidence file's **current** `_verification` block, not from note tags.

---

### Task 1: Define the shared Reconciliation Procedure (used by every batch)

**Files:** None created — this is the instruction block every subagent batch prompt embeds verbatim.

**Reconciliation Procedure (per paper, applied by the subagent):**

1. Read `Projects/CTCC/evidence/<paper_id>.json`. Locate `_verification.unverified_items` (e.g. `["key_claims[2]", "results[0]", ...]`) to know how many items to expect — but **do the actual removal by matching each array's `quote_verified === false` items directly**, not by re-deriving indices from that list.
2. For each item with `"quote_verified": false` in `key_claims`, `definitions`, `results`, or `limitations`: delete that entire object from its array. Do not touch items with `quote_verified: true` or items with no `quote` field (i.e. `methods_assumptions`).
3. Rewrite `_verification` to reflect the drop, keeping an audit trail:
   ```json
   "_verification": {
     "timestamp": "<original timestamp, unchanged>",
     "total_quotes": <original verified count>,
     "verified": <original verified count>,
     "page_corrected": <original page_corrected count>,
     "ocr_fallback_used": <original ocr_fallback_used count>,
     "unverified": 0,
     "unverified_items": [],
     "dropped_unverified_count": <N items removed>,
     "dropped_at": "<current ISO-8601 timestamp>"
   }
   ```
4. Read `Projects/CTCC/synthesis/CTCC - <paper_id>.md`.
5. In the **Quotables** section, delete the entire `> "..." (p. N) [unverified]`-or-not blockquote line for each dropped item's quote (match by the quote text substring — case-insensitive, first ~40 chars is enough since quotes are long and distinct). If a line lacks `[unverified]` because the note is stale, still remove it if the quote text matches a dropped item — the evidence, not the note's old tag, is ground truth.
6. Scan **TL;DR, Core contributions, Methods + data, Key assumptions, Results, Limitations / threats to validity, Extracted definitions / cost categories** for any sentence, bullet, or table row whose *only* support was a dropped claim/quote:
   - If a statement is supported **solely** by a dropped item: delete the statement (bullet/row/sentence). If deleting it breaks a numbered list, renumber.
   - If a statement is corroborated by another **still-verified** item in the same file: keep the statement, but if it cited the now-dropped quote/page inline, remove that specific citation.
   - If deleting content leaves a section with zero items, write `*(no verified content remains for this section)*` rather than leaving an empty heading.
7. Save both files. Do not touch any other file's evidence or note.
8. Report back to the parent: per paper, the count of items dropped by field, and a one-line note of which synthesis sections were edited.

---

### Task 2: Batch 1 — dispatch subagent for the single 86-claim file

| Evidence file | Unverified |
|---|---|
| `Transmission investment under uncertainty- Reconciling private and public incentives.json` | 86 |

**Batch total: 86 unverified claims, 1 file.** This file alone exceeds the per-batch average (~43) by 2x — it is not combined with any other file so its subagent can focus entirely on it without splitting attention across papers.

- [ ] **Step 1:** Confirm `Projects/CTCC/synthesis/CTCC - Lavrutich2023TransmissionInvestment.md` exists (`Glob` check).
- [ ] **Step 2:** Dispatch one `Task` tool call, `subagent_type: generalPurpose`, `model: composer-2.5-fast`, `run_in_background: false`. Prompt = Task 1's Reconciliation Procedure + this file's evidence/note path pair (absolute paths) + instruction: "Process this paper using the Reconciliation Procedure. Report dropped-item count by field."
- [ ] **Step 3 (verification):** After the subagent returns, run:
  ```bash
  grep -c '"quote_verified": false' "Projects/CTCC/evidence/Lavrutich2023TransmissionInvestment.json"
  ```
  Expected: `0`.
- [ ] **Step 4:** Read the updated synthesis note and confirm no `[unverified]`-tagged or dropped-quote Quotables lines remain, and that Core contributions/Results sections read coherently (no dangling references to removed claims).

---

### Task 3: Batch 2 — dispatch subagent for the single 47-claim file

| Evidence file | Unverified |
|---|---|
| `Lopez et al. - 2025 - Renewable Energy Technical Potential and Supply Curves for the Contiguous United States 2024 Editio.json` | 47 |

**Batch total: 47 unverified claims, 1 file.** Same rationale as Batch 1 — this file alone exceeds the per-batch average.

- [ ] **Step 1–4:** Same pattern as Task 2, scoped to this one file/note pair.

---

### Task 4: Batch 3 — dispatch subagent for files 3a–3f

| Evidence file | Unverified |
|---|---|
| `Rostoian - Reconductoring Economic and Financial Analysis (REFA) Tool.json` | 22 (all — 0/22 verified) |
| `National Transmission Planning Study. Chapter 3 Transmission Portfolios and Operations for 2035 Sce.json` | 8 |
| `National Transmission Planning Study. Chapter 1 Introduction.json` | 3 |
| `National Transmission Planning Study. Executive Summary.json` | 2 |
| `Joskow 05 Patterns of Transmission Investment.json` | 1 |
| `ipcc_wg3_ar5_chapter7.json` | 1 |

**Batch total: 37 unverified claims, 6 files.**

- [ ] **Step 1:** Confirm all 6 paired notes exist (`Glob` check).
- [ ] **Step 2:** Dispatch one `Task` tool call, `subagent_type: generalPurpose`, `model: composer-2.5-fast`, `run_in_background: false`. Prompt = Task 1's Reconciliation Procedure + these 6 file pairs (absolute paths) + instruction: "Process all 6 papers using the Reconciliation Procedure. Report dropped-item counts per file."
- [ ] **Step 3 (verification):** For each of the 6 evidence files, run `grep -c '"quote_verified": false' "Projects/CTCC/evidence/<file>.json"` — expected `0` for all.
- [ ] **Step 4:** Spot-check the Rostoian note (0/22 verified — every quoted item in this file was unverified). The subagent must not delete the note itself, only strip unsupported content per step 6's "no verified content remains" fallback. **Flag this file for manual review**: a 100%-unverified file may indicate the PDF text extraction failed for this paper rather than the claims being wrong — worth checking before treating this as final.

---

### Task 5: Batch 4 — dispatch subagent for files 4a–4e

| Evidence file | Unverified |
|---|---|
| `National Transmission Planning Study. Chapter 2 Long-Term U.S. Transmission Planning Scenarios.json` | 19 |
| `Rawlins et al. - Ryan Pletka, Project Manager.json` | 10 |
| `Larsen - 2016 - A method to estimate the costs and benefits of undergrounding electricity transmission and distribut.json` | 3 |
| `peaker power plant displacement.json` | 3 |
| `OPINIONETCC-Competitive-Transmission-Myths-Dispelled-11_6_25-FINAL.json` | 1 |

**Batch total: 36 unverified claims, 5 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.
- [ ] **Step 4:** Spot-check the Larsen note — the sample data pulled earlier in this conversation showed at least one dropped item was a chart-axis quote ("Likelihood axis ranges from 0% to 6%") rather than a substantive claim; confirm the subagent removed the axis-description line without disturbing the adjacent benefit–cost ratio figures that were separately verified.

---

### Task 6: Batch 5 — dispatch subagent for files 5a–5f

| Evidence file | Unverified |
|---|---|
| `Teegala and Singal - 2016 - Optimal costing of overhead power transmission lines using genetic algorithms.json` | 18 |
| `Per_Acre_Linear_Rent_Schedule_for_Calendar_Years_2026-2035.json` | 10 (all — 0/10 verified) |
| `Sliwa and Interconnection - The Competitive Planning Process & Supplemental Project Planning.json` | 4 |
| `2024.11_refa_documentation.json` | 2 |
| `2025 Mid-Year SOM Report - September 2025.json` | 1 |
| `Power Delayed- Economic Effects of Electricity Transmission and Generation Development Delays.json` | 1 |

**Batch total: 36 unverified claims, 6 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.
- [ ] **Step 4:** Spot-check `Per_Acre_Linear_Rent_Schedule...` (0/10 verified). This is a BLM per-acre rate-schedule table — table content is exactly the known false-positive-unverified case called out in `Systems/docs/specs/2026-07-25-ocr-fallback-design.md` (layout garbling in text-layer extraction). **Flag for manual review**: check whether the PDF is a scanned/table-heavy document before treating this note's content as unsupported.

---

### Task 7: Batch 6 — dispatch subagent for files 6a–6f

| Evidence file | Unverified |
|---|---|
| `Regional Energy Deployment System (ReEDS) 2011.json` | 17 |
| `NaitBelaid et al. - Reconductoring Economic and Financial Analysis (REFA) Tool.json` | 11 |
| `Transmission Infrastructure access pricing and lumpy investments.json` | 4 |
| `Ellram and Tate - 2021 - Cost Avoidance Not Everything that Counts is Counted.json` | 2 |
| `Data_Center_White_Paper_BEG.json` | 1 |
| `TaylorRoaldA Framework for Risk Assessment and Optimal Line Upgrade Selection to Mitigate Wildfire Risk.json` | 1 |

**Batch total: 36 unverified claims, 6 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.

---

### Task 8: Batch 7 — dispatch subagent for files 7a–7f

| Evidence file | Unverified |
|---|---|
| `Kishore and Singal - 2014 - Optimal economic planning of power transmission lines A review.json` | 14 |
| `Transmission constraints, intermittent renewables and welfare.json` | 13 |
| `CAISOTransmissionEconomicAssessmentMethodology.json` | 4 |
| `Theeconomic value oftransmission lines.json` | 3 |
| `GenX.json` | 1 |
| `a03.1_2024-12-06_ipsac_pjm_rtep_process.json` | 1 |

**Batch total: 36 unverified claims, 6 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.
- [ ] **Step 4:** Spot-check the Kishore and Singal note — the sample data pulled earlier showed several dropped items are mathematical notation/equations (e.g. `"minZ = ∑ij Cij nij + ..."`) rather than prose claims. Confirm the subagent does not remove the surrounding explanatory prose about the optimization formulation if that prose is otherwise supported — only the specific unverifiable equation-quote citations.

---

### Task 9: Batch 8 — dispatch subagent for files 8a–8e

| Evidence file | Unverified |
|---|---|
| `UTAustin_FCe_TransmissionCosts_2017.json` | 14 |
| `Gramlich et al. - Fostering Collaboration Would Help Build Needed Transmission.json` | 12 |
| `Transmission-in-IRP-Part-2.json` | 8 |
| `HOWWetlandCategoriesRatios.json` | 1 |
| `best solution to coordinate the location of power plants with lumpy transmission investments?.json` | 1 |

**Batch total: 36 unverified claims, 5 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.
- [ ] **Step 4:** Spot-check `Transmission-in-IRP-Part-2` — the sample data pulled earlier showed several dropped items are tabular utility-comparison data (zone/scenario counts per utility, e.g. "PAC 25 7 Yes Yes / NVE 6 4 Yes Yes..."). If the note's Results table has rows keyed to these exact figures, confirm the subagent removes only the specific unverified rows/cells, not the entire comparison table if some rows remain supported.

---

### Task 10: Batch 9 (final) — dispatch subagent for files 9a–9f

| Evidence file | Unverified |
|---|---|
| `Costs rise nearly $90M over initial estimates for controversial transmission line - WPR.json` | 13 |
| `Oikonomou et al. - 2024 - Western Interconnection Baseline Study.json` | 13 |
| `2026 PRA Results Posting 20260522 - Corrections754715.json` | 4 |
| `The effect of transmission congestion, generation profiles, and curtailment.json` | 3 |
| `Newhavencorridorcostinflation.json` | 2 |
| `ice_2.0_phase_i_final_report_29may2025.json` | 1 |

**Batch total: 36 unverified claims, 6 files.**

- [ ] **Step 1–3:** Same pattern as Task 4.
- [ ] **Step 4:** Use the WPR file as the ground-truth spot-check for this batch — we already inspected its full pre-drop state in this conversation. Its dropped set is exactly `key_claims[2,3,4,6,7,9]`, `definitions[1]`, `results[0,1,4]`, `limitations[0,1,3]` (13 items). Confirm the subagent's output matches: those 13 quotes gone from Quotables, and the Core contributions items #4 (litigation dispute), #6 (renewable generation claim), and the MISO cost-sharing sentence in Core contributions #5 either removed or rephrased since their supporting quotes are dropped, while items #1–3 (cost overrun, material cost escalation, regulatory bottleneck) remain since their quotes were verified.

---

### Task 11: Aggregate verification + session logging

- [ ] **Step 1:** Re-run the mechanical verifier in dry-run mode to confirm no unverified quotes remain among the 42 processed files and nothing else regressed:
  ```bash
  cd /Users/ai17/Documents/Andys_Workshop
  node Knowledge/Synthesis/_pipeline/scripts/verify-evidence-retroactive.js --profile ctcc --dry-run
  ```
  Expected: `TOTAL: ... quotes: X/X verified, ... 0 unverified` restricted to the 42 files touched (the 19 skipped files will still skip, as expected — out of scope here).
- [ ] **Step 2:** Grep across `Projects/CTCC/synthesis/` for stray `[unverified]` tags to confirm none remain for the 42 touched notes:
  ```bash
  grep -l '\[unverified\]' Projects/CTCC/synthesis/*.md
  ```
  Manually confirm any remaining hits belong only to notes **outside** the 42-file scope.
- [ ] **Step 3:** Per vault rule `05-session-autopersist.mdc` (project-centric routing — CTCC is a specific project): run `python scripts/timekeep.py`, then append a Session Snapshot to `Projects/CTCC/WORKLOG.md` and a summary section to `Projects/CTCC/CHANGELOG.md` covering: the verification run, the 42-file unverified-claim removal across 9 batches, the two flagged 0%-verified files (`Rostoian...`, `Per_Acre_Linear_Rent_Schedule...`) needing manual PDF-extraction review, and the still-open 19 skipped files + 3 empty (`0/0`) files as next steps.
- [ ] **Step 4:** Run `/session-verifier` per the always-applied post-edit checklist (multi-file edits across 42 evidence + 42 synthesis notes qualifies as non-trivial work).

## Dead code removal

No dead code expected — this is content curation, not code changes. No files become unused.

## Rollback plan

- Evidence JSON and synthesis note edits are plain-text/JSON files; if the vault repo is git-tracked, `git diff` / `git checkout -- <path>` per file restores pre-batch state. Since batches are dispatched and reviewed sequentially, a bad batch can be rolled back without affecting already-completed batches.
- If a batch's subagent misbehaves (drops verified content, botches JSON), do not proceed to the next batch — fix or revert that batch first.

## Batch summary (for quick reference)

| Batch | Files | Unverified total |
|---|---|---|
| 1 | 1 | 86 |
| 2 | 1 | 47 |
| 3 | 6 | 37 |
| 4 | 5 | 36 |
| 5 | 6 | 36 |
| 6 | 6 | 36 |
| 7 | 6 | 36 |
| 8 | 5 | 36 |
| 9 | 6 | 36 |
| **Total** | **42** | **386** |
