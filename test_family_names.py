#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test family members name anonymization"""

import sys
sys.path.insert(0, 'd:\\projects\\safe_med')

from safe_med_ui.rule_fallback import FallbackRuleEngine
from safe_med_ui.config_store import ConfigStore
from pathlib import Path

# Load configuration
config = ConfigStore(repo_root=Path('d:\\projects\\safe_med'))
terms = config.load_terms()

# Create engine with surnames enabled
engine = FallbackRuleEngine(
    custom_terms=terms,
    enable_categories={
        "surnames": True,
        "hospital_dict": False,
        "date": False,
        "id_like": False,
        "phone": False,
        "email": False,
        "age": False,
        "doctor_title": False,
        "hospital_suffixes": False,
        "departments": False,
        "custom_sensitive": False,
    }
)

# Test family members
test_cases = [
    "家族成员：\n父亲：王进，已去世，死于心梗\n母亲：赵红，已去世，死于胃癌\n哥哥：李明，在北京市第二医院工作",
    "家族成员：\n爸爸：张旭\n妈妈：周丽\n兄弟：王强\n妻子：孙梅",
    "紧急联系人：李华，电话13800138000",
    "推荐医生：王医生和陈医生",
]

print("=" * 70)
print("家族成员名字匿名化测试")
print("=" * 70)

for text in test_cases:
    result, stats = engine.deidentify(text)
    print(f"\n原文：\n{text}")
    print(f"\n结果：\n{result}")
    print(f"\n统计：{stats}")
    print("-" * 70)
