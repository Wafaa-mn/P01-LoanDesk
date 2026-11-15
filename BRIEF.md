# P01 — LoanDesk: campus equipment loans

> This file describes **both versions** of the project: the **team** version (full-time students, 3 per team) and the **solo** version (part-time students, one person). Read `../PROJECT_RULES.md` first: it defines what every project must contain, the output files and the grading. This brief adds only what is specific to this project.
>
> **As-of date: 2026-10-30.** R3 and Q1 compare dates with it (a loan is overdue if DueDate is before the as-of date). Use this fixed date, not today's date, so that your results can be compared with the reference results.

## 1. Scenario

The university's equipment desk lends cameras, laptops, microphones and projectors to students and staff. Staff write a short free-text note at the desk when a device comes back or when a borrower gets in touch. The desk manager wants a review queue of problematic loans: late or overdue loans, damaged or incomplete returns, loans due on a day when the desk is closed, and borrowers holding too many devices.

A desk coordinator reviews each flagged loan and records Confirmed, FalsePositive or NeedsMoreInfo. No real borrower is contacted.

## 2. Team and solo version at a glance

| | Team (3 students) | Solo (1 student) |
|---|---|---|
| Records file | `data/loans_team.csv` (66 rows) | `data/loans_solo.csv` (24 rows) |
| Review rules (Section 6) | R1, R2, R3, R4, R5 | R1, R2, R3 |
| SQL reports (Section 7) | Q1, Q2, Q3, Q4, Q5 | Q1, Q2 |
| App (Section 8) | browse + review (with confirmed codes) + dashboard, approval gate on Resolve | browse + review, approval state shown |
| Flows (Section 9) | F1 with duplicate check and error path, F2, F3 (own idea) | F1, F2 |
| Feedback loop (Section 10) | review of every case, precision per rule, tuning of R3 | — |
| Extensions | two from the menu in `PROJECT_RULES.md`, Section 3.10 | — |

Both records files contain some **invalid rows** on purpose. Your validation must find them (`PROJECT_RULES.md`, Section 3.1).

## 3. Data files (`data/`)

All files are UTF-8 CSV with a header row, comma separator and a decimal **point**. The data is synthetic.

### `assets.csv` — master data, 10 rows

| Column | Type | Meaning |
|---|---|---|
| `AssetID` | text | primary key |
| `AssetName` | text | device name |
| `Category` | text | Camera, Laptop, Audio, Projector, Tablet, Accessory |
| `ReplacementValueHUF` | integer | replacement value in HUF |

### `borrowers.csv` — master data, 10 rows

| Column | Type | Meaning |
|---|---|---|
| `BorrowerID` | text | primary key |
| `BorrowerAlias` | text | synthetic display name |
| `Faculty` | text | faculty |
| `BorrowerType` | text | Student or Staff |
| `MaxOpenLoans` | integer | maximum number of loans not yet returned |

### `loans_team.csv` and `loans_solo.csv` — the records to check (one row = one loan)

| Column | Allowed format | Meaning |
|---|---|---|
| `LoanID` | text, unique | unique loan ID, e.g. L-0001 |
| `AssetID` | must exist in `assets.csv` (`AssetID`) | reference to assets.csv |
| `BorrowerID` | must exist in `borrowers.csv` (`BorrowerID`) | reference to borrowers.csv |
| `Purpose` | one of: `Course`, `Thesis`, `Event`, `Research` | purpose of the loan |
| `LoanDate` | date `YYYY-MM-DD` | YYYY-MM-DD |
| `DueDate` | date `YYYY-MM-DD` | YYYY-MM-DD |
| `ReturnedDate` | date `YYYY-MM-DD`, **may be empty** | YYYY-MM-DD, or empty if the device is still out |
| `DeskNote` | free text | free text written by desk staff (input for Gemini) |

The solo file contains the first 18 valid records of the team file plus the same 6 invalid rows.

### `llm_dev_set.csv` — labelled texts for testing your Gemini prompt

10 texts in the style of `DeskNote`, with the correct answers in the `gold_…` columns (lists are written as JSON, Booleans as `true`/`false`). Use it to measure the accuracy of your extraction (`PROJECT_RULES.md`, Section 3.3).

## 4. Public API

- **API:** Nager.Date public holidays. Documentation: <https://date.nager.at/Api>
- **Example request:** `GET https://date.nager.at/api/v3/PublicHolidays/2026/HU`
- **What you need from it:** The list of Hungarian public holidays in 2026. Use only nationwide entries (`global` is true). The desk is closed on these days.
- **Store it in SQLite as:** `api_holidays (HolidayDate, LocalName, Name)`
- Use every entry whose `global` is true, whatever its `types` value. Store all of them, not only the dates that match a record.
- No API key is needed. Call it politely: cache the responses, so that a rerun does not call the API again.
- Check the documentation yourself; the example shows the idea, not necessarily every parameter you need.

## 5. Gemini extraction

From the free-text column **`DeskNote`** of every accepted record, extract a JSON object with exactly these fields:

| Field | JSON type | Allowed values / meaning |
|---|---|---|
| `item_condition` | string | one of: good, worn, damaged, not_inspected |
| `missing_accessories` | array of strings | accessories reported missing; empty list if none |
| `extension_requested` | boolean | true if the borrower asked to keep the device longer |

Hint for the prompt: Use not_inspected when the device has not been returned yet.

## 6. Review rules

A record that matches a rule gets a **flag**. One record can match several rules. RiskScore of a flag: High = 0.9, Medium = 0.6.

| Rule | ReasonCode | Severity | Input | Condition | Version |
|---|---|---|---|---|---|
| R1 | `DUE_ON_HOLIDAY` | Medium | API | The device is not returned (ReturnedDate empty) and DueDate is a Hungarian public holiday according to the API. | team and solo |
| R2 | `DAMAGED_OR_INCOMPLETE` | High | Gemini | Gemini extracted item_condition = damaged, or missing_accessories is not empty. | team and solo |
| R3 | `LATE_OR_OVERDUE` | High | data | ReturnedDate is after DueDate, or the device is not returned and DueDate is strictly before the as-of date. DueDate equal to the as-of date is not overdue; a return on the due date is not late. | team and solo |
| R4 | `TOO_MANY_OPEN_LOANS` | Medium | data, several rows together | A borrower has more not-returned loans than their MaxOpenLoans. Flag every not-returned loan of that borrower. Exactly MaxOpenLoans is allowed. | team only |
| R5 | `EXTENSION_ON_OVERDUE` | Medium | Gemini + data | Gemini extracted extension_requested = true, the device is not returned (ReturnedDate empty) and DueDate is strictly before the as-of date (the borrower asks for more time when the loan is already overdue). | team only |

**Boundary cases.** Your code must handle these exactly as stated, and your tests must cover them:

- A loan not returned with DueDate equal to the as-of date (2026-10-30) is not overdue (R3).
- A loan returned exactly on DueDate is not late (R3).
- Team: a staff borrower with exactly 4 open loans is not flagged by R4.

## 7. SQL reports

Write each report as one SQL query in `sql/queries.sql` and save its result as `output/sql/Qn.csv`. The result must have exactly these columns, in this order.

| Report | Title | Result columns | Rows and sort order | Version |
|---|---|---|---|---|
| Q1 | Open overdue loans | LoanID, AssetName, BorrowerAlias, DueDate, DaysOverdue | Not returned and DueDate before the as-of date. DaysOverdue = as-of date minus DueDate in days. Sort by DaysOverdue descending, then LoanID. | team and solo |
| Q2 | Loans by faculty | Faculty, LoanCount, OpenLoanCount | One row per faculty that has loans. OpenLoanCount counts loans not yet returned. Sort by Faculty. | team and solo |
| Q3 | Review cases by asset category | Category, LoanCount, CaseCount, HighCaseCount | CaseCount counts loans with at least one flag (a loan counts once, even with several flags). Sort by Category. | team only |
| Q4 | Borrowers over the open-loan limit | BorrowerAlias, BorrowerType, OpenLoans, MaxOpenLoans | Borrowers whose number of not-returned loans is greater than MaxOpenLoans. Sort by BorrowerAlias. | team only |
| Q5 | Borrower ranking within faculty | Faculty, BorrowerAlias, LoanCount, RankInFaculty | One row per borrower with at least one loan. RankInFaculty = rank of the borrower within their faculty by LoanCount, most loans = 1; equal counts share a rank and the next rank is skipped (window function `RANK()`). Sort by Faculty, RankInFaculty, BorrowerAlias. | team only |

If a report needs a value computed in Python (for example a converted amount or a number of working days), store that value in SQLite as well, so the query can use it. Q5 (team) must use a window function (`... OVER (...)`) or a CTE (`WITH ...`), as its description says.

## 8. App

Import `output/cases.csv` into a SharePoint list named **`P01 Review Queue`** (`PROJECT_RULES.md`, Section 3.6). Besides the common case columns, `cases.csv` and the list must contain these context columns, so the reviewer can decide without opening other files:

`AssetName`, `BorrowerAlias`, `DueDate`, `ReturnedDate`, `item_condition`

(Columns from master files, the API or the Gemini extraction are looked up in Python before export.)

## 9. Flows

- **F1 (team and solo):** the Python pipeline sends the run report to your HTTP flow; the flow writes it into the Excel table and answers with a receipt (`PROJECT_RULES.md`, Section 3.7).
- **F2 (team and solo):** the reviewer requests approval from the app; a High case goes to the approver (yourself), a Medium case gets `NotRequired`; the decision is written back to the list (`PROJECT_RULES.md`, Section 3.7).
- **F3 (team only):** your own flow. An idea that fits this project: when a case is set to Confirmed in the list (SharePoint trigger with a trigger condition), create an Outlook calendar reminder for the desk manager on the due date. You may choose another idea, but it must use at least one Power Automate feature that was not covered in class. Send messages only to your own university address or your own Teams chat.

## 10. Review guideline and feedback loop (team only)

The members of a team act as the reviewers described in Section 1. They review **every case** in the app and record which reason codes of the case they confirm. Then the team measures how precise each rule is and tunes one rule (`PROJECT_RULES.md`, Section 3.9).

**Guideline for the reviewers**

1. Check every reason code of the case: is its condition really true? Use the record, the master data and the API values, and **read the original `DeskNote` yourself** instead of trusting the Gemini extraction. A code whose condition is not true (for example because Gemini misread the text) is not confirmed.
2. **Business tolerance for R3 `LATE_OR_OVERDUE`.** The desk manager tolerates a return that is **at most 2 days late**: such a loan is not a real problem, even though R3 flags it. A device that is still out after its due date is never tolerated.
3. `ConfirmedCodes` = the confirmed codes of the case. `ReviewDecision` = `Confirmed` if at least one code is confirmed, `FalsePositive` if none is. Use `NeedsMoreInfo` only if the text really does not allow a decision.
4. `ReviewerNotes`: one sentence; for a code you do not confirm, say why (e.g. *tolerated: within the business tolerance* or *the text does not say this*).

**Rule to tune: R3 `LATE_OR_OVERDUE`.** The rule in Section 6 is stricter than the business tolerance above, so some of its flags will not be confirmed. After the review, measure the precision of every rule, analyse the reviewed R3 flags, and choose a new threshold for R3 from the data: it must remove the flags the reviewers did not confirm and keep every confirmed one. The threshold of Section 6 stays the default of your pipeline (so that `output/` can be compared with the reference); the tuned value is a parameter that writes `output/tuned/`.

## 11. Checklist for this project

- [ ] Rejected rows found with the right reason codes (team: 6 of 66, solo: 6 of 24).
- [ ] API data stored, R1 computed from it.
- [ ] Gemini extraction with JSON schema; accuracy on `llm_dev_set.csv` reported.
- [ ] Rules R1, R2, R3, R4, R5 (team) / R1, R2, R3 (solo), boundary cases tested.
- [ ] SQL reports Q1, Q2, Q3, Q4, Q5 (team) / Q1, Q2 (solo).
- [ ] `P01 Review Queue` list and the review app.
- [ ] Flows F1 and F2 (team: also F3).
- [ ] Team: every case reviewed by the guideline of Section 10; `reviews.csv`, rule precision, R3 tuned with a before/after comparison.
- [ ] Team: two extensions from `PROJECT_RULES.md`, Section 3.10.

The full grading checklist is in `../GRADING_CHECKLIST.md`.
