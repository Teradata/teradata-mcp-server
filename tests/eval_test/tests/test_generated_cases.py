from __future__ import annotations

import importlib

# Import the generated-case module so pytest can collect the dynamically registered
# test functions from this test module.
_generated_cases = importlib.import_module("tests.generated_cases")

for _name in dir(_generated_cases):
    if _name.startswith("test_") and callable(getattr(_generated_cases, _name)):
        globals()[_name] = getattr(_generated_cases, _name)
