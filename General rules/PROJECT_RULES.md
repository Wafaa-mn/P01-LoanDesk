# Final project — common rules

Course: *Data-driven Application Development* (MSc Data Science, University of Debrecen).

This file is the same for all ten projects. Your project's `BRIEF.md` adds the data, the API, the rules and the reports that are specific to your project. If the two seem to contradict each other, the brief wins; if something is still unclear, ask your instructor.

## 1. What you build

Every project is the same kind of system: a small **review pipeline**. Records arrive in a CSV file; some are invalid, some are risky. Your system finds the risky ones and lets a person review them.

```text
data/*.csv ──► Python pipeline ──────────────► SQLite database ──► SQL reports
                 │  validation                    (output/project.sqlite)   (output/sql/Qn.csv)
                 │  public API (context data)
                 │  Gemini (JSON extraction from free text)
                 │  review rules → flags → cases
                 ▼
            output/cases.csv ──► SharePoint list ──► Power Apps review app ──► F2 approval flow
                 │
                 └─ run report (JSON) ──HTTP──► F1 Power Automate flow ──► Excel table + receipt

Team only: review decisions ──► back into SQLite ──► precision per rule ──► one rule tuned (feedback loop)
```

You use everything from Weeks 1–11: Python and `requests` (Weeks 1–2), Gemini with structured output (Week 3), SQLite (Weeks 4–5), Microsoft Lists and Power Apps (Weeks 6–7), Power Automate (Weeks 8–11).

## 2. Team and solo

| | Team (full-time, 3 students) | Solo (part-time, 1 student) |
|---|---|---|
| Records file | `<records>_team.csv` (66 rows) | `<records>_solo.csv` (24 rows) |
| Review rules | R1–R5 | R1–R3 |
| SQL reports | Q1–Q5 (Q5 with a window function or CTE) | Q1–Q2 |
| Tests | at least 25 | at least 8 |
| App | browse, review with confirmed codes, dashboard; approval gate on Resolve | browse, review, approval state |
| Flows | F1 with duplicate check and error path; F2; F3 (own idea) | F1; F2 |
| Feedback loop (3.9) | review of every case, precision per rule, tuning of one rule | — |
| Extensions (3.10) | two from the menu | — |
| Live demo | 20 minutes | 10 minutes |

**Time:** 6 weeks, at home. Plan with about **120–170 hours for a team** in total (7–9 hours per person per week) and about **45–65 hours for a solo student** (8–11 hours per week). **Tools:** every tool is allowed, including AI assistants (Section 6).

A possible plan (one milestone per week):

| Week | Milestone (team and solo) | Team in addition |
|---|---|---|
| 1 | Repository and README skeleton; data loaded; validation and its tests | division of work; choose the two extensions |
| 2 | API client and SQLite schema; first SQL reports | Q5 |
| 3 | Gemini extraction and its evaluation on the dev set; review rules and cases | R5; start the extensions |
| 4 | SharePoint list and the review app | dashboard, approval gate, confirmed codes |
| 5 | Flows F1 and F2 | F3; review of every case, precision, tuning |
| 6 | End-to-end run, documentation, rehearsal of the demo | the two extensions finished |

A team divides the work, for example *pipeline, API and tuning* / *Gemini, SQL and one extension* / *app, flows and one extension*, but every member reviews cases and must be able to explain the whole system (Section 7).

## 3. Requirements

### 3.1 Python pipeline and validation

- One documented command runs the whole local pipeline, for example `python main.py --scope team` (or `--scope solo`). It reads the files in `data/` and writes everything into `output/`. Running it again gives the same results and does not duplicate anything.
- The **as-of date** for all date rules is **2026-10-30**. Keep it as a constant, not today's date.
- **Validation** of the records file. Check every row in this order; the **first** failed check decides the reason code, and the row is rejected:

| Order | ReasonCode | The row is rejected if … |
|---|---|---|
| 1 | `MISSING_ID` | the ID column (first column) is empty |
| 2 | `DUPLICATE_ID` | the ID already appeared in an **earlier** row, whether that row was accepted or rejected (the earlier row keeps its own result) |
| 3 | `UNKNOWN_REFERENCE` | a reference column is empty or contains a key that does not exist in its master file |
| 4 | `INVALID_DATE` | a date is empty, not in the format given in the brief, or not a real date (e.g. 2026-02-30). Exception: a date the brief marks as *may be empty* |
| 5 | `INVALID_VALUE` | any other column breaks its format in the brief: not a number (a decimal **comma** is not accepted), outside the allowed range, not one of the allowed values (case-sensitive), or a Boolean other than `TRUE`/`FALSE` |

- Write `output/rejected_rows.csv` with the columns `SourceRow, RecordID, ReasonCode`. `SourceRow` is the line number in the CSV file, where the header is line 1 (so the first data row is 2). Strip spaces around values before checking.
- Only accepted rows go further.
- Do **not** add other checks (for example dates in the future, or a registration date after the session). They would change your counts compared with the reference. You may mention such ideas in the README as possible improvements.

### 3.2 Public API

- Call the real public API named in the brief over HTTP from Python (`requests`), with an explicit **timeout**.
- If a call fails, the run stops with a clear message. Never continue with invented default values.
- Save the raw responses (for example under `output/api_cache/`) and reuse them on the next run, so that a rerun does not call the API again. Delete the cache to force fresh calls.
- Store the values you use in the SQLite table named in the brief.
- Tests must not call the real API: use saved sample responses or fakes (`monkeypatch`, as in Week 10).

### 3.3 Gemini extraction

- For every accepted record, send the free-text column named in the brief to Gemini and receive a JSON object with exactly the fields of the brief. The field definitions in the brief are the reference; the dev set below is only a sample of typical texts. Use the model from Week 3 (`gemini-3.1-flash-lite`) or a newer available Gemini model.
- Use **structured output**: send the JSON schema with the request (`response_mime_type="application/json"` and `response_json_schema=...`, as in Week 3) and **validate** every answer in Python (for example with a Pydantic model). An answer that fails validation is retried once. An API error (for example HTTP 429, too many requests) is retried at most three times with a pause. If a record still has no valid answer, it gets `ExtractionStatus = failed` (see below), the Gemini rules (R2; team: also R5) are not evaluated for it, and the run summary prints how many records failed.
- Cache the answers (for example in `output/llm_cache.json`) so a rerun does not call Gemini again.
- Store the results in the SQLite table `extractions` and in `output/extractions.csv`, one row per accepted record: `RecordID`, one column per field of the brief (lists as JSON text, Booleans as `true`/`false`), and `ExtractionStatus` (`ok` or `failed`; the fields are empty for a failed record).
- **Evaluate** your prompt on `data/llm_dev_set.csv`: run the same extraction on the 10 texts and compare with the `gold_…` columns. Write `output/llm_dev_eval.csv` (one row per text and field: `DevID, Field, Gold, Predicted, Correct`). A prediction is correct if it equals the gold value after normalisation: text compared exactly (allowed values are lower case), Booleans as `true`/`false`, numbers numerically (`7` = `7.0`), lists as sets (order and upper/lower case ignored) and report the accuracy per field in the README. Aim for at least 80 % per field; if you are below, describe in the README what you changed in the prompt and why some cases are still wrong.
- The API key is read from the environment variable `GEMINI_API_KEY`. It never appears in code, Git, screenshots or the README.

### 3.4 Review rules, flags and cases

- Implement the rules of your version exactly as written in the brief, including the boundary cases.
- `output/flags.csv`: one row per matched rule and record, columns `RecordID, RuleID, ReasonCode, Severity, RiskScore` (High = 0.9, Medium = 0.6), sorted by RecordID, then RuleID.
- `output/cases.csv`: one row per record with at least one flag:

| Column | Content |
|---|---|
| `CaseID` | the record ID |
| `Severity` | `High` if the record has at least one High flag, otherwise `Medium` |
| `RiskScore` | the largest RiskScore of its flags |
| `ReasonCodes` | its reason codes joined with `;`, in rule order (R1 first) |
| `Status` | always `New` (the review starts in the app) |
| context columns | the columns listed in the brief, Section 8 |

Sort by RiskScore descending, then CaseID.

- **Tests** (`pytest`): team at least 25, solo at least 8. Cover every reason code of the validation, every rule, and every boundary case of the brief; the team also tests the import of the reviews, the precision calculation and the tuned threshold (Section 3.9). No test may call the real API, Gemini or a flow.

### 3.5 SQLite and SQL reports

- Build `output/project.sqlite` in every run from scratch (no duplicate rows after a rerun).
- Tables: the master tables (as in `data/`, same names), the records table (accepted rows only; named after the records file **without** `_team`/`_solo`, e.g. `loans`, `purchases`), the API table(s) of the brief, `extractions`, `flags`, `cases`, and any table you need for values computed in Python. Team: also `reviews` and `review_codes` (Section 3.9). Declare **primary keys** and **foreign keys**.
- Write each report of your version (team Q1–Q5, solo Q1–Q2) as one SQL query in `sql/queries.sql`. Put a marker line `-- Q1`, `-- Q2`, … before each query, so that Python can split the file. Run the queries from Python and save the results as `output/sql/Q1.csv`, `Q2.csv`, … with exactly the columns and sort order of the brief.
- Team: Q5 needs a window function (`RANK() OVER (...)`, `LAG(...) OVER (...)`, `SUM(...) OVER (...)`) or a CTE (`WITH ...`), as its description in the brief says. Python's built-in `sqlite3` supports both (SQLite 3.25 or newer; check with `sqlite3.sqlite_version`).
- Results are compared with the reference numerically (`8` = `8.0`); round only where the brief says so.
- Put a schema diagram (tables, keys, relations) in the README. A hand-drawn photo, a Mermaid diagram or a screenshot are all fine.

### 3.6 App (Power Apps)

Build the app from a **blank canvas app**, as in Weeks 6–7 (not *Create an app from data*).

1. **List:** import `output/cases.csv` into a SharePoint list named `<Pxx> Review Queue` (e.g. `P03 Review Queue`), with **Create from CSV** (Week 6). Set the column types in the import dialog:

| Column from `cases.csv` | Type in the list |
|---|---|
| `CaseID` | the `Title` column |
| `Severity` | Choice: High, Medium |
| `RiskScore` | Number, 1 decimal |
| `ReasonCodes` | Single line of text |
| `Status` | Choice: New, InReview, Resolved |
| context columns | Number for numbers, Date for dates (date only), Single line of text for everything else |

Then add the review columns:

| Column | Type | Values |
|---|---|---|
| `ReviewDecision` | Choice | Confirmed, FalsePositive, NeedsMoreInfo |
| `ReviewerNotes` | Multiple lines of text | |
| `ResolvedDate` | Date | set to today by **Resolve** |
| `ApprovalStatus`, `ApprovalComment`, `ApprovalDate` | text, multiple lines of text, date and time | written by flow F2 (Week 9) |
| `ConfirmedCodes` (team) | Single line of text | the reason codes the reviewer confirms, joined with `;` (Section 3.9) |

2. **Browse screen:** a gallery of the cases with the key context columns, sorted by RiskScore (highest first), with a Severity filter, a Status filter and a CaseID search.
3. **Review screen:** all context columns of the case, the decision and the notes. Saving requires non-empty notes. **Start review** sets InReview; **Resolve** is allowed only for an InReview case with a decision that is not NeedsMoreInfo and with notes (Week 7). Show a success or error message after every save.
   - **Team:** the reviewer picks the confirmed codes from the case's own reason codes (for example a combo box with multiple selection whose items come from `Split(ThisItem.ReasonCodes, ";")`, saved with `Concat(...)`; use the formula separators of your Power Apps language setting, as in Week 6). Saving is refused if the decision does not fit the codes: `Confirmed` needs at least one confirmed code, `FalsePositive` none.
4. **Solo — approval state:** the review screen shows `ApprovalStatus` and `ApprovalComment`, with a **Refresh** button (the approver answers outside the app, Week 9).
5. **Team only — dashboard screen:** at least three numbers or charts, for example cases by Severity, by Status, and by ReasonCode.
6. **Team only — approval state and gate:** as for solo, plus: a High case can be resolved only when its `ApprovalStatus` is `Approved` (Week 9).

### 3.7 Flows (Power Automate)

**F1 — run report (team and solo).** At the end of the pipeline, Python sends one JSON report to an HTTP-triggered flow (Weeks 10–11). The URL is read from the environment variable `FLOW_URL`; a separate command or option sends it, so that a local rerun does not send a report by accident (for example `python main.py --scope team --send-report`).

Report (exactly these keys):

```json
{
  "run_id": "6f1d2c3e-8a4b-4c5d-9e6f-0a1b2c3d4e5f",
  "project_id": "P03",
  "scope": "team",
  "generated_at": "2026-12-01T10:15:00+01:00",
  "record_count": 66,
  "accepted_count": 60,
  "rejected_count": 6,
  "case_count": 31,
  "high_case_count": 17
}
```

(Illustrative values. `run_id` is a new UUID for every run, `generated_at` is ISO 8601 with UTC offset, `scope` is `team` or `solo`, the counts are integers.)

The flow adds one row to the table `tblProjectRuns` of an Excel workbook in your OneDrive (upload `templates/project_runs_template.xlsx`; the table already exists in it):

| Excel column | Value |
|---|---|
| `RunID`, `ProjectID`, `Scope` | `run_id`, `project_id`, `scope` |
| `ReceivedAt` | the time the **flow** received the report, Budapest time, `yyyy-MM-dd HH:mm:ss` (Week 11) |
| `RecordCount` … `HighCaseCount` | the five counts |
| `Alert` | `Yes` or `No` |

and answers:

```json
{"run_id": "<the same run_id>", "status": "recorded", "alert": true}
```

`alert` is a JSON Boolean: `true` if `high_case_count` > 0. Python checks the receipt (same `run_id`, known status, Boolean `alert`) and saves it as `output/flow_receipt.json`. The flow sends you an alert email when `alert` is true.

The Python client sends exactly one request with a timeout and never retries automatically. A timeout, a non-2xx answer and an invalid receipt each end with a clear message, not a traceback (Week 10, Task 2).

- **Team in addition:** sending the same report again (same `run_id`) is answered with `"status": "duplicate"` and adds no row; a Try/Catch error path answers HTTP 500 and notifies you (Week 11).

**Licence:** the HTTP trigger of F1 is a premium feature. Check in the first week that you can save a flow with it (premium licence or trial); ask your instructor if you cannot. In a team, one member can own the flow.

**F2 — approval (team and solo).** The same pattern as Week 9, Task 1. The reviewer presses **Request approval** on the review screen; the flow (Power Apps (V2) trigger, input = the list item ID):

| Case | Flow writes | Answer to the app |
|---|---|---|
| `Status` is Resolved, or `ApprovalStatus` is already Pending or Approved | nothing | not accepted, with a message |
| `Severity` is Medium | `ApprovalStatus = NotRequired`, date | accepted, "no approval required" |
| `Severity` is High | `Pending`; after the approver (yourself) answered: `Approved` or `Rejected`, comment, date | accepted, "approval requested" — at once, before the approval |

**F3 — your own flow (team only).** One more flow that is useful for your scenario and uses **at least one Power Automate feature that was not covered in class** (for example: a Teams adaptive card with buttons, a trigger condition, a SharePoint *When an item is created or modified* trigger, a child flow, parallel branches, a Do until loop, a Word template or PDF conversion, an Outlook calendar event, a Planner task). Triggers and actions used in Weeks 8–11 (manual, Forms, Recurrence, RSS, Power Apps, HTTP, Approvals, Excel, Scopes) do not count as new. The brief suggests an idea. Document it in the README: purpose, trigger, steps, the new feature, a screenshot of a successful run.

Messages and approvals go only to your own university address or your own Teams chat.

### 3.8 Documentation and demo

- `README.md`: the architecture (a diagram), setup, environment variables (names only), the commands, the schema diagram, the Gemini accuracy, the description of F3 (team), the feedback loop and the two extensions (team), known limitations.
- `AI_USAGE_LOG.md`: which AI tools you used for what, and at least **three** cases where you had to check or correct an AI answer (template in `templates/`).
- `CONTRIBUTIONS.md` (team): who did what, and which cross-check each member did on another member's part.
- **Live demo** (team 20 min, solo 10 min), in this order:
  1. Run the pipeline from the raw CSV files; show accepted/rejected counts and one boundary case. The API and Gemini caches may be used; be ready to delete one cache file and show a live call.
  2. Show two SQL reports and explain one join and what one aggregate counts.
  3. Open the app: filter, review one case, try to save without notes, resolve a case.
  4. Request an approval (F2), approve it, show the result in the app.
  5. Send the run report (F1); show the receipt, the run history and the Excel row. Team: send it again (duplicate) and show F3.
  6. Team: the feedback loop — the precision table, the analysis of the tuned rule, a run with the tuned parameter and the before/after table.
  7. Team: the two extensions (about 2 minutes each).

### 3.9 Feedback loop (team only)

A review queue is only useful if its rules are precise. In this part the team uses the reviewers' decisions to measure each rule and to tune one of them. The brief (Section 10) gives the **guideline** for the reviewers and names the **rule to tune**.

1. **Review every case** in the app, following the guideline of the brief: `ReviewDecision`, `ConfirmedCodes` and `ReviewerNotes` for each case. Every member reviews about a third of the cases (the list's *Modified By* column shows who). Resolving the cases is not required for this part.
2. **Bring the decisions back.** Export the list (in Lists: *Export → Export to CSV*, or with a flow or any other way you document) and import it with a separate command, for example `python main.py --scope team --import-reviews <exported file>`. The import:
   - writes `output/reviews.csv` with the columns `CaseID, ReviewDecision, ConfirmedCodes, ReviewerNotes` (one row per case; codes joined with `;` in rule order);
   - prints the problems it finds: a CaseID that is not in `cases.csv`, a case without a decision, a confirmed code that is not one of the case's reason codes, a decision that does not fit the codes (see Section 3.6).
   
   Whenever `output/reviews.csv` exists, every run loads it into SQLite: `reviews` (primary key CaseID, foreign key to `cases`) and `review_codes` (CaseID, ReasonCode; one row per confirmed code; primary key on both columns). If a later run no longer has a case of `reviews.csv` (for example after a change in the extraction), skip that row and print a warning.
3. **Precision per rule.** Write one SQL query with the marker `-- PRECISION` in `sql/queries.sql` and save its result as `output/rule_precision.csv`, one row per rule that has flags, sorted by RuleID:

| Column | Meaning |
|---|---|
| `RuleID`, `ReasonCode` | the rule |
| `Flags` | all flags of the rule in `flags.csv` |
| `Confirmed` | flags of reviewed cases whose code is in `ConfirmedCodes` (*reviewed* = decision `Confirmed` or `FalsePositive`) |
| `NotConfirmed` | flags of reviewed cases whose code is not in `ConfirmedCodes` |
| `Excluded` | flags of cases with `NeedsMoreInfo` or without a decision |
| `Precision` | Confirmed / (Confirmed + NotConfirmed), rounded to 2 decimals; empty if nothing was reviewed |

4. **Tune the rule named in the brief.**
   - **Analyse** the reviewed flags of that rule: a table and a chart (PNG, for example with matplotlib) that show how the value behind the rule (days late, percent over capacity, …) relates to the decision.
   - **Choose the new threshold from the data:** it removes the flags that were not confirmed and keeps every confirmed one. Explain the choice in one paragraph.
   - **Make the threshold a parameter** (a command-line option or a config file). Its default stays the threshold of the brief, so that `output/` remains comparable with the reference.
   - **Run with the tuned value** into `output/tuned/` (`flags.csv`, `cases.csv`). Thanks to the caches, this run calls neither Gemini nor the API again. The tuned cases do not have to be imported into the list.
   - Write `output/tuning_before_after.csv`, two rows (`before`, `after`):

| Column | Meaning |
|---|---|
| `Version` | `before` (brief threshold) or `after` (tuned threshold) |
| `RuleID` | the tuned rule |
| `Setting` | the threshold as short text, e.g. `tolerance = 2 days` |
| `RuleFlags`, `ConfirmedFlags`, `NotConfirmedFlags`, `Precision` | as in `rule_precision.csv`, for the tuned rule only, using the reviews you already have |
| `TotalCases` | number of rows of `cases.csv` (before) or `tuned/cases.csv` (after) |

5. **README section *Feedback loop*:** the precision table, the analysis and the chart, the before/after table, and a short conclusion: how many fewer cases a reviewer has to look at, and why no confirmed flag was lost. Mention which rules lost precision because of Gemini errors.

### 3.10 Extensions (team only)

Choose **two** of the six extensions below and write your choice in the README in the first week. Each one is graded on its acceptance criteria. Document each in the README: what it does, how to run it, evidence (screenshots or a link), and what you checked.

| ID | Extension | Acceptance criteria |
|---|---|---|
| X1 | **Power BI report** on the review queue | Power BI Desktop (Windows) or the Power BI service; data from the SharePoint list (and, if you like, the CSV files in `output/`); at least 3 visuals, including cases by ReasonCode and the precision per rule; at least one slicer; refreshed after a change in the list (show it); `.pbix` or screenshots in `powerplatform/`. |
| X2 | **Python web API called by a flow** | A small FastAPI or Flask app deployed to a public host (a flow cannot reach `localhost`); at least one endpoint that answers from your data (for example the summary of one case); a secret header checked by the API, its value read from an environment variable; a flow that calls the API with the HTTP action and uses the answer; tests for the endpoint; synthetic data only. |
| X3 | **Gemini case summaries with evaluation** | For every case, a summary of 1–2 sentences for the reviewer from the record, its context columns and its reason codes, with structured output (for example `{"summary": ..., "mentioned_codes": [...]}`) and a cache; stored in `output/case_summaries.csv` and in a list column `CaseSummary` shown in the app; 10 summaries rated independently by two members (no invented fact / all reason codes mentioned / useful 1–3) with a table and the agreement in the README. |
| X4 | **Data-quality report** | One command writes `output/data_quality.html` (or `.md`): for every column the type, the empty values, the distinct values, min and max or the most frequent values; a chart for every numeric and date column; the rejected rows by reason code; three written observations. A generated library report (e.g. ydata-profiling) may be added, but the parts above come from your own code. |
| X5 | **Streamlit or Dash dashboard** | Reads `output/project.sqlite`; starts with one documented command; at least 3 views: the case list with filters, the precision per rule, and one chart about your domain; screenshots in the README. |
| X6 | **Continuous integration** | A GitHub Actions workflow that, on every push, installs the requirements and runs a linter (e.g. ruff) and `pytest`; needs no secret (the tests use fakes); a status badge in the README; one failing run and its fix shown (link or screenshot). |

## 4. What to submit

A ZIP file or a Git repository link (private, shared with the instructor), with this structure:

```text
README.md
AI_USAGE_LOG.md
CONTRIBUTIONS.md          (team)
requirements.txt
main.py                   (or another documented entry point)
src/                      your Python modules
tests/                    pytest tests
sql/queries.sql
data/                     the files of your brief, unchanged
output/                   the result of your final run (without the caches if they are large);
                          team: also reviews.csv, rule_precision.csv, tuning_before_after.csv, tuned/
powerplatform/            app export (.msapp) if available, flow screenshots, the Excel workbook
```

Do not submit `.env` files, API keys, flow URLs or real personal data.

## 5. Grading

90 points for the project (the same for every team member) + 10 points for each student's individual defence. The full checklist with points is in `GRADING_CHECKLIST.md`; the instructor uses the same list. The team version has more parts, so its 90 points are spread over more items.

| Component | Team | Solo |
|---|---:|---:|
| A. Python pipeline and validation | 10 | 12 |
| B. Public API | 8 | 10 |
| C. Gemini extraction | 10 | 14 |
| D. Review rules and cases | 10 | 10 |
| E. SQLite and SQL reports | 10 | 12 |
| F. App | 12 | 16 |
| G. Flows | 10 | 12 |
| H. Documentation and demo | 2 | 4 |
| J. Feedback loop | 12 | — |
| K. Extensions | 6 | — |
| **Project total** | **90** | **90** |
| I. Individual defence | 10 | 10 |

Your results are compared with the instructor's reference results (computed from the same data, the same API and correct extractions). Small differences in the Gemini part are expected; explain them.

## 6. AI tools

You may use any AI assistant for code, SQL, Power Fx, flows and documentation. Three conditions:

1. Record the important uses in `AI_USAGE_LOG.md`, including what you checked and corrected.
2. Never paste API keys, flow URLs or personal data into a prompt.
3. You must understand and be able to change everything you submit. The individual defence (Section 7) checks this.

## 7. Individual defence (10 points)

During or after the demo, every student, one by one:

| | Points |
|---|---:|
| Explains a part they built, live in the code, the app or the flow | 4 |
| Answers two questions about a part built by another member (solo: about a design decision) | 3 |
| Makes a small change on request and shows the effect (e.g. change a rule threshold and rerun; add a column to the gallery) | 3 |
