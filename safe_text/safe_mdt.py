#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/10 09:39
# @Author  : sunwenjun
# @File    : safe_mdt.py
# @brief: 多学科会诊数据脱敏

import json
import copy
from ner.ner_rules import NERRules
from anonymizers.id_anonymizer import get_hash
from anonymizers.date_anonymizer import normalize_and_shift_date
from anonymizers.age_anonymizer import age_to_range
from anonymizers.name_anonymizer import hash_name
from anonymizers.doctor_anonymizer import anonymize_name_with_title
from anonymizers.location_anonymizer import anonymize_hospital,anonymize_location
from anonymizers.other_anonymizer import anonymize_other
from conf import titles_path, common_surnames_path, hospitals_path, hospital_suffixes_path

def text_anonymize(content):
    '''
    文本数据脱敏
    :param content:脱敏前文本
    :return:脱敏后文本
    '''
    if not content or not isinstance(content, str):
        return ""
    modifications = []
    ner_rules = NERRules(titles_path, common_surnames_path, hospitals_path, hospital_suffixes_path)
    entity_list = ner_rules.extract_entities(content=content)
    for entity in entity_list:
        entity_type = entity['entity_type']
        text = entity['text']
        if entity_type == 'DATE':
            text_safe = normalize_and_shift_date(text=text, shift_days=-100)
            modifications.append((text, text_safe))
        elif entity_type == 'AGE':
            text_safe = age_to_range(age=text)
            modifications.append((text, text_safe))
        elif entity_type == 'NAME':
            text_safe = hash_name(name=text)
            modifications.append((text, text_safe))
        elif entity_type == 'HOSPITAL':
            text_safe = anonymize_hospital(text=text)
            modifications.append((text, text_safe))
        elif entity_type == 'LOCATION':
            text_safe = anonymize_location(text=text)
            modifications.append((text, text_safe))
        elif entity_type == 'DOCTOR':
            text_safe = anonymize_name_with_title(text)
            modifications.append((text, text_safe))
        elif entity_type == 'OTHER':
            text_safe = anonymize_other(text=text)
            modifications.append((text, text_safe))
    index = 0
    for text, text_safe in modifications:
        content = content.replace(text, text_safe)
        index += 1
        print(f"序号：{index}---脱敏前:{text}---脱敏后:{text_safe}")

    return content


def mdt_anonymize():
    json_path = '../data/Old_住院会诊脱敏.json'
    json_out = '../data/Old_住院会诊脱敏_v2.json'
    hash_dict_path = '../data/Old_住院会诊Hashdict.json'

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    datacp = copy.deepcopy(data)
    print(f'待处理数据量：{len(datacp)}')

    case_safe_list = []
    hash_dict = {}
    for case in datacp:
        case_safe = {}

        # 会诊编号
        content = case.get('会诊编号', '')
        case_safe['会诊编号'] = get_hash(text=content)
        hash_dict.update({content: case_safe['会诊编号']})

        # 病历号
        content = case.get('病历号', '')
        case_safe['病历号'] = get_hash(text=content)
        hash_dict.update({content: case_safe['病历号']})

        # 邀请科室
        content = case.get('邀请科室', '')
        case_safe['邀请科室'] = text_anonymize(content=content)

        # 发起科室
        content = case.get('发起科室', '')
        case_safe['发起科室'] = text_anonymize(content=content)

        # 会诊目的
        content = case.get('会诊目的', '')
        case_safe['会诊目的'] = text_anonymize(content=content)

        # 会诊意见
        content = case.get('会诊意见', '')
        case_safe['会诊意见'] = text_anonymize(content=content)

        # 会诊意见提出科室
        content = case.get('会诊意见提出科室', '')
        case_safe['会诊意见提出科室'] = text_anonymize(content=content)

        case_safe_list.append(case_safe)

    # 存储hash_dict和datacp
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump(datacp, f, indent=4, ensure_ascii=False)

    with open(hash_dict_path, 'w', encoding='utf-8') as f:
        json.dump(hash_dict, f)


if __name__ == '__main__':
    mdt_anonymize()
