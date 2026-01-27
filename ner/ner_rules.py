#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/10/9 15:06
# @Author  : sunwenjun
# @File    : ner_rules.py
# @brief: 使用正则表达式，实现命名实体识别
'''
ner好坏的评价指标

敏感信息类型包括：
1. name - 姓名（患者、医生等人名）
2. id_card - 身份证号
3. phone - 电话号码
4. address - 地址
5. medical_card - 医疗卡号
6. insurance_no - 医保号
7. admission_no - 住院号
8. outpatient_no - 门诊号
9. report_no - 检查报告号
10. specimen_no - 标本号
11. pathology_no - 病理号
12. doctor_signature - 医生签名/姓名
13. hospital_name - 医院名称
'''
import re
import jieba
import jieba.posseg as pseg


class NERRules(object):
    def __init__(self, titles_path, common_surnames_path, hospitals_path, hospital_suffixes_path):
        '''

        :param titles_path:
        :param common_surnames_path:
        :param locations_path:
        :param location_suffixes_path:
        '''

        self.titles = self.load_dict(dict_path=titles_path)
        self.common_surnames = self.load_dict(dict_path=common_surnames_path)
        self.hospitals = self.load_dict(dict_path=hospitals_path)
        self.hospital_suffixes = self.load_dict(dict_path=hospital_suffixes_path)

        self.entity_types = {'AGE': self.extract_age,
                             'DATE': self.extract_date,
                             'NAME': self.extract_name,
                             'HOSPITAL': self.extract_hospital,
                             'LOCATION': self.extract_location,
                             'DOCTOR': self.extract_doctor,
                             'OTHER': self.extract_other}

    def load_dict(self, dict_path):
        line_list = []
        with open(dict_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                line_list.append(line)

        return line_list

    def get_matches(self, entity_type: str, pattern: str, text: str) -> list:
        '''
        匹配命名实体
        :param entity_type:
        :param text:
        :return:
        '''
        match_list = []
        matches = re.finditer(pattern, text)
        for match in matches:
            (start, end) = match.span()
            word = match.group()
            res = {
                "start": start,
                "end": end,
                "entity_type": entity_type,
                "text": word
            }
            match_list.append(res)

        return match_list

    def extract_date(self, entity_type: str, text: str) -> list:
        '''
        匹配日期时间格式（如 2025-10-01 或 2025-10-01 12:30）
        :param entity_type: DATE
        :param text:
        :return:
        '''

        res_list = []
        pattern = r"(\d{4})[-.]\d{1,2}[-.]\d{1,2}(?:[ Tt]?\d{1,2}:\d{1,2}(?::\d{1,2})?)?"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r"(\d{4})年\d{1,2}月\d{1,2}日(?:[ Tt]?\d{1,2}:\d{1,2}(?::\d{1,2})?)?"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        return res_list

    def extract_age(self, entity_type: str, text: str) -> list:
        '''
        年龄（如 30岁）
        :param entity_type: AGE
        :param text:
        :return:
        '''

        res_list = []
        pattern = r"\b(\d{1,3})岁\b"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)
        return res_list

    def extract_doctor(self, entity_type: str, text: str) -> list:
        '''
        医护人员
        :param entity_type: DOCTOR
        :param text:
        :return:
        '''
        res_list = []
        # 医院常见职称列表（可根据实际医院扩展）
        pattern = r"(" + '|'.join(self.common_surnames) + r")\s*([\u4e00-\u9fa5]{1,2})\s*(" + "|".join(
            self.titles) + ")"
        #
        # pattern = r"(" + '|'.join(
        #     self.common_surnames) + r")\s*(" + "|".join(self.titles) + ")"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        for match in matches:
            word = match.get("text", "")
            words = pseg.cut(word)
            candidates = [word for word, flag in words if flag in ["nr"]]  # “nr”表示人名
            if not candidates:
                print(f"skip doctor candidates:{word}")
                continue

            # 如果 text 中包含指定关键词，就跳过
            if any(h in word for h in ["麻醉","请示"]):  # todo：bad name
                print("skip doctor candidates:", word)
                continue
            res_list.append(match)

        # res_list.extend(matches)

        pattern = r"(?:医生|医师|签名)[：:]\s*(" + '|'.join(
            self.common_surnames) + r")\s*([\u4e00-\u9fa5]{1,2})"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)

        res_list.extend(matches)

        return res_list

    def extract_name(self, entity_type: str, text: str) -> list:
        '''
        提取患者姓名
        todo: 结巴，依赖上下文.先提取，再过滤
        :param entity_type: NAME
        :param text:
        :return:
        '''
        res_list = []
        # *****姓名*****
        # 完整的姓名正则表达式：匹配单字姓氏和复姓，并跟随1或2个汉字作为名字
        # 构建姓氏正则部分
        surname_pattern = "(?:" + "|".join(self.common_surnames) + ")"

        # 姓名模式：姓 + 名（1~2个汉字）
        name_pattern = surname_pattern + r"[\u4e00-\u9fa5]{1,2}"

        # 含提示词的完整匹配
        pattern = r"(?:姓名|患者|病人|就诊人|家属)[:：\s]*(" + name_pattern + ")"

        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        for match in matches:
            word = match.get("text", "")
            words = pseg.cut(word)
            candidates = [word for word, flag in words if flag in ["nr"]]  # “nr”表示人名
            if not candidates:
                print(f"skip name candidates :{word}")
                continue

            # 如果 text 中包含指定关键词，就跳过
            if any(h in word for h in ["麻醉","请示"]):  # todo：bad name
                print("skip name candidates:", word)
                continue

            res_list.append(match)

        return res_list

    def extract_hospital(self, entity_type: str, text: str) -> list:
        '''
        医院
        :param entity_type: HOSPITAL
        :param text:
        :return:
        '''
        res_list = []

        # 完全匹配
        # pattern = r"(" + "|".join(self.hospitals) + ")"
        # matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        # res_list.extend(matches)

        pattern = r"(" + "|".join(self.hospitals) + r"|[\u4e00-\u9fa5]{1,10}\s*(?:" + "|".join(
            self.hospital_suffixes) + r"))"

        # pattern = r"([\u4e00-\u9fa5]{1,10}\s*" + "|".join(self.hospital_suffixes) + ")"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)

        # 后处理
        for match in matches:
            word = match.get("text", "")
            # 如果 text 中包含指定关键词，就跳过
            if any(h in word for h in ["当地医院", "就诊于医院"]):
                print("skip hospital candidates:", word)
                continue
            res_list.append(match)

        # res_list.extend(matches)

        pattern = r"([一二三四五六七八九十]+(层|楼|诊室)|\d+(层|楼|诊室))"
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        return res_list

    def extract_location(self, entity_type: str, text: str) -> list:
        '''
        地点:省市区
        :param entity_type: LOCATION
        :param text:
        :return:
        '''
        res_list = []

        pattern = r'(?:住址|地址|居住地)[：:]\s*([^，,。\n]{10,50})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        return res_list

    def extract_other(self, entity_type: str, text: str) -> list:
        '''
        其他
        :param entity_type: OTHER
        :param text:
        :return:
        '''
        res_list = []
        pattern = r"腾讯会议号：[0-9]+[。,]*"  # 示例匹配：腾讯会议号：123456、腾讯会议号：7890,
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:身份证|证件号)[：:]\s*(\d{15}|\d{17}[\dXx])'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:电话|手机|联系方式)[：:]\s*(1[3-9]\d{9}|\d{3,4}-\d{7,8})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:医疗卡|就诊卡)[：:]\s*(\d{8,20})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:医保号|社保号)[：:]\s*(\d{8,20})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:住院号|入院号)[：:]\s*(\d{6,15})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:门诊号|挂号)[：:]\s*(\d{6,15})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        pattern = r'(?:报告号|检查号)[：:]\s*([A-Z0-9]{8,20})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)
        pattern = r'(?:床号)[：:]\s*([A-Z0-9]{1,5})'
        matches = self.get_matches(entity_type=entity_type, pattern=pattern, text=text)
        res_list.extend(matches)

        return res_list

    def extract_entities(self, content):
        res_list = []
        for entity_type, func in self.entity_types.items():
            tmp_list = func(entity_type=entity_type, text=content)
            res_list.extend(tmp_list)
        return res_list


if __name__ == '__main__':
    # 输入文本
    test1 = """
    中山大學肿瘤防治中心
    Sun Yat-senUniversity Cancer Center
    姓名:谢梓莹 性别：女  年龄：30岁 科(区)别:放疗五区 床号:08 住院号:0000688716 
    2024-05-15 13:01 陈佛平主治医师查房记录 
    今随陈佛平主治医师查房，患者未诉恶心呕吐等不适，诉便秘。今日为化疔第2天，继续支持对症治疗。
    医嘱内容:顺铂化疗
    医生签名:欧阳翼
    """

    test2 = """
    出生日期:1977-11-29 当前年龄:46岁 
    姓名:马燕红 科(区)别:放疗五区 床号:14 住院号:0000669289 
    第4次入院记录
    姓名:马燕红 籍贯:江西省 
    性别:女 住址:江西省南昌市青山湖区湖坊镇万家118 
    年龄:46岁 入院日期:2024-01-29 14:45 
    婚姻:已婚 记录日期:2024-01-29 15:21 
    职业:个体经营者 病史提供:本人 
    民族:汉族 可靠程度:可靠 
    主诉:宫颈鳞癌 IIA1期术后同步放化疗中
    现病史:患者近1月同房后阴道出血2次，伴右下腹痛，23-11-17至江西省妇幼保健院就诊，查彩超:于言多发性肌瘤:盆腔积液。TCT:高度鳞状上皮内病变(HSIL)，不除外进一步病变; HPV16(+)=阴道镜及活检:(颈管)浸润性鳞状细胞癌;(阴道后壁上段)片示间质纤维组织及至少为游离的鳞状细胞原位癌团块。患者遂转至我院就诊,我院病理会诊:(言颈4°)浸润性鳞状细胞癌(中分化);(阴道后壁上段)送检组织中见少量游离异型细胞巢,至少为高级别鳞状上皮内病变，未除外浸润癌可能;(颈管)浸润性鳞状细胞癌(中分化)。于2023年11月30日在全麻下行广泛性全子宫+双侧附件切除+前哨淋巴结标记+前哨淋巴结活检+腹腔粘连松解术手术,术后病理:宫颈肿物2*2*12cm,(全子宫及双附件)镜检为中至低分化鳞状细胞癌，癌组织浸润宫颈深肌层(最大浸润深度为0.7cm，此处宫颈肌壁全层厚度为1.1cm)，未累及阴道弯窿，可见脉管内癌栓,淋巴结、阴道壁未见癌。2023-12-14放疗科就诊。勾画靶区时发现腹主动脉旁及髂血管旁多发淋巴结肿大,2023-12-29 17:01:25PET/CT宫颈癌术后:阴道残端稍肿张增厚局部代谢活跃，疑术后改变伴炎症;双侧盆腔、双侧闭孔区条片状、结节样影代谢活跃,余盆腔腹膜增厚代谢略活跃，结合病史,考虑术后改变。双侧髂血管旁、骶前、直肠周围脂肪间隙多发淋巴结代谢较活跃，复习我院2023-11-21CT、2023-11-21及12-15MR检查,部分病灶较术前新见/增大,疑术后反应性/炎性改变,请结合临床。腹主动脉旁多发小淋巴结部分代谢略活跃,较2023-11-21我院CT大小相仿，疑炎性病变，建议密切随诊。左锁上小淋巴结代谢略活跃,较前大小无明显变化，疑炎性病变。于2024-01-04开始外照射放疗，放疗处方剂量:小骨盆野D T:CTV: 45Gy/25F,2024-01-09于第一程同期化疗,顺铂44mgd1-d3,现放疗第19次。患者为行进一步治疗，门诊拟“宫颈鳞癌IIA1期术后”收治入院。现患者无阴道出血,无腹痛，饮食睡眠可，二便正常。外院治疗过程:无
    既往史:10余年前行宫颈LEEP术(具体病因及术后病理不详，自诉无恶性病变)，否认"肝炎、结核、伤寒"等传染性疾病史;否认"高血压、冠心病、糖尿病"病史:否认输血史。
    宫颈疾病及筛查史:未接种HPV疫苗，曾经行宫颈癌筛查,末次筛查时间2017年,筛查方法:HP V、TCT.
    个人史:否认吸烟史，否认饮酒史。否认化学物接触史。
    月经史:未绝经，12岁月经初潮，月经周期30天，经期7天，末次月经日期:2023年11月23日月经规则，月经量量多，有痛经程度:轻。不需服用止痛药。
    -第1页-
    """

    test3 = """
    北大人民医院通州院区3层5诊室三楼3楼北京大学血液病研究所欧阳主任
    北大人民血液中心
    """

    test4 = """
    浙江省肿病醫院
    ZHEJIANG CANCER HOSPITAT
    浙江省癌症中心
    宫颈癌专科入院记录
    性别:女 年龄:54岁 
    辅助检查
    
    (1)实验室检查: HPV检查结果:未知
    2024年04月01日绍兴市人民医院 肿瘤指标ca125:61.23U/ml,SCC:>70.00ng/ml。
    
    (2)特殊检查:
    2024年04月01日绍兴市人民医院盆腔MRI子宫颈癌(FIGGO分期IVB)，累及膀胱后壁、宫体、阴道中上段、两侧盆壁、腹股沟、多发肿大淋巴结;骨盆及两侧股骨骨质改变，转移可能大，请结合ECT或PET-CT检查。
    
    (3)病理学检查结果:
    宫颈脱落细胞学病理:未知宫颈组织学病理类型:鳞癌
    
    病理检查1:2024年03月26日绍兴市人民医院宫颈活检2418922(宫颈)低分化(鳞状)细胞
    癌
    
    初步诊断:1.宫颈恶性肿瘤IVB
    2.高血压
    3.脑卒中个人史
    医师签名:/表如几
    日 期:2024-04-09 14:32
    """
    test5 = """
    步评估患者向麻醉医师就诊当地医院就诊于医院
    """

    titles_path = '/Users/sunwenjun/Documents/gitee/safe-med/dict/DoctorSuffixes.txt'
    common_surnames_path = '/Users/sunwenjun/Documents/gitee/safe-med/dict/Surnames.txt'
    hospitals_path = '/Users/sunwenjun/Documents/gitee/safe-med/dict/Hospitals.txt'
    hospital_suffixes_path = '/Users/sunwenjun/Documents/gitee/safe-med/dict/HospitalSuffixes.txt'

    ner_rules = NERRules(titles_path=titles_path, common_surnames_path=common_surnames_path,
                         hospitals_path=hospitals_path, hospital_suffixes_path=hospital_suffixes_path)
    entity_list = ner_rules.extract_entities(test1)
    for entity in entity_list:
        print("entity:", entity)
