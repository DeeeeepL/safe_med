#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 13:55
# @Author  : sunwenjun
# @File    : doctor_anonymizer.py
# @brief: 医生职称脱敏
import re

# 医院常见职称列表（可根据实际医院扩展） todo：替换成从文件中读取
TITLES = [
    # 医生职称
    '主任医师', '副主任医师', '主治医师', '住院医师', '助理医师', '实习医师',
    '教授医师', '博士后医师', '研究员医师',
    # 护士职称
    '护士长', '副主任护师', '主任护师', '护师', '助理护师', '护士', '实习护士',
    # 技师职称
    '技师', '高级技师', '主任技师', '助理技师'
]


def anonymize_name_with_title(text: str) -> str:
    """
    医院姓名脱敏，保留职称，姓名替换为'某某'
    例如：
        '陈佛平主治医师' → '某某主治医师'
        '李四护士长' → '某某护士长'
        '王五技师' → '某某技师'
    """
    if not text or not isinstance(text, str):
        return "某某"

    # 去掉前后空格
    text = text.strip()

    # 遍历职称列表，匹配并保留职称
    for title in TITLES:
        if title in text:
            return "某某" + title

    # 如果未匹配到职称，默认只保留“某某”
    return "某某"


if __name__ == '__main__':
    examples = [
        "陈佛平主治医师",
        "李四主任医师",
        "王五医师",
        "赵六助理医师",
        "钱七护士长",
        "孙八护师",
        "周九技师",
        "未知人员"
    ]

    for e in examples:
        print(f"{e} → {anonymize_name_with_title(e)}")
