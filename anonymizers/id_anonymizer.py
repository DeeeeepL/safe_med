#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 14:54
# @Author  : sunwenjun
# @File    : id_anonymizer.py
# @brief: 各种id号脱敏
import hashlib


def get_hash(text):
    '''
    生成唯一代号
    :param value:
    :return:
    '''

    if not text:
        return ''
    value = str(text)
    hash_number = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return hash_number
