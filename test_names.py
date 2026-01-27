#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test anonymize_name function"""

import sys
sys.path.insert(0, 'd:\\projects\\safe_med')

from anonymizers.name_anonymizer import anonymize_name

# Test cases
test_names = [
    "张三",
    "李四",
    "欧阳娜娜",
    "李",
    "王五六",
]

print("=" * 50)
print("Testing anonymize_name function")
print("=" * 50)

for name in test_names:
    result = anonymize_name(name)
    print(f"{name:10} → {result:10}")

print("\n" + "=" * 50)
print("Now testing with rule_fallback.py")
print("=" * 50)

from safe_med_ui.rule_fallback import FallbackRuleEngine
from safe_med_ui.config_store import ConfigStore
from pathlib import Path

config = ConfigStore(repo_root=Path('d:\\projects\\safe_med'))
terms = config.load_terms()

engine = FallbackRuleEngine(
    custom_terms=terms,
    enable_categories={
        "surnames": True,
        "hospital_dict": False,
        "hospital_suffixes": False,
        "doctor_title": False,
        "id_like": False,
        "phone": False,
        "email": False,
        "date": False,
        "age": False,
    }
)

test_texts = [
    "患者姓名：张三",
    "医生：李四",
    "护士欧阳娜娜检查了患者",
    "患者张三和李四同时就诊",
]

for text in test_texts:
    result, stats = engine.deidentify(text)
    print(f"\n原文: {text}")
    print(f"结果: {result}")
    print(f"统计: {stats}")
