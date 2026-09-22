# BizScopeAI Analytics Evaluation

## Evaluation Status

- Test framework: pytest
- Python: 3.10.10
- Analytics functions tested: 19
- Total automated tests: 160
- Passed: 160
- Failed: 0
- Errors: 0
- Full-suite execution time: 3.36 seconds

## Dataset

Evaluation dataset:

`dataset/sales_dataset.csv`

Dataset size:

- 1,000 rows
- 14 columns
- Synthetic business sales dataset

## Coverage

The evaluation suite covers:

- Revenue trend analysis
- Product performance
- Regional performance
- Profitability
- Customer performance
- Customer retention
- Customer type analysis
- Category performance
- Monthly performance
- Correlation analysis
- Business comparisons
- Significant changes
- Segment changes
- Change contribution
- Order metrics
- Marketing performance
- Distribution statistics
- Outlier detection

## Validation Types

Tests include:

- Numerical correctness
- Aggregation reconciliation
- Expected business metrics
- Missing-column handling
- Empty-data handling
- Zero-value edge cases
- Multi-row order handling
- Segment appearance/disappearance
- Statistical calculations
- Output structure validation

## Evaluation Result

**160/160 automated tests passed.**

The complete evaluation suite was executed together using:

```powershell
.\venv\Scripts\python.exe -m pytest Evaluation/test_cases -v
```

The full suite completed successfully with no failures or errors.

## Reproducibility

The evaluation is reproducible from the project's test suite:

`Evaluation/test_cases/`

The tests validate the behavior of the analytics functions against the evaluation dataset and targeted edge-case datasets.
