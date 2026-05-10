# Consistency: Main Paper Methods vs. Appendix

When checking whether **Section 3 (Methods)** in `papers/paper1/paper1.tex` is consistent with **Appendix A** (`papers/paper1/p1appendix.tex`), apply this definition. The appendix is the source of truth for notation and terminology.

## Definition of consistency

**Consistent** means all three of the following hold:

### 1. Substantive consistency

- Same cost and benefit categories and sub-components (e.g. capital = build + ROW capital + env. mitigation; delay = base + congestion + curtailment).
- Same definitions: what counts as capital, what enters rate base, which costs use which discount rate (WACC vs. social), how revenue is treated (excluded from societal metrics; benefit to utility, cost to ratepayers).
- No logical or framing contradictions between the main paper and the appendix.

### 2. Notation consistency

- The **same mathematical symbols and subscript names** are used for the same quantities in both places.
- Examples: appendix uses \(C_{\text{rent}}\), \(C_{\text{loss}}\), \(C_{\text{cong,delay}}\) — the main paper must use those same symbols for those costs, not \(C_{\text{ROW rent}}\), \(C_{\text{Line losses}}\), \(C_{\text{Congestion delay}}\).
- When in doubt, the appendix’s variable tables and equation subscripts are the reference.

### 3. Terminology consistency

- Same **terms** for the same concepts in prose and in equation labels.
- Examples: “base delay” not “construction delay”; “externality costs” for the set discounted at the social rate (emissions, expected wildfire, expected outage).

## How to report a consistency check

When asked “is it consistent?” (or similar), explicitly report:

1. **Substantive:** Match or list any mismatches (categories, definitions, logic).
2. **Notation:** Match or list any symbol/subscript mismatches with appendix.
3. **Terminology:** Match or list any term mismatches.

Do not say “consistent” unless all three are satisfied.
