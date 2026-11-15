# Final project — Data-driven Application Development

The course ends with a project that uses every part of the course: **Python + public API + Gemini + SQL + app + flows**. You have **6 weeks** and you work **at home**. Every tool is allowed, including AI assistants.

- **Full-time students** work in **teams of 3** on the **team version**: more rules and reports, a feedback loop that measures and tunes the rules with the reviewers' decisions, and two extensions of your choice.
- **Part-time students** work **alone** on the **solo version** (a smaller part of the same project).

## Start here

1. Read `PROJECT_RULES.md` — what every project must contain, the output files, the demo and the grading.
2. Open the folder of your project (your instructor tells you which one) and read its `BRIEF.md`. Both versions are in the same brief.
3. Look at `GRADING_CHECKLIST.md` — the instructor grades with exactly this list.
4. Copy the `templates/` you need into your repository.

## The ten projects

All data is synthetic. Every project has the same structure: master files, a records file with some invalid rows, a free-text column for Gemini, a real public API, review rules, SQL reports, an app and flows (team: also a feedback loop).

| Project | Scenario | Records | Free text for Gemini | Public API |
|---|---|---|---|---|
| `P01_loandesk` | **LoanDesk**: campus equipment loans | loans | `DeskNote` | Nager.Date public holidays |
| `P02_fieldworks` | **FieldWorks**: outdoor maintenance planning | work orders | `RequestText` | Open-Meteo Historical Weather API |
| `P03_stockbridge` | **StockBridge**: purchase proposals and stock review | purchases | `SupplierMessage` | Frankfurter exchange rates |
| `P04_eventplan` | **EventPlan**: room booking review | bookings | `RequestText` | Nager.Date public holidays |
| `P05_parcelwatch` | **ParcelWatch**: delivery promise review | deliveries | `CustomerNote` | Nager.Date public holidays |
| `P06_grantcheck` | **GrantCheck**: mobility expense claims | claims | `ClaimNote` | Frankfurter exchange rates |
| `P07_repairqueue` | **RepairQueue**: IT repair desk tickets | tickets | `ProblemDescription` | endoflife.date API |
| `P08_energylens` | **EnergyLens**: campus electricity readings | readings | `TechnicianNote` | Open-Meteo Historical Weather API |
| `P09_skillsroster` | **SkillsRoster**: international training registrations | registrations | `RegistrationComment` | Nager.Date public holidays |
| `P10_catalogcheck` | **CatalogCheck**: library acquisitions | acquisitions | `CatalogerNote` | Open Library Search API |

## Folder contents

```text
README.md                this file
PROJECT_RULES.md         common requirements (read first)
GRADING_CHECKLIST.md     grading items and points
templates/
  project_runs_template.xlsx   Excel table tblProjectRuns for flow F1
  AI_USAGE_LOG_template.md     template for your AI usage log
  README_template.md           skeleton for your project README
Pxx_name/
  BRIEF.md               your project: scenario, data, API, Gemini fields, rules, reports, app, flows
  data/                  master files, records (team and solo), llm_dev_set.csv
```
