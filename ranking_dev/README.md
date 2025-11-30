# Ranking Development Folder

Temporary folder for developing and testing ranking components before merging.

## Structure
- `schema.sql` - Database table definitions
- `schema.py` - Python schema management
- `repository.py` - Database CRUD operations
- `rs_rating.py` - RS Rating calculator
- `momentum.py` - Momentum Score calculator
- `trend_template.py` - Trend Template calculator
- `technical.py` - Technical Score calculator
- `composite.py` - Composite Score calculator
- `orchestrator.py` - Ranking orchestrator
- `test_*.py` - Test files for each component

## Workflow
1. Develop each component
2. Test independently
3. Merge to ranking/ folder
