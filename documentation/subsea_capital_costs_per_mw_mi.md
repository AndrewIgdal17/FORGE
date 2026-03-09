# Subsea capital costs ($/mi and $/MW-mi) from CTCC

Build costs in CTCC are stored as **variable** ($/mi) and **fixed** ($). For subsea, structure cost is 0. **$/MW-mi** = variable conductor $/mi ÷ line capacity (MW). Values from `yamls/10_project_category_build_costs.yaml`; contingency not applied.

---

## Subsea AC

| Capacity (MW) | Variable conductor ($/mi) | $/MW-mi (variable only) |
|---------------|---------------------------|--------------------------|
| 140           | 2,579,892                 | 18,428                   |
| 329           | 2,579,892                 | 7,842                    |
| 394           | 2,579,892                 | 6,548                    |
| 460           | 4,606,949                 | 10,015                   |
| 657           | 10,958,519                | 16,680                   |
| 1792          | 10,958,519                | 6,115                    |
| 2598          | 10,958,519                | 4,218                    |
| 6625          | 10,958,519                | 1,654                    |

---

## Subsea DC (cable variable only; converter is fixed)

| Capacity (MW) | Variable conductor ($/mi) | $/MW-mi (variable only) |
|---------------|---------------------------|--------------------------|
| 500           | 1,105,668                 | 2,211                    |
| 1500          | 3,685,559                 | 2,457                    |
| 2000          | 3,685,559                 | 1,843                    |
| 2400          | 7,305,679                 | 3,044                    |
| 6000          | 7,305,679                 | 1,218                    |

Converter type (LCC vs VSC) does not change the per-mile cable cost; it only changes the fixed converter cost.
