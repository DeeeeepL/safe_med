#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test desensitization with test_data.txt"""

import sys
sys.path.insert(0, 'd:\\projects\\safe_med')

from safe_med_ui.rule_fallback import FallbackRuleEngine
from safe_med_ui.config_store import ConfigStore
from pathlib import Path

# Load configuration
config = ConfigStore(repo_root=Path('d:\\projects\\safe_med'))
terms = config.load_terms()

# Create engine with all categories enabled
engine = FallbackRuleEngine(
    custom_terms=terms,
    enable_categories={
        "date": True,
        "id_like": True,
        "phone": True,
        "email": True,
        "age": True,
        "doctor_title": True,
        "hospital_dict": True,
        "surnames": True,
        "hospital_suffixes": True,
        "departments": True,
        "custom_sensitive": True,
    }
)

# Read test data
with open('test_data.txt', 'r', encoding='utf-8') as f:
    test_text = f.read()

print("=" * 80)
print("ORIGINAL TEXT (First 30 lines):")
print("=" * 80)
print('\n'.join(test_text.split('\n')[:30]))

print("\n\n" + "=" * 80)
print("DEIDENTIFIED TEXT (First 30 lines):")
print("=" * 80)

result, stats = engine.deidentify(test_text)
print('\n'.join(result.split('\n')[:30]))

print("\n\n" + "=" * 80)
print("STATISTICS:")
print("=" * 80)
for category, count in sorted(stats.items()):
    if count > 0:
        print(f"  {category:25} : {count:3d} items")

print("\n\n" + "=" * 80)
print("HASH MAPPING (ID consistent replacement):")
print("=" * 80)
for original, hashed in sorted(engine.hash_mapping.items()):
    print(f"  {original:30} → {hashed}")

# Save full result
output_file = 'test_data_deidentified.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(result)

print(f"\n✓ Full deidentified text saved to: {output_file}")
