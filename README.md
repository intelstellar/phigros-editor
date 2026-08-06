# Phigros 存档编辑器 by FuwaMintNEKO

一个用于查看和编辑 Phigros 本地存档（`playerprefs.xml`）的图形化工具。

## 功能

- 自动解密/加密 Phigros 的自定义 AES-CBC 存档格式
- 图形界面浏览所有存档条目（Key / Value / 类型 / 状态）
- 实时搜索过滤（支持按 Key、Value 或全部搜索）
- 编辑加密字符串、明文字符串（如 `unity.*`）和 int 类型条目
- JSON 格式化/压缩快捷按钮
- 保存时自动备份原文件（`.bak`），仅重新加密被修改的条目
- 命令行工具支持批量解密导出为 JSON

## 文件说明

| 文件 | 说明 |
|------|------|
| `phigros_editor.py` | 图形化编辑器（主程序） |
| `phigros_decrypt.py` | 解密/加密库 + 命令行工具 |
| `analyze_phigros.py` | 存档分析脚本（只读，用于调试加密格式） |
| `LocalSave_reference.cs` | 加密表源码（sBox / invSBox / IV / rcon / tempArray） |

## 用法

### 图形界面

```bash
python phigros_editor.py
```

点击「打开存档」选择 `com.PigeonGames.Phigros.v2.playerprefs.xml` 文件，编辑 Value 后点击「应用修改到列表」，最后点「保存」写回。

### 命令行

```bash
# 解密存档并导出为 JSON
python phigros_decrypt.py <存档.xml> -o <输出.json>

# 显示详细过程
python phigros_decrypt.py <存档.xml> -v
```

## 依赖

- Python 3.8+
- 仅使用标准库（tkinter、xml、base64 等），无需安装第三方包

## 免责声明

本项目仅供学习与交流使用，不用于任何商业用途。

- Phigros 游戏的版权归 [PigeonGames](https://pigeongames.cn/) 所有
- 加密算法参考自 [PhigrosLibraryCSharp](https://github.com/yt6983138/PhigrosLibraryCSharp)（MIT 协议）
- 使用本工具修改存档可能导致数据损坏或账号风险，后果自负
- 如有侵权，请联系删除
