#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 11:57
# @Author  : sunwenjun
# @File    : age_anonymizer.py
# @brief: 年龄脱敏

import re
from typing import Union


def age_to_range(age: Union[str, int]) -> str:
    '''
    将年龄转换为年龄段，例如 15 → 10～20岁
    :param age: 年龄 例如：15
    :return:年龄段 例如：10～20岁
    '''
    """"""
    try:
        # 去除可能的非数字字符，例如 "15岁"
        if isinstance(age, str):
            match = re.search(r'\d+', age)
            if not match:
                return "未知"
            age = int(match.group())
        else:
            age = int(age)
    except ValueError:
        return "未知"

    # 定义年龄段
    if age < 0:
        return "未知"
    elif age < 10:
        return "0～10岁"
    elif age >= 100:
        return "100岁以上"
    else:
        lower = (age // 10) * 10
        upper = lower + 10
        return f"{lower}～{upper}岁"


if __name__ == '__main__':

    # 测试示例
    examples = ["15", 15, "15岁", "3 岁", -28, 105, "abc"]
    for e in examples:
        print(f"{e} → {age_to_range(e)}")
