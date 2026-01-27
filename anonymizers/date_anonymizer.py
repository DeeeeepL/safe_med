#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 11:56
# @Author  : sunwenjun
# @File    : date_anonymizer.py
# @brief: 日期脱敏
import re
from datetime import datetime, timedelta


def normalize_and_shift_date(text, shift_days=-100):
    '''
    日期处理,只保留年月日，且向前偏移一定天数，例如向前偏移100天
    :param text: 日期 例如：2025-10-01，2025年10月1日，2025.10.01，2025-10-01 11:20
    :param shift_days: 向前偏移的天数 例如：-100天
    :return: 2025-10-01
    '''
    # 提取日期部分（支持多种格式）
    match = re.search(r'(\d{4})[年\-\.](\d{1,2})[月\-\.](\d{1,2})', text)
    if not match:
        return None  # 未匹配到日期则返回 None

    year, month, day = map(int, match.groups())

    # 构造日期对象
    date_obj = datetime(year, month, day)

    # 向前偏移指定天数（默认 -10 天）
    shifted_date = date_obj + timedelta(days=shift_days)

    # 格式化输出为 YYYY-MM-DD
    return shifted_date.strftime("%Y-%m-%d")


if __name__ == '__main__':
    # 测试示例
    examples = [
        "2025-02-01",
        "2025年10月1日",
        "2025.10.01",
        "2025-10-01 11:20",
        "2025-10-01 11:20:34",
        "2025-10-01T11:20:34Z",
        "2025-10-01T11:20:34+08:00",
        "abcxxx"
    ]

    for e in examples:
        print(e, "→", normalize_and_shift_date(e))
