import re
from dataclasses import dataclass
from typing import Dict, List, Tuple
from anonymizers.age_anonymizer import age_to_range
from anonymizers.date_anonymizer import normalize_and_shift_date
from anonymizers.name_anonymizer import anonymize_name, hash_name
from anonymizers.doctor_anonymizer import anonymize_name_with_title
from anonymizers.id_anonymizer import get_hash


# 你可以把这些规则继续扩展到：住院号/门诊号/医保卡/车牌/地址等
RE_ID_LIKE = re.compile(r"\b\d{15}\b|\b\d{17}[\dXx]\b")  # 身份证（粗略）
RE_PHONE = re.compile(r"\b1[3-9]\d{9}\b")
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
RE_DATE = re.compile(r"\b(20\d{2}|19\d{2})[-/.年](0?[1-9]|1[0-2])[-/.月](0?[1-9]|[12]\d|3[01])日?\b")
RE_AGE = re.compile(r"(\d+)\s*[岁]")  # 年龄：如"45岁"


def _replace_dict(text: str, terms: List[str], tag: str) -> Tuple[str, int]:
    """
    简单包含替换（按长词优先），后续你也可替换成 Aho-Corasick 以提升性能
    """
    if not terms:
        return text, 0
    terms = sorted({t for t in terms if t}, key=len, reverse=True)
    n = 0
    for t in terms:
        if t in text:
            text = text.replace(t, tag)
            n += 1
    return text, n


@dataclass
class FallbackRuleEngine:
    custom_terms: Dict[str, List[str]]
    enable_categories: Dict[str, bool]
    replacement_mode: str = "tag"  # "tag" | "mask"
    hash_mapping: Dict[str, str] = None  # 用于保持相同ID的一致性映射

    def __post_init__(self):
        if self.hash_mapping is None:
            self.hash_mapping = {}

    def deidentify(self, text: str) -> Tuple[str, Dict[str, int]]:
        stats: Dict[str, int] = {}

        def sub(regex, repl, key):
            nonlocal text
            if not self.enable_categories.get(key, True):
                return
            text2, k = regex.subn(repl, text)
            text = text2
            if k:
                stats[key] = stats.get(key, 0) + k

        # ========== 日期脱敏：使用normalize_and_shift_date进行日期偏移 ==========
        if self.enable_categories.get("date", True):
            def replace_date(match):
                date_str = match.group(0)
                # 调用date_anonymizer进行日期偏移（默认向前偏移100天）
                shifted_date = normalize_and_shift_date(date_str, shift_days=-100)
                if shifted_date:
                    return shifted_date
                return "[DATE]"  # 如果偏移失败，返回标签
            
            text2 = RE_DATE.sub(replace_date, text)
            k = len(RE_DATE.findall(text))
            if text2 != text:
                text = text2
                if k:
                    stats["date"] = stats.get("date", 0) + k

        # ========== 身份证脱敏：使用get_hash生成唯一代码 ==========
        if self.enable_categories.get("id_like", True):
            def replace_id(match):
                id_str = match.group(0)
                # 使用哈希保持映射一致性
                if id_str not in self.hash_mapping:
                    self.hash_mapping[id_str] = f"ID_{get_hash(id_str)}"
                return self.hash_mapping[id_str]
            
            text2 = RE_ID_LIKE.sub(replace_id, text)
            k = len(RE_ID_LIKE.findall(text))
            if text2 != text:
                text = text2
                if k:
                    stats["id_like"] = stats.get("id_like", 0) + k

        # ========== 电话号码脱敏 ==========
        sub(RE_PHONE, "[PHONE]", "phone")

        # ========== 邮箱脱敏 ==========
        sub(RE_EMAIL, "[EMAIL]", "email")

        # ========== 年龄脱敏：使用age_to_range转换为年龄段 ==========
        # 例如：45岁 → 40～50岁
        if self.enable_categories.get("age", False):
            def replace_age(match):
                age_str = match.group(1)
                return age_to_range(age_str)
            
            text2 = RE_AGE.sub(replace_age, text)
            if text2 != text:
                k = len(RE_AGE.findall(text))
                text = text2
                if k:
                    stats["age"] = stats.get("age", 0) + k

        # ========== 医生职位脱敏：使用anonymize_name_with_title进行智能处理 ==========
        # 保留职称，医生姓名替换为'某某'，如：李四主治医师 → 某某主治医师
        if self.enable_categories.get("doctor_title", False):
            # 只处理 "汉字(2-3个) + 医学职位" 的模式，避免过度替换
            # 匹配：名字(2-4个汉字) + 医学职称关键词
            medical_titles = ['主任医师', '副主任医师', '主治医师', '住院医师', '助理医师', '实习医师', 
                             '教授医师', '博士后医师', '研究员医师', '护士长', '副主任护师', '主任护师', 
                             '护师', '助理护师', '护士', '实习护士', '技师', '高级技师', '主任技师', '助理技师']
            
            for title in sorted(medical_titles, key=len, reverse=True):
                # 匹配 "2-4个汉字 + 职位" 的模式
                pattern = re.compile(rf"[\u4e00-\u9fa5]{{2,4}}{re.escape(title)}")
                matches = list(pattern.finditer(text))
                for match in reversed(matches):  # 反向遍历避免替换后位置改变
                    original = match.group(0)
                    # 调用anonymize_name_with_title进行智能脱敏
                    anonymized = anonymize_name_with_title(original)
                    text = text[:match.start()] + anonymized + text[match.end():]
                    stats["doctor_title"] = stats.get("doctor_title", 0) + 1

        # ========== 医院脱敏：使用医院词典进行替换 ==========
        # 将医院名称替换为通用标签，如：北京协和医院 → [HOSPITAL]
        if self.enable_categories.get("hospital_dict", True):
            # 使用词典匹配医院名称
            hospitals = self.custom_terms.get("hospitals", [])
            if hospitals:
                # 按长度排序，优先匹配长的医院名称
                for hospital in sorted(hospitals, key=len, reverse=True):
                    if hospital in text:
                        text = text.replace(hospital, "[HOSPITAL]")
                        stats["hospital_dict"] = stats.get("hospital_dict", 0) + 1

        # ========== 姓氏脱敏：使用anonymize_name进行智能处理 ==========
        # 姓氏处理：保留姓氏+模糊化，如"张三" → "张某"、"欧阳娜娜" → "欧阳某"
        if self.enable_categories.get("surnames", False):
            surnames_list = self.custom_terms.get("surnames", [])
            if surnames_list:
                # 只处理多字姓氏（复姓）- 避免单字过度匹配的问题
                # 例：欧阳、司马、诸葛等
                multi_char_surnames = [s for s in surnames_list if len(s) > 1]
                
                for surname in sorted(multi_char_surnames, key=len, reverse=True):
                    # 匹配 "多字姓氏 + 1-2个汉字"
                    pattern = re.compile(rf"{re.escape(surname)}[\u4e00-\u9fa5]{{1,2}}")
                    matches = list(pattern.finditer(text))
                    for match in reversed(matches):
                        name = match.group(0)
                        anonymized = anonymize_name(name)
                        if anonymized != name:
                            text = text[:match.start()] + anonymized + text[match.end():]
                            stats["surnames"] = stats.get("surnames", 0) + 1
                
                # 对单字姓氏，仅在特定上下文（标签）中进行替换，避免误匹配
                single_char_surnames = [s for s in surnames_list if len(s) == 1]
                
                if single_char_surnames:
                    # 只在这些标签之后匹配名字：姓名、患者、医生、护士、家族成员等
                    # 使用负向前查断言来确保是标签之后，避免"患者从..."这样的误匹配
                    context_patterns = [
                        r'(?:姓名|患者名字|病人)：([\u4e00-\u9fa5]{1,2})',  # "姓名："后面
                        r'(?:主治医生|医生|护士|医师|大夫)：([\u4e00-\u9fa5]{1,2})',   # "医生："后面
                        r'(?<!从)患者([\u4e00-\u9fa5]{1,2})(?=，|。|、)',    # "患者XX，" 格式
                        r'(?:父亲|母亲|父母|爸爸|妈妈|哥哥|弟弟|姐姐|妹妹|爷爷|奶奶|公公|婆婆|儿子|女儿|孙子|孙女|妻子|丈夫|兄弟|姐妹)：([\u4e00-\u9fa5]{1,2})',  # 家族成员
                        r'(?:紧急联系人|联系人)：([\u4e00-\u9fa5]{1,2})',  # 联系人
                        r'(?:推荐|咨询)医生：([\u4e00-\u9fa5]{1,2})',  # 推荐医生
                    ]
                    
                    for pattern_str in context_patterns:
                        pattern = re.compile(pattern_str)
                        matches = list(pattern.finditer(text))
                        for match in reversed(matches):
                            # 获取匹配到的名字（可能在第1组或最后一组）
                            name = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                            if name and len(name) >= 2 and name[0] in single_char_surnames:
                                anonymized = anonymize_name(name)
                                start = match.start(1) if match.lastindex and match.lastindex >= 1 else match.start()
                                end = match.end(1) if match.lastindex and match.lastindex >= 1 else match.end()
                                text = text[:start] + anonymized + text[end:]
                                stats["surnames"] = stats.get("surnames", 0) + 1

        # ========== 医疗机构后缀脱敏：使用医疗机构后缀词典进行替换 ==========
        # 医疗机构后缀脱敏，如：医院、诊所、中心 → [FACILITY_TYPE]
        if self.enable_categories.get("hospital_suffixes", False):
            # 使用词典匹配医疗机构后缀
            suffixes = self.custom_terms.get("hospital_suffixes", [])
            if suffixes:
                # 按长度排序，优先匹配长的后缀
                for suffix in sorted(suffixes, key=len, reverse=True):
                    if suffix in text:
                        text = text.replace(suffix, "[FACILITY]")
                        stats["hospital_suffixes"] = stats.get("hospital_suffixes", 0) + 1

        # ========== 科室脱敏：词典匹配 ==========
        if self.enable_categories.get("departments", False):
            text, k = _replace_dict(text, self.custom_terms.get("departments", []), "[DEPARTMENT]")
            if k:
                stats["departments"] = stats.get("departments", 0) + k

        # ========== 自定义敏感词脱敏 ==========
        text, k = _replace_dict(text, self.custom_terms.get("custom_sensitive", []), "[SENSITIVE]")
        if k:
            stats["custom_sensitive"] = stats.get("custom_sensitive", 0) + k

        return text, stats
