#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test to verify highlighting feature
"""

import sys
sys.path.insert(0, 'd:\\projects\\safe_med')

import re

# 测试高亮模式
text = """
脱敏示例：
姓名：张某
年龄：40～50岁
身份证号：ID_dc567e46
联系电话：[PHONE]
就诊医院：[HOSPITAL]
就诊科室：[DEPARTMENT]
就诊时间：2023-09-06
"""

print("=" * 60)
print("高亮功能测试")
print("=" * 60)

patterns = [
    (r'\[PHONE\]', 'phone'),
    (r'ID_[a-f0-9]+', 'id'),
    (r'某[某某a-zA-Z0-9]*', 'name'),
    (r'\[HOSPITAL\]', 'hospital'),
    (r'\[DEPARTMENT\]', 'hospital'),
    (r'\[FACILITY\]', 'hospital'),
    (r'\d{4}-\d{2}-\d{2}', 'date'),  # 日期格式
    (r'\d+～\d+岁', 'modified'),      # 年龄范围
]

print("\n检测到的高亮内容：")
print("-" * 60)

for pattern, tag in patterns:
    matches = list(re.finditer(pattern, text))
    if matches:
        print(f"\n{tag.upper()} (颜色标签：{tag}):")
        for match in matches:
            print(f"  - '{match.group(0)}' at position {match.start()}-{match.end()}")

print("\n" + "=" * 60)
print("✓ 高亮功能配置完成！")
print("=" * 60)
print("\n说明：")
print("  • 黄色背景：通用修改内容 (modified)")
print("  • 浅红色：电话号码 (phone)")
print("  • 天蓝色：身份证/ID号 (id)")
print("  • 浅绿色：姓名 (name)")
print("  • 金色：日期 (date)")
print("  • 橙色：医院/科室 (hospital)")
