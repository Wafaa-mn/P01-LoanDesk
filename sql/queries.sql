
-- Q1
-- Open overdue loans
SELECT
    l.LoanID,
    a.AssetName,
    b.BorrowerAlias,
    l.DueDate,
    CAST(
        julianday('2026-10-30') - julianday(l.DueDate)
        AS INTEGER
    ) AS DaysOverdue
FROM loans AS l
JOIN assets AS a
    ON l.AssetID = a.AssetID
JOIN borrowers AS b
    ON l.BorrowerID = b.BorrowerID
WHERE
    l.ReturnedDate IS NULL
    AND date(l.DueDate) < date('2026-10-30')
ORDER BY
    DaysOverdue DESC,
    l.LoanID;


-- Q2
-- Loans by faculty
SELECT
    b.Faculty,
    COUNT(l.LoanID) AS LoanCount,
    SUM(
        CASE
            WHEN l.ReturnedDate IS NULL THEN 1
            ELSE 0
        END
    ) AS OpenLoanCount
FROM loans AS l
JOIN borrowers AS b
    ON l.BorrowerID = b.BorrowerID
GROUP BY
    b.Faculty
ORDER BY
    b.Faculty;


-- Q5
-- Borrower ranking within faculty
WITH borrower_loan_counts AS (
    SELECT
        b.Faculty,
        b.BorrowerAlias,
        COUNT(l.LoanID) AS LoanCount
    FROM borrowers AS b
    JOIN loans AS l
        ON b.BorrowerID = l.BorrowerID
    GROUP BY
        b.BorrowerID,
        b.Faculty,
        b.BorrowerAlias
),
ranked_borrowers AS (
    SELECT
        Faculty,
        BorrowerAlias,
        LoanCount,
        RANK() OVER (
            PARTITION BY Faculty
            ORDER BY LoanCount DESC
        ) AS RankInFaculty
    FROM borrower_loan_counts
)
SELECT
    Faculty,
    BorrowerAlias,
    LoanCount,
    RankInFaculty
FROM ranked_borrowers
ORDER BY
    Faculty,
    RankInFaculty,
    BorrowerAlias;

-- Q3
SELECT
    a.Category,
    COUNT(DISTINCT l.LoanID) AS LoanCount,
    COUNT(DISTINCT c.CaseID) AS CaseCount,
    COUNT(
        DISTINCT CASE
            WHEN c.Severity = 'High' THEN c.CaseID
        END
    ) AS HighCaseCount
FROM loans AS l
JOIN assets AS a
    ON l.AssetID = a.AssetID
LEFT JOIN cases AS c
    ON l.LoanID = c.CaseID
GROUP BY a.Category
ORDER BY a.Category;


-- Q4
SELECT
    b.BorrowerAlias,
    b.BorrowerType,
    COUNT(l.LoanID) AS OpenLoans,
    b.MaxOpenLoans
FROM borrowers AS b
JOIN loans AS l
    ON b.BorrowerID = l.BorrowerID
WHERE l.ReturnedDate IS NULL
GROUP BY
    b.BorrowerID,
    b.BorrowerAlias,
    b.BorrowerType,
    b.MaxOpenLoans
HAVING COUNT(l.LoanID) > b.MaxOpenLoans
ORDER BY b.BorrowerAlias;