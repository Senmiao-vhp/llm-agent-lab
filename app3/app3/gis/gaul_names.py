from __future__ import annotations

from typing import Dict, List


_ADMIN_SUFFIXES = (
    "特别行政区",
    "自治区",
    "自治州",
    "自治县",
    "地区",
    "盟",
    "省",
    "市",
    "区",
    "县",
    "旗",
)


def strip_cn_admin_suffix(name: str) -> str:
    """
    将常见中文行政后缀去掉，用于生成 GAUL 候选。
    只做轻量规则：不做繁简转换、不做拼音。
    """
    s = (name or "").strip()
    for suf in _ADMIN_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def gaul_name_candidates(region: str, extra_candidates: List[str] | None = None) -> List[str]:
    """
    为 GEE GAUL(2015) 的 ADM1/ADM2 名称匹配生成候选。
    说明：
    - GAUL 字段多为英文/拼音式命名（如 "Sichuan Sheng", "Beijing Shi"），
      因此需要少量中文->英文候选映射来提高命中率。
    """
    cn = strip_cn_admin_suffix(region)
    cn_to_en: Dict[str, List[str]] = {
        "北京": ["Beijing Shi", "Beijing"],
        "上海": ["Shanghai Shi", "Shanghai"],
        "天津": ["Tianjin Shi", "Tianjin"],
        "重庆": ["Chongqing Shi", "Chongqing"],
        "河北": ["Hebei Sheng", "Hebei"],
        "山西": ["Shanxi Sheng", "Shanxi"],
        "辽宁": ["Liaoning Sheng", "Liaoning"],
        "吉林": ["Jilin Sheng", "Jilin"],
        "黑龙江": ["Heilongjiang Sheng", "Heilongjiang"],
        "江苏": ["Jiangsu Sheng", "Jiangsu"],
        "浙江": ["Zhejiang Sheng", "Zhejiang"],
        "安徽": ["Anhui Sheng", "Anhui"],
        "福建": ["Fujian Sheng", "Fujian"],
        "江西": ["Jiangxi Sheng", "Jiangxi"],
        "山东": ["Shandong Sheng", "Shandong"],
        "河南": ["Henan Sheng", "Henan"],
        "湖北": ["Hubei Sheng", "Hubei"],
        "湖南": ["Hunan Sheng", "Hunan"],
        "广东": ["Guangdong Sheng", "Guangdong"],
        "海南": ["Hainan Sheng", "Hainan"],
        "四川": ["Sichuan Sheng", "Sichuan"],
        "贵州": ["Guizhou Sheng", "Guizhou"],
        "云南": ["Yunnan Sheng", "Yunnan"],
        "陕西": ["Shaanxi Sheng", "Shaanxi"],
        "甘肃": ["Gansu Sheng", "Gansu"],
        "青海": ["Qinghai Sheng", "Qinghai"],
        "台湾": ["Taiwan"],
        "内蒙古": ["Nei Mongol Zizhiqu", "Nei Mongol"],
        "广西": ["Guangxi Zhuangzu Zizhiqu", "Guangxi"],
        "西藏": ["Xizang Zizhiqu", "Xizang"],
        "宁夏": ["Ningxia Huizu Zizhiqu", "Ningxia"],
        "新疆": ["Xinjiang Uygur Zizhiqu", "Xinjiang"],
        "香港": ["Hong Kong"],
        "澳门": ["Macao", "Macau"],
    }

    out: List[str] = []
    for x in (extra_candidates or []):
        x = (x or "").strip()
        if x and x not in out:
            out.append(x)
    for x in (region, cn):
        x = (x or "").strip()
        if x and x not in out:
            out.append(x)
    for x in cn_to_en.get(cn, []):
        x = (x or "").strip()
        if x and x not in out:
            out.append(x)
    return out

