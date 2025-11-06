# MATLAB Environment Setup for matRad Tools

## Environment Activation

**IMPORTANT**: Before running any matRad tools or tests, you must activate the MATLAB environment:

```bash
source /Users/ahmadneishabouri/matlab_env/bin/activate
```

## Environment Details

- **Environment Path**: `/Users/ahmadneishabouri/matlab_env/`
- **Python Version**: 3.9.6
- **MATLAB Version**: R2024b
- **MATLAB Engine**: Installed and configured

## Verification

After activating the environment, verify MATLAB Engine is available:

```bash
python -c "import matlab.engine; print('MATLAB Engine successfully imported!')"
```

## Usage in Scripts

When creating scripts that use matRad tools, either:

1. **Activate environment first** (recommended):
   ```bash
   source /Users/ahmadneishabouri/matlab_env/bin/activate
   python your_script.py
   ```

2. **Use full path to environment python**:
   ```bash
   /Users/ahmadneishabouri/matlab_env/bin/python your_script.py
   ```

## Test Scripts

All test scripts should be run with the activated environment:

```bash
source /Users/ahmadneishabouri/matlab_env/bin/activate
cd /Users/ahmadneishabouri/matRad
python test_objectives_constraints.py
```

## Troubleshooting

If you get `ModuleNotFoundError: No module named 'matlab'`:
1. Ensure the environment is activated
2. Check that MATLAB Engine is installed in the environment
3. Verify MATLAB R2024b is installed at `/Applications/MATLAB_R2024b.app/`

## Installation Notes

The MATLAB Engine for Python was installed using:
```bash
cd /Applications/MATLAB_R2024b.app/extern/engines/python
python setup.py build --build-base=/tmp install --user
```

This installation is specific to the matlab_env environment.
