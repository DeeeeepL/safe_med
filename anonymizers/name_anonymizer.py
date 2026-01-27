#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 11:53
# @Author  : sunwenjun
# @File    : name_anonymizer.py
# @brief: 姓名脱敏
import re
import hashlib


def anonymize_name(name: str) -> str:
    '''
    医疗病例中姓名脱敏处理：保留姓氏 + 模糊化
    例：张三 → 张某，欧阳娜娜 → 欧阳某，李 → 李某，John → 某某
    :param name:
    :return:
    '''
    if not name or not isinstance(name, str):
        return "某某"

    # 去掉非汉字
    name = re.sub(r'[^\u4e00-\u9fa5]', '', name)
    if len(name) == 0:
        return "某某"

    # 处理复姓（常见复姓列表）
    compound_surnames = ['欧阳', '司马', '诸葛', '司徒', '东方', '慕容', '尉迟', '长孙', '司空', '皇甫', '夏侯']
    for cs in compound_surnames:
        if name.startswith(cs):
            return cs + '某'

    # 普通姓氏
    return name[0] + '某'


def hash_name(name: str) -> str:
    '''
    对姓名进行哈希脱敏，可保持同名映射一致
    张三 → NAME_ID_8a9f3b1c
    李四 → NAME_ID_17e25ca2
    :param name:
    :return:
    '''
    if not name:
        return ""
    h = hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]
    return f"NAME_ID_{h}"
