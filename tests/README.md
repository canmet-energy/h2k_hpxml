# Testing Guide

This testing framework provides comprehensive regression testing for the H2K to HPXML translation pipeline using golden file comparisons.

## Prerequisites

- Python environment with all dependencies installed
- OpenStudio-HPXML configured and available
- H2K example files in the `examples/` directory

## Running Tests

### Standard Test Suite
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest -m "not baseline_generation"  # Normal tests only
pytest tests/integration/            # Integration tests
pytest tests/unit/                   # Unit tests
```

### Regression Testing

#### Combined Regression Test (Recommended)
```bash
# Run regression test (energy + HPXML validation)
pytest tests/integration/test_regression.py -v -s
```

This test is **~50% faster** than running separate tests because it:
- Runs each H2K file once through the simulation pipeline
- Validates both energy data (with 5% tolerance) and HPXML structure (exact match) in a single pass
- Provides comprehensive reporting for both validation types

#### Individual Test Types (Less Efficient)
```bash
# Run energy data regression tests only
pytest tests/integration/test_energy_comparison.py -v

# Run HPXML structure regression tests only
pytest tests/integration/test_hpxml_comparison.py -v

# Run unit tests (fast)
pytest tests/unit/ -v
```

## Golden File Management

### Generating New Baselines
**⚠️ WARNING: Only run baseline generation with verified, stable code**

```bash
# Generate fresh golden files (requires CI=true to skip confirmation)
CI=true pytest tests/integration/test_generate_baseline.py --run-baseline -v -s
```

### Cleaning Test Data
```bash
# Clean all test data
python scripts/clean_test_data.py

# Clean only for baseline generation (preserves existing baselines)
python scripts/clean_test_data.py --baseline-only

# Preview what would be cleaned
python scripts/clean_test_data.py --dry-run
```

## Test Data Structure

```
tests/
├── fixtures/expected_outputs/golden_files/
│   ├── baseline/           # Golden master files
│   └── comparison/         # Test comparison outputs
├── temp/                   # Temporary simulation outputs
└── utils/                  # Shared test utilities
```

## Development Workflow

### Before Committing Code
1. **Run all tests**: `pytest`
2. **Ensure tests pass**: All tests must pass or be updated for new features
3. **Update baselines if needed**: Only when output format changes intentionally
4. **Clean test data**: Use `python scripts/clean_test_data.py` for fresh runs

### When Output Changes
1. **Verify changes are intentional**: Review differences carefully
2. **Update golden files**: `CI=true pytest tests/integration/test_generate_baseline.py --run-baseline -v -s`
3. **Test against new baselines**: `pytest tests/integration/test_regression.py -v -s`

### Adding New Tests
1. **Use existing utilities**: Import from `tests.utils`
2. **Follow golden file pattern**: Compare against baseline files
3. **Include cleanup**: Use `clean_for_baseline_generation()` before baseline creation

## Test Categories

- **Energy Data Regression**: Compares annual energy consumption values
- **HPXML Structure Validation**: Verifies XML structure and key elements
- **Baseline Generation**: Creates fresh golden files from simulation runs
- **Cleanup Management**: Ensures fresh test environments

## Key Commands Reference

```bash
# Essential test commands
pytest                                              # Run all tests
pytest -v                                          # Verbose output  
pytest -m "not baseline_generation"                # Skip baseline generation
pytest tests/integration/test_regression.py -v -s  # Regression test (recommended)
CI=true pytest --run-baseline -v -s                # Generate new baselines
python scripts/clean_test_data.py                          # Clean test data
```

## Notes

- Golden files are backed up automatically during baseline generation
- Test data is cleaned automatically before baseline generation
- All tests must pass before code commits
- Baseline generation should only be done with verified stable code