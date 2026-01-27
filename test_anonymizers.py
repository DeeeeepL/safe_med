#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify anonymizers integration in rule_fallback.py
"""

import sys
sys.path.insert(0, 'd:\\projects\\safe_med')

from safe_med_ui.rule_fallback import FallbackRuleEngine
from safe_med_ui.config_store import ConfigStore
import json

# Load configuration
config = ConfigStore()
config.load()

# Create engine with all categories enabled
engine = FallbackRuleEngine(
    custom_terms=config.custom_terms,
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

# Test cases
test_cases = [
    ("患者年龄：45岁", "Age anonymization"),
    ("日期：2023-12-15", "Date anonymization"),
    ("身份证：110101197812345678", "ID anonymization"),
    ("医生：李四主治医师", "Doctor title anonymization"),
    ("医院：北京协和医院", "Hospital anonymization"),
    ("姓名：张三", "Name/surname anonymization"),
    ("地点：医疗中心", "Location/suffix anonymization"),
]

print("=" * 70)
print("ANONYMIZERS INTEGRATION TEST")
print("=" * 70)

for text, description in test_cases:
    result, stats = engine.deidentify(text)
    print(f"\n{description}:")
    print(f"  Original: {text}")
    print(f"  Result:   {result}")
    print(f"  Stats:    {stats}")

print("\n" + "=" * 70)
print("Full medical record test:")
print("=" * 70)

medical_record = """
患者姓名：张三
性别：男
年龄：45岁
身份证：110101197812345678
门诊日期：2023-12-15
就诊医院：北京协和医院
接诊医生：李四主治医师
电话号码：13812345678
邮箱：patient@example.com
诊断：患者于2023-10-20初诊，主要症状为头痛。
医疗机构类型：三甲医院
科室：心内科
备注：患者为高危人群，需要定期随访。
"""

result, stats = engine.deidentify(medical_record)
print("\nOriginal record:")
print(medical_record)
print("\n" + "-" * 70)
print("Anonymized record:")
print(result)
print("\n" + "-" * 70)
print("Desensitization statistics:")
for category, count in stats.items():
    if count > 0:
        print(f"  {category}: {count}")

print("\nHash mapping (ID consistency):")
for original, hashed in engine.hash_mapping.items():
    print(f"  {original} → {hashed}")
