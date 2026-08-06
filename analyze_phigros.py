# -*- coding: utf-8 -*-
"""
Phigros PlayerPrefs 存档分析脚本（只读，不修改原文件）

文件格式：
  XML <map><string name="key">value</string></map>
  key 和 value 都是 URL-encoded 的 base64 字符串
  (%3D==, %2F=/, %2B=+)

本脚本完成：
  1. 解析 XML，提取所有 (key, value) 对
  2. 对每个 key 和 value 做 URL-decode 得到 base64 字符串
  3. base64 decode 得到原始字节
  4. 统计 key/value 字节长度分布、最高频 value
  5. 打印前 20 个条目的详细信息
  6. 判断加密模式线索（ECB / 固定 IV CBC / AES block 对齐）
"""

import os
import sys
import base64
import binascii
from collections import Counter
from urllib.parse import unquote
from xml.etree import ElementTree as ET

# 增加 Windows 控制台 UTF-8 输出兼容
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

XML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "com.PigeonGames.Phigros.v2.playerprefs.xml",
)


def url_decode(s):
    """URL-decode (%3D -> =, %2F -> /, %2B -> +)"""
    return unquote(s)


def b64_decode_safe(b64_str):
    """
    对 URL-decode 后的 base64 字符串做 base64 decode，
    返回原始字节。失败时返回 None。
    """
    if b64_str is None:
        return None
    s = b64_str.strip()
    # 补齐 padding
    pad = (-len(s)) % 4
    s_padded = s + ("=" * pad)
    try:
        return base64.b64decode(s_padded, validate=False)
    except (binascii.Error, ValueError):
        return None


def hex_head(b, n=16):
    """返回前 n 字节的 hex 字符串，不足则全显示"""
    if b is None:
        return "<decode-failed>"
    return b[:n].hex()


def main():
    if not os.path.isfile(XML_PATH):
        print("[ERROR] 找不到文件:", XML_PATH)
        return

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    # 收集所有 <string> 条目
    # 也顺带统计 <int> 等非 string 条目数量（仅作参考）
    entries = []  # list of dict
    int_count = 0
    other_count = 0

    for child in root:
        tag = child.tag
        if tag == "string":
            raw_key = child.attrib.get("name", "")
            raw_val = (child.text or "")
            entries.append({"raw_key": raw_key, "raw_val": raw_val})
        elif tag == "int":
            int_count += 1
        else:
            other_count += 1

    print("=" * 70)
    print("Phigros PlayerPrefs 存档分析")
    print("=" * 70)
    print(f"文件路径: {XML_PATH}")
    print(f"总 <string> 条目数: {len(entries)}")
    print(f"非 string 条目: <int>={int_count}, 其他={other_count}")
    print()

    # 解析每个条目
    parsed = []  # 每项: dict(raw_key, raw_val, key_b64, val_b64, key_bytes, val_bytes, key_ok, val_ok)
    key_decode_fail = 0
    val_decode_fail = 0
    non_b64_entries = 0  # 看起来根本不是 base64 的条目（比如 unity.* 明文）

    for e in entries:
        raw_key = e["raw_key"]
        raw_val = e["raw_val"]

        key_b64 = url_decode(raw_key)
        val_b64 = url_decode(raw_val)

        key_bytes = b64_decode_safe(key_b64)
        val_bytes = b64_decode_safe(val_b64)

        key_ok = key_bytes is not None
        val_ok = val_bytes is not None

        if not key_ok:
            key_decode_fail += 1
        if not val_ok:
            val_decode_fail += 1

        # 如果两者都无法 base64 decode，可能本身就是明文（如 unity.player_session_count）
        if not key_ok and not val_ok:
            non_b64_entries += 1

        parsed.append({
            "raw_key": raw_key,
            "raw_val": raw_val,
            "key_b64": key_b64,
            "val_b64": val_b64,
            "key_bytes": key_bytes,
            "val_bytes": val_bytes,
            "key_ok": key_ok,
            "val_ok": val_ok,
        })

    print("解码情况:")
    print(f"  key base64 decode 失败: {key_decode_fail}")
    print(f"  val base64 decode 失败: {val_decode_fail}")
    print(f"  看起来是明文（key/val 均非 base64）的条目数: {non_b64_entries}")
    print()

    # ------------------------------------------------------------------
    # 4. 统计
    # ------------------------------------------------------------------
    # 仅对成功 decode 的条目做统计
    key_lens = [len(p["key_bytes"]) for p in parsed if p["key_ok"]]
    val_lens = [len(p["val_bytes"]) for p in parsed if p["val_ok"]]

    key_len_dist = Counter(key_lens)
    val_len_dist = Counter(val_lens)

    print("-" * 70)
    print("【key 字节长度分布】")
    for length in sorted(key_len_dist.keys()):
        cnt = key_len_dist[length]
        mod16 = "16的倍数" if length % 16 == 0 else "非16倍数"
        print(f"  len={length:4d}  count={cnt:4d}  [{mod16}]")
    print()

    print("-" * 70)
    print("【value 字节长度分布】")
    for length in sorted(val_len_dist.keys()):
        cnt = val_len_dist[length]
        mod16 = "16的倍数" if length % 16 == 0 else "非16倍数"
        print(f"  len={length:4d}  count={cnt:4d}  [{mod16}]")
    print()

    # 出现频率最高的 value（按原始字节统计）
    val_bytes_counter = Counter()
    for p in parsed:
        if p["val_ok"]:
            val_bytes_counter[p["val_bytes"]] += 1

    print("-" * 70)
    print("【出现频率最高的 value（top 10）】")
    if val_bytes_counter:
        for i, (vb, cnt) in enumerate(val_bytes_counter.most_common(10), 1):
            print(f"  #{i:2d}  出现 {cnt:4d} 次  "
                  f"len={len(vb):3d}  hex(head16)={vb[:16].hex()}")
    else:
        print("  (无)")
    print()

    # 同样统计 key 是否有重复（一般不该重复）
    key_bytes_counter = Counter()
    for p in parsed:
        if p["key_ok"]:
            key_bytes_counter[p["key_bytes"]] += 1
    dup_keys = [(k, c) for k, c in key_bytes_counter.items() if c > 1]
    print("-" * 70)
    print("【key 重复情况】")
    if dup_keys:
        print(f"  发现 {len(dup_keys)} 个重复 key:")
        for k, c in dup_keys[:10]:
            print(f"    count={c}  len={len(k)}  hex(head16)={k[:16].hex()}")
    else:
        print("  无重复 key（所有 key 唯一）")
    print()

    # ------------------------------------------------------------------
    # 5. 打印前 20 个条目的详细信息
    # ------------------------------------------------------------------
    print("-" * 70)
    print("【前 20 个条目详情】")
    for i, p in enumerate(parsed[:20], 1):
        print(f"  [{i:2d}]")
        print(f"      URL-decoded key(b64)   : {p['key_b64']}")
        print(f"      URL-decoded value(b64) : {p['val_b64']}")
        if p["key_ok"]:
            print(f"      key 字节长度 : {len(p['key_bytes'])}")
        else:
            print(f"      key 字节长度 : <decode-failed>")
        if p["val_ok"]:
            print(f"      val 字节长度 : {len(p['val_bytes'])}")
        else:
            print(f"      val 字节长度 : <decode-failed>")
        print(f"      key 前16字节 hex : {hex_head(p['key_bytes'], 16)}")
        print(f"      val 前16字节 hex : {hex_head(p['val_bytes'], 16)}")
    print()

    # ------------------------------------------------------------------
    # 6. 加密模式线索判断
    # ------------------------------------------------------------------
    print("-" * 70)
    print("【加密模式线索判断】")

    # 6a. 相同明文是否产生相同密文
    #     对于 value：如果有同一个 value 字节出现多次，且对应 key 不同，
    #     那么这些 key 加密后是否相同？反过来：同一个 value 出现多次，
    #     说明该 value（明文/密文）确实固定 —— 若是加密后的密文，则说明
    #     相同明文产生相同密文（ECB 或固定 IV CBC）。
    same_pt_same_ct = False
    if val_bytes_counter:
        top_val, top_cnt = val_bytes_counter.most_common(1)[0]
        if top_cnt > 1:
            same_pt_same_ct = True
            print(f"  * 同一 value 字节串出现 {top_cnt} 次 "
                  f"(len={len(top_val)}, hex(head16)={top_val[:16].hex()})")
            print(f"    -> 说明【相同明文 -> 相同密文】，符合 ECB 或固定 IV 的 CBC 特征。")
        else:
            print("  * 未发现重复 value，无法从重复性判断。")
    print()

    # 6b. 字节长度是否为 16 的倍数（AES block = 16）
    key_total = len(key_lens)
    val_total = len(val_lens)
    key_mod16 = sum(1 for l in key_lens if l % 16 == 0)
    val_mod16 = sum(1 for l in val_lens if l % 16 == 0)

    print(f"  * key 字节长度为 16 倍数的: {key_mod16} / {key_total}  "
          f"({(key_mod16 / key_total * 100) if key_total else 0:.2f}%)")
    print(f"  * val 字节长度为 16 倍数的: {val_mod16} / {val_total}  "
          f"({(val_mod16 / val_total * 100) if val_total else 0:.2f}%)")

    if key_mod16 == key_total and key_total > 0:
        print("    -> 所有 key 长度均为 16 倍数，强烈暗示 AES-ECB/CBC（block=16）。")
    elif key_mod16 / key_total > 0.9 if key_total else False:
        print("    -> 绝大多数 key 长度为 16 倍数，提示 AES block 对齐（少数可能是明文条目）。")
    else:
        print("    -> key 长度并不全是 16 倍数，可能存在流式加密/明文条目。")

    if val_mod16 == val_total and val_total > 0:
        print("    -> 所有 val 长度均为 16 倍数，强烈暗示 AES-ECB/CBC（block=16）。")
    elif val_mod16 / val_total > 0.9 if val_total else False:
        print("    -> 绝大多数 val 长度为 16 倍数，提示 AES block 对齐（少数可能是明文条目）。")
    else:
        print("    -> val 长度并不全是 16 倍数，可能存在流式加密/明文条目。")
    print()

    # 6c. 进一步：对于【同一个 value 出现多次】的情况，
    #     检查这些条目的 key 是否前缀有共同字节（可能是 ECB 模式下
    #     相同前缀明文产生相同前缀密文）。仅作展示。
    print("  * 进一步：检查最高频 value 对应的多条 key 是否有共同前缀字节")
    if val_bytes_counter:
        top_val, top_cnt = val_bytes_counter.most_common(1)[0]
        if top_cnt > 1:
            same_val_keys = [p["key_bytes"] for p in parsed
                             if p["val_ok"] and p["val_bytes"] == top_val
                             and p["key_ok"]]
            # 找共同前缀
            if same_val_keys:
                common_prefix = same_val_keys[0]
                for kb in same_val_keys[1:]:
                    # 截断到共同前缀
                    n = 0
                    for a, b in zip(common_prefix, kb):
                        if a == b:
                            n += 1
                        else:
                            break
                    common_prefix = common_prefix[:n]
                print(f"    共 {len(same_val_keys)} 个 key 指向同一 value，"
                      f"共同前缀长度 = {len(common_prefix)} 字节")
                if len(common_prefix) > 0:
                    print(f"    共同前缀 hex: {common_prefix.hex()}")
                else:
                    print("    这些 key 没有共同字节前缀 "
                          "(说明 key 是不同的明文，但加密到同一 value)。")
    print()

    # 6d. 综合
    print("  【综合判断】")
    if same_pt_same_ct and key_mod16 == key_total and val_mod16 == val_total:
        print("    -> 高度疑似 AES-ECB 或固定 IV 的 CBC 模式。")
        print("       理由：(1) 相同 value 反复出现；(2) 所有长度均为 16 倍数。")
    elif same_pt_same_ct:
        print("    -> 存在相同明文->相同密文现象，但长度不全是 16 倍数，")
        print("       可能是流式加密（如 CTR/RC4）或掺杂了明文条目。")
    else:
        print("    -> 证据不足，无法确定加密模式。")

    print("=" * 70)


if __name__ == "__main__":
    main()
