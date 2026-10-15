# Phigros Save Editor by FuwaMintNEKO 
(Yeah this tool is completely written by FuwaMintNEKO and i only translated this from Chinese to English using AI bc idk how to read Chinese TvT & added some features such as multiselect key & batch value editing for convenience uses)
(thank you so much for creating this amazing tool FuwaMintNEKO / 非常感谢你制作了这款超棒的工具，FuwaMintNEKO (┬┬﹏┬┬))

A graphical tool for viewing and editing local Phigros save files (`playerprefs.xml`).

## Features

- Automatically decrypt/encrypt Phigros’ custom AES-CBC save file format
- Graphical interface for browsing all archive entries (Key / Value / Type / Status)
- Real-time search and filtering (supports searching by Key, Value, or all fields)
- Edit encrypted strings, plaintext strings (e.g., `unity.*`), and int-type entries
- Shortcut buttons for JSON formatting and compression
- Automatically backs up the original file (`.bak`) upon saving; only re-encrypts modified entries
- Command-line tool supports batch decryption and export to JSON

## File Description

| File | Description |
|------|------|
| `phigros_editor.py` | Graphical editor (main program) (the only thing I translated) |
| `phigros_decrypt.py` | Decryption/encryption library + command-line tool |
| `analyze_phigros.py` | Save file analysis script (read-only, used for debugging the encryption format) |
| `LocalSave_reference.cs` | Encryption table source code (sBox / invSBox / IV / rcon / tempArray) |

## Usage

### How to use

Install the latest version of Python, then download the entire repository to your computer, extract it, then open a command prompt and type:
```bash
python phigros_editor.py
```
Then click Enter, after that you have to click on Open Save button on top left corner -> find your Phigros save file and open it -> Edit the way you want -> click on "Apply Changes to List" after done editing -> click on "Save (Encrypt & Write)" to save your save file 

With phigros_decrypt.py, you can use it to decrypt your original save file into readable text by typing "python phigros_decrypt.py putsavefilenamehere.xml -v"
## 依赖 (Dependencies)

- Python 3.8+
- 仅使用标准库（tkinter、xml、base64 等），无需安装第三方包 (Uses only standard libraries (tkinter, xml, base64, etc.); no third-party packages need to be installed)

## 免责声明 (Disclaimer)

本项目仅供学习与交流使用，不用于任何商业用途。
(This project is intended solely for educational and exchange purposes and is not intended for any commercial use.)

- Phigros 游戏的版权归 [PigeonGames](https://pigeongames.cn/) 所有
(The copyright for the Phigros game belongs to [PigeonGames](https://pigeongames.cn/))
- 加密算法参考自 [PhigrosLibraryCSharp](https://github.com/yt6983138/PhigrosLibraryCSharp)（MIT 协议）
The encryption algorithms are based on [PhigrosLibraryCSharp](https://github.com/yt6983138/PhigrosLibraryCSharp) (MIT License)
- 使用本工具修改存档可能导致数据损坏或账号风险，后果自负
(Using this tool to modify save files may result in data corruption or account risks; you assume all responsibility for the consequences)
- 如有侵权，请联系删除
(If you believe your rights have been infringed, please contact us to have the content removed)
