#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 11:52
# @Author  : sunwenjun
# @File    : location_anonymizer.py
# @brief: 地点脱敏
import re


def anonymize_hospital(text: str) -> str:
    '''
    医疗文本中的地点脱敏：
    - 仅保留省级信息
    - 删除详细地址或医院名称
    :param text:
    :return:
    '''
    if not text or not isinstance(text, str):
        return ""

    # 常见医院名脱敏
    pattern = r'[^\s，,]*(医院|诊所|中心|研究所)[^\s，,]*'

    # 使用函数动态替换不同类型
    def replace_func1(match):
        word = match.group(1)
        if word == '医院':
            return '某医院'
        elif word == '诊所':
            return '某诊所'
        elif word == '中心':
            return '某中心'
        elif word == '研究所':
            return '某研究所'
        else:
            return text  # 兜底

    text_new = re.sub(pattern, replace_func1, text)
    if text_new != text:
        return text_new
    return  text


def anonymize_location(text: str) -> str:
    '''
    医疗文本中的地点脱敏：
    - 保留省级信息
    - 去除详细地址或医院名称
    :param text:
    :return:
    '''
    if not text or not isinstance(text, str):
        return ""

    # 常见医院名脱敏
    pattern = r'[^\s，,]*(层|楼|诊室)[^\s，,]*'

    # 使用函数动态替换不同类型
    def replace_func2(match):
        word = match.group(1)
        if word == '层':
            return 'XX层'
        elif word == '楼':
            return 'XX楼'
        elif word == '诊室':
            return 'XX诊室'
        else:
            return text  # 兜底

    text_new = re.sub(pattern, replace_func2, text)
    if text_new != text:
        return text_new

    # 提取省份
    province_match = re.search(r'([\u4e00-\u9fa5]{2,}省)', text)
    if province_match:
        return province_match.group(1) + "某地"

    # 提取直辖市
    city_match = re.search(r'(北京市|天津市|上海市|重庆市)', text)
    if city_match:
        return city_match.group(1) + "某地"

    # 其他未知情况
    return "某地"


def map_location(location: str, mapping: dict) -> str:
    '''
    根据映射表替换真实地点
    :param location:
    :param mapping:
    :return:
    '''
    if not location:
        return ""
    for real_name, code in mapping.items():
        if real_name in location:
            return code
    return "未知中心"


if __name__ == '__main__':
    # 示例映射表
    location_map = {
        "北京协和医院": "SITE_01",
        "四川大学华西医院": "SITE_02",
        "上海瑞金医院": "SITE_03"
    }

    print(map_location("患者来自北京协和医院", location_map))
    # → SITE_01

    examples = [
        "北京协和医院心内科",
        "上海瑞金医院门诊",
        "广州华侨诊所",
        "深圳市中心医院",
        "某科研中心",
        "五楼",
        "河南省信阳市",
        "广东省深圳市",
        "广东省深圳市宝安区",
        "北京市昌平区"
    ]

    for e in examples:
        print(f"{e} → {anonymize_location(e)}")
