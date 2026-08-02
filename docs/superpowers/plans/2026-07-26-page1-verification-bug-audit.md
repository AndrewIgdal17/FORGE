# Page-1 Verification Bug Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to run this plan — one Composer/Grok subagent per restoration batch, dispatched **sequentially**, reviewed between batches.

**Goal:** Determine whether the `pdf-to-text.js` page-1 text-loss bug (fixed 2026-07-26) caused any of the 386 quotes dropped from the 40 CTCC evidence files (batches 1–9, 2026-07-25/26) to be wrongly removed as false-negative "unverified" — and restore any genuine false positives to evidence + synthesis notes.

**Architecture:** Two phases. Phase A (mechanical, scriptable, TDD-able): extract every quote removed from each synthesis note (via `git diff` against commit `b9f62ed`, the last commit before this session's work started) and re-verify each against the now-fixed `pdf-to-text.js` output. This produces a precise, auditable list of true false-negatives (quotes that now verify) vs. correctly-dropped quotes (still unverified after the fix). Phase B (judgment-required, subagent-driven): for any file with restorable quotes, restore them to the evidence JSON and re-integrate them into the synthesis note's prose/tables/Quotables, batched by discrete file.

**Tech Stack:** Node.js (reusing existing `Knowledge/Synthesis/_pipeline/scripts/` modules), `git diff`, Python for report aggregation. No new dependencies.

## Global Constraints

- Scope: the 40 evidence files with `_verification.dropped_unverified_count` set (i.e., touched by today's earlier batches 1–9). Does NOT include `Rostoian - Reconductoring Economic and Financial Analysis (REFA) Tool.json` or `Per_Acre_Linear_Rent_Schedule_for_Calendar_Years_2026-2035.json` — those were already fully re-synthesized from scratch under the fixed pipeline and are out of scope here.
- The evidence JSON files are gitignored (`Projects/*/evidence/**/*.json` in `.gitignore`) — there is NO git history for them. The only recoverable pre-drop record is each paper's synthesis note, which IS tracked and has a clean pre-session baseline at commit `b9f62ed` ("restructure: migrate CTCC to project-centric layout").
- A quote is a genuine false-negative (restore it) only if it now verifies (exact or fuzzy match, with OCR fallback) against the FIXED `pdf-to-text.js` output. Do not restore based on plausibility alone — the whole point of this audit is to stay mechanical and avoid re-introducing hallucination risk.
- Do not touch the 3 pre-existing empty (`0/0`) evidence files or the 19 skipped files (missing PDF / parse failure / corrupted JSON) — those remain out of scope for this plan, per the original scope split.
- Model for restoration subagents: `cursor-grok-4.5-high-fast` (matching the model used for the two full re-syntheses today), `run_in_background: false`, sequential dispatch.

---

## Phase A: Build and run the audit script

### Task 1: Write the audit script

**Files:**
- Create: `Knowledge/Synthesis/_pipeline/scripts/audit-page1-bug.js`

**Purpose:** For each of the 40 in-scope papers, extract every quote removed from its synthesis note (relative to `b9f62ed`), then re-verify each against the current (fixed) PDF text extraction. Output a JSON report — this script only reads and reports, it does not write to evidence or synthesis files.

- [ ] **Step 1: Write the script**

```js
#!/usr/bin/env node
"use strict";

/**
 * Audit script for the pdf-to-text.js page-1 text-loss bug (fixed 2026-07-26).
 * For each in-scope paper, extracts quotes removed from its synthesis note
 * (git diff against a pre-session baseline commit) and re-verifies each
 * against the CURRENT (fixed) pdf-to-text.js output. Read-only: writes a
 * JSON report only, does not modify evidence or synthesis files.
 *
 * Usage: node audit-page1-bug.js [--baseline <commit>]
 */

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { verifyEvidence, splitTaggedText, findQuoteInPages, buildPages } = require("./verify-evidence.js");

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..");
const SCRIPTS_DIR = __dirname;
const SYNTHESIS_DIR = path.join(REPO_ROOT, "Projects/CTCC/synthesis");
const LITERATURE_PREFIX = "Projects/CTCC/literature/";
const DEFAULT_BASELINE = "b9f62ed";

const IN_SCOPE_PAPER_IDS = [
  "2024.11_refa_documentation",
  "2025 Mid-Year SOM Report - September 2025",
  "2026 PRA Results Posting 20260522 - Corrections754715",
  "CAISOTransmissionEconomicAssessmentMethodology",
  "Costs rise nearly $90M over initial estimates for controversial transmission line - WPR",
  "Data_Center_White_Paper_BEG",
  "Ellram and Tate - 2021 - Cost Avoidance Not Everything that Counts is Counted",
  "GenX",
  "Gramlich et al. - Fostering Collaboration Would Help Build Needed Transmission",
  "HOWWetlandCategoriesRatios",
  "Joskow 05 Patterns of Transmission Investment",
  "Kishore and Singal - 2014 - Optimal economic planning of power transmission lines A review",
  "Larsen - 2016 - A method to estimate the costs and benefits of undergrounding electricity transmission and distribut",
  "Lopez et al. - 2025 - Renewable Energy Technical Potential and Supply Curves for the Contiguous United States 2024 Editio",
  "NaitBelaid et al. - Reconductoring Economic and Financial Analysis (REFA) Tool",
  "National Transmission Planning Study. Chapter 1 Introduction",
  "National Transmission Planning Study. Chapter 2 Long-Term U.S. Transmission Planning Scenarios",
  "National Transmission Planning Study. Chapter 3 Transmission Portfolios and Operations for 2035 Sce",
  "National Transmission Planning Study. Executive Summary",
  "Newhavencorridorcostinflation",
  "OPINIONETCC-Competitive-Transmission-Myths-Dispelled-11_6_25-FINAL",
  "Oikonomou et al. - 2024 - Western Interconnection Baseline Study",
  "Power Delayed- Economic Effects of Electricity Transmission and Generation Development Delays",
  "Rawlins et al. - Ryan Pletka, Project Manager",
  "Regional Energy Deployment System (ReEDS) 2011",
  "Sliwa and Interconnection - The Competitive Planning Process & Supplemental Project Planning",
  "TaylorRoaldA Framework for Risk Assessment and Optimal Line Upgrade Selection to Mitigate Wildfire Risk",
  "Teegala and Singal - 2016 - Optimal costing of overhead power transmission lines using genetic algorithms",
  "The effect of transmission congestion, generation profiles, and curtailment",
  "Theeconomic value oftransmission lines",
  "Transmission Infrastructure access pricing and lumpy investments",
  "Transmission constraints, intermittent renewables and welfare",
  "Transmission investment under uncertainty- Reconciling private and public incentives",
  "Transmission-in-IRP-Part-2",
  "UTAustin_FCe_TransmissionCosts_2017",
  "a03.1_2024-12-06_ipsac_pjm_rtep_process",
  "best solution to coordinate the location of power plants with lumpy transmission investments?",
  "ice_2.0_phase_i_final_report_29may2025",
  "ipcc_wg3_ar5_chapter7",
  "peaker power plant displacement",
];

function log(line) {
  console.log(`${new Date().toISOString()}  ${line}`);
}

function gitDiffNote(paperId, baseline) {
  const noteRel = `Projects/CTCC/synthesis/CTCC - ${paperId}.md`;
  const r = spawnSync("git", ["diff", baseline, "--", noteRel], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  if (r.status !== 0 && r.status !== null) {
    log(`  WARN git diff failed for ${paperId}: ${r.stderr}`);
    return "";
  }
  return r.stdout || "";
}

/**
 * Extract removed Quotables blockquote lines from a unified diff.
 * Matches lines like: -> "quote text" (p. N) [unverified]
 * @returns {{quote: string, claimedPage: string}[]}
 */
function extractRemovedQuotes(diffText) {
  const results = [];
  const lines = diffText.split("\n");
  const bqRe = /^-\s*>\s*"(.+)"\s*\(p\.\s*(\S+)\)/;
  const bqReNoQuotes = /^-\s*-\s*p\.\s*\S+:\s*"(.+)"/; // alternate "- p.N: "..."" list format
  for (const line of lines) {
    if (!line.startsWith("-") || line.startsWith("---")) continue;
    let m = line.match(bqRe);
    if (m) {
      results.push({ quote: m[1], claimedPage: m[2] });
      continue;
    }
    m = line.match(bqReNoQuotes);
    if (m) {
      results.push({ quote: m[1], claimedPage: "" });
    }
  }
  return results;
}

function spawnPdfToText(pdfRel) {
  const r = spawnSync("node", [path.join(SCRIPTS_DIR, "pdf-to-text.js"), pdfRel], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    env: {
      ...process.env,
      SYNTHESIS_LITERATURE_PREFIX: LITERATURE_PREFIX,
      VAULT_ROOT: REPO_ROOT,
      REPO_ROOT,
    },
    timeout: 120000,
  });
  if (r.status !== 0) return null;
  const idx = (r.stdout || "").indexOf("{");
  if (idx < 0) return null;
  try {
    const parsed = JSON.parse(r.stdout.slice(idx));
    return parsed.ok ? parsed : null;
  } catch (_) {
    return null;
  }
}

function main() {
  const argv = process.argv.slice(2);
  let baseline = DEFAULT_BASELINE;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--baseline" && argv[i + 1]) {
      baseline = argv[i + 1];
      i++;
    }
  }

  const report = { baseline, generated_at: new Date().toISOString(), papers: [] };

  for (const paperId of IN_SCOPE_PAPER_IDS) {
    const diffText = gitDiffNote(paperId, baseline);
    const removedQuotes = extractRemovedQuotes(diffText);
    if (removedQuotes.length === 0) {
      report.papers.push({ paper_id: paperId, removed_quote_count: 0, candidates: [] });
      log(`${paperId}: 0 removed quotes in diff`);
      continue;
    }

    const pdfRel = `${LITERATURE_PREFIX}${paperId}.pdf`;
    const pdfResult = spawnPdfToText(pdfRel);
    if (!pdfResult) {
      log(`  WARN ${paperId}: pdf-to-text failed, skipping re-verification`);
      report.papers.push({
        paper_id: paperId,
        removed_quote_count: removedQuotes.length,
        candidates: removedQuotes.map((q) => ({ ...q, now_verified: null, note: "pdf-to-text failed" })),
      });
      continue;
    }

    const { perPageTexts, pageLabels } = splitTaggedText(pdfResult.text || "");
    const pages = buildPages(perPageTexts, pageLabels);

    const candidates = removedQuotes.map((q) => {
      const match = findQuoteInPages(q.quote, pages);
      return {
        quote: q.quote,
        claimedPage: q.claimedPage,
        now_verified: !!match,
        matched_page: match ? match.label : null,
        match_method: match ? match.method : null,
      };
    });

    const restorable = candidates.filter((c) => c.now_verified);
    log(`${paperId}: ${removedQuotes.length} removed quotes, ${restorable.length} now verify (restorable)`);
    report.papers.push({ paper_id: paperId, removed_quote_count: removedQuotes.length, candidates });
  }

  const totalRemoved = report.papers.reduce((s, p) => s + p.removed_quote_count, 0);
  const totalRestorable = report.papers.reduce(
    (s, p) => s + p.candidates.filter((c) => c.now_verified).length,
    0,
  );
  report.summary = { total_removed_quotes_found_in_diff: totalRemoved, total_restorable: totalRestorable };

  const outPath = path.join(REPO_ROOT, "Projects/CTCC/code/docs/superpowers/plans/2026-07-26-page1-bug-audit-report.json");
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");
  log("---");
  log(`TOTAL: ${totalRemoved} removed quotes found in diffs, ${totalRestorable} restorable (false negatives)`);
  log(`Report written to ${outPath}`);
}

main();
```

- [ ] **Step 2: Sanity-test on one known file before running the full batch**

```bash
cd /Users/ai17/Documents/Andys_Workshop
node -e '
const { extractRemovedQuotes } = (() => {
  // inline test of the regex against the WPR diff sample from this conversation
  const sample = `-> "Project co-owners say increases are driven by rising material costs, land-related expenses, ongoing legal challenges." (p. 0) [unverified]`;
  const bqRe = /^-\s*>\s*"(.+)"\s*\(p\.\s*(\S+)\)/;
  console.log(sample.match(bqRe));
  return {};
})();
'
```

Expected: the regex captures the quote text and claimed page (`0`) correctly. If it does not match, fix the regex before running the full script — do not proceed with a broken extractor.

- [ ] **Step 3: Run the audit script for real**

```bash
cd /Users/ai17/Documents/Andys_Workshop
node Knowledge/Synthesis/_pipeline/scripts/audit-page1-bug.js
```

Expected: completes in under a few minutes (39 papers × one `pdf-to-text.js` call each, no OCR fallback needed for most since only page-1 text was affected and most quotes aren't garbled tables). Produces `Projects/CTCC/code/docs/superpowers/plans/2026-07-26-page1-bug-audit-report.json` with a `summary.total_restorable` count.

- [ ] **Step 4: Review the report**

Read the generated report. For each paper with `candidates` where `now_verified: true`, that quote is a confirmed false-negative — genuinely present in the source PDF, wrongly dropped by today's earlier batches due to the bug. For `now_verified: false` candidates, the removal was correct (the quote really isn't findable in the source, bug or no bug) — no action needed for those.

Report to the user: how many total removed quotes were checked, how many are restorable, and which specific papers have restorable content, before proceeding to Phase B.

---

## Phase B: Restore confirmed false-negatives

**This phase's scope is only known after Task 1 completes** — the exact set of papers/quotes needing restoration depends on the audit report's `total_restorable` count and distribution. Follow this procedure once the report is in hand:

### Task 2: Determine restoration batches

- [ ] **Step 1:** From the audit report, list every paper with at least one `now_verified: true` candidate.
- [ ] **Step 2:** If the total restorable-quote count across those papers is small (rough guideline: under ~15 quotes total), restore them all in a single subagent dispatch. If larger, batch by discrete file with quote-count balanced via the same LPT bin-packing approach used in the original removal plan (`2026-07-25-ctcc-evidence-unverified-removal.md`), sequential dispatch, `cursor-grok-4.5-high-fast`.
- [ ] **Step 3:** If `total_restorable` is 0, skip Phase B entirely — the bug did not cause any actual data loss in the 40-file cleanup (it only fully broke the two single-page PDFs already fixed today), and this plan is complete after Task 1's report is reviewed.

### Task 3+: Restoration dispatch (repeat per batch)

For each batch, dispatch one subagent with this procedure per paper:

1. Read the audit report's entries for this paper — the list of `now_verified: true` quotes, their `matched_page`, and the quote text itself.
2. Read the current evidence JSON. Add each restorable quote back as an item in the appropriate array (`key_claims`, `definitions`, `results`, or `limitations` — infer from the quote's content and the removed line's original context in the note diff) with `"quote_verified": true`, `"page": <matched_page>`, and a `"claim"`/`"item"`/`"definition"` field written to describe what the quote establishes (the diff often shows the original claim text on the line right before/after the quote in the note — reuse it if present; otherwise write a faithful one-line paraphrase of the quote).
3. Update the evidence JSON's `_verification` block: increment `verified` and `total_quotes` by the number of restored items, decrement nothing from `dropped_unverified_count` (leave it as a historical record of the original drop, but add a new field `restored_after_bugfix_count` with the count restored).
4. Read the current synthesis note. Re-integrate each restored quote:
   - Add it back to **Quotables** with its corrected page number, no `[unverified]` tag.
   - If the note's prose (Core contributions, Results, etc.) was trimmed in a way that specifically removed the claim this quote supports, restore that specific bullet/row too, now correctly backed by a real quote.
   - Do not blindly revert the whole note to its pre-batch state — only restore the specific items confirmed by the audit; keep all other edits from today's batches (which remain correct) intact.
5. Save both files.
6. Report per paper: how many items restored, which sections of the note were touched.

### Task 4: Final verification + logging

- [ ] **Step 1:** Re-run `node Knowledge/Synthesis/_pipeline/scripts/verify-evidence-retroactive.js --profile ctcc --dry-run` to confirm the restored items verify cleanly and nothing regressed (expect `0 unverified` still, with a higher `verified` total than before restoration).
- [ ] **Step 2:** Run `python scripts/timekeep.py`, append a WORKLOG snapshot to `Projects/CTCC/WORKLOG.md` and a CHANGELOG entry to `Projects/CTCC/CHANGELOG.md` documenting: the bug, the fix, the audit findings (X restorable out of Y removed), and which papers/items were restored.
- [ ] **Step 3:** Run `/session-verifier`.

## Dead code removal

No dead code expected. The audit script (`audit-page1-bug.js`) is a one-time diagnostic tool tied to this specific bug; it can be deleted after this plan completes if desired, or kept as a reference — not required either way since it's read-only and harmless to leave.

## Rollback plan

- The audit script is read-only (writes only a report file) — no rollback needed for Phase A.
- Phase B edits are plain JSON/Markdown; `git diff` / `git checkout` restores synthesis notes if a restoration batch goes wrong (evidence JSON has no git history, so back up `Projects/CTCC/evidence/*.json` for in-scope files before Phase B if extra safety is wanted).

## Related

- Original removal plan: `Projects/CTCC/code/docs/superpowers/plans/2026-07-25-ctcc-evidence-unverified-removal.md`
- Bug fix: `Knowledge/Synthesis/_pipeline/scripts/pdf-to-text.js` (the `.trim()` → `.replace(/\s+$/, "")` change, 2026-07-26)
- OCR fallback design (documents the table-garbling failure mode, unrelated to this bug but same pipeline): `Systems/docs/specs/2026-07-25-ocr-fallback-design.md`
