# Publishing H2K-HPXML Package to PyPI

This guide outlines the process to build and publish the H2K-HPXML package to the Python Package Index (PyPI).

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Install Build Tools**:
   ```bash
   pip install --upgrade build twine
   ```

3. **API Tokens**: Configure API tokens for secure publishing:
   - Go to PyPI Account Settings → API tokens
   - Create a token with appropriate scope
   - Store securely (see Authentication section below)

## Package Configuration

The package is already configured with `pyproject.toml`. Key sections:

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "h2k-hpxml"
version = "1.0.0"
description = "H2K to HPXML translation tool for building energy modeling"
```

### Version Management

Update version in `pyproject.toml` before each release:
```toml
version = "1.0.1"  # Follow semantic versioning
```

## Pre-Publication Steps

### 1. Code Quality Checks
```bash
# Run all tests
pytest

# Ensure regression tests pass
pytest tests/integration/test_regression.py -v

# Check for any linting issues (if configured)
# flake8 src/
```

### 2. Documentation Updates
- Update `CHANGELOG.md` with new version changes
- Verify `README.md` is current
- Check all documentation links work

### 3. Clean Build Environment
```bash
# Remove any previous builds
rm -rf dist/ build/ *.egg-info/

# Clean test data
python scripts/clean_test_data.py
```

## Building the Package

### 1. Build Source and Wheel Distributions
```bash
python -m build
```

This creates:
- `dist/h2k-hpxml-{version}.tar.gz` (source distribution)
- `dist/h2k_hpxml-{version}-py3-none-any.whl` (wheel distribution)

### 2. Verify Build Contents
```bash
# Check contents of wheel
python -m zipfile -l dist/h2k_hpxml-*.whl

# Check contents of source distribution
tar -tzf dist/h2k-hpxml-*.tar.gz
```

### 3. Test Local Installation
```bash
# Install in a fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install dist/h2k_hpxml-*.whl

# Test CLI commands
h2k2hpxml --help
h2k-resilience --help

# Test import
python -c "from h2k_hpxml import h2ktohpxml; print('Import successful')"

deactivate
rm -rf test_env
```

## Authentication Setup

### Option 1: API Token (Recommended)
```bash
# Create ~/.pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_API_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

### Option 2: Environment Variables
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_API_TOKEN_HERE
```

## Publishing Process

### 1. Test on TestPyPI First
```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ h2k-hpxml
```

### 2. Publish to PyPI
```bash
# Upload to production PyPI
python -m twine upload dist/*
```

### 3. Verify Publication
```bash
# Check package page
# Visit: https://pypi.org/project/h2k-hpxml/

# Test installation
pip install h2k-hpxml
```

## Post-Publication Steps

### 1. Tag Release in Git
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 2. Create GitHub Release
- Go to GitHub repository → Releases
- Create new release from the tag
- Include changelog and installation instructions

### 3. Update Documentation
- Update installation instructions in README.md
- Notify users of new version
- Update any deployment scripts

## Package Management Commands

### Check Package Info
```bash
# View package metadata
python -m twine check dist/*

# Show package info after upload
pip show h2k-hpxml
```

### Update Existing Package
```bash
# Increment version in pyproject.toml
# Clean and rebuild
rm -rf dist/
python -m build
python -m twine upload dist/*
```

## Troubleshooting

### Common Issues

1. **Version Already Exists**:
   - PyPI doesn't allow re-uploading same version
   - Increment version number in `pyproject.toml`

2. **Missing Files in Package**:
   - Check `[tool.setuptools.package-data]` in `pyproject.toml`
   - Verify files are included in source control

3. **Import Errors After Installation**:
   - Check package structure matches `[tool.setuptools.packages.find]`
   - Verify all `__init__.py` files are present

4. **Console Scripts Not Working**:
   - Check `[project.scripts]` configuration
   - Verify entry point functions exist and are importable

### Testing Package Dependencies
```bash
# Test in clean environment
python -m venv clean_test
source clean_test/bin/activate
pip install h2k-hpxml
# Test all functionality
deactivate
rm -rf clean_test
```

## Security Considerations

1. **Never commit API tokens** to version control
2. **Use tokens with minimal required scope**
3. **Rotate tokens periodically**
4. **Use TestPyPI for testing** before production uploads
5. **Verify package contents** before publishing

## Automated Publishing (Optional)

For automated publishing via GitHub Actions, create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish package
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        user: __token__
        password: ${{ secrets.PYPI_API_TOKEN }}
```

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [setuptools Documentation](https://setuptools.pypa.io/)
- [PyPI Help](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)