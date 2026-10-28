# banano2gif 🍌➡️🎞️

> **全能 AI 表情包与动态帧生成引擎**  
> 原生支持【**纯 Web 前端免后端运行 (Pure Web / GitHub Pages)**】！  
> 原生支持【**4K 超高清九宫格出图 (4096x4096)**】！  
> 支持【**文生动图**、**图生动图（垫图/参考图锁脸）**、**动作生成迁移 (Motion Transfer)**、**视频直转动图**】全模态！  
> 原生支持【**8-bit Alpha 完整半透明通道 WebP 与透明 GIF**】智能去底！  
> 默认内置官方原生 SDK，开箱即用。彻底去除数字角标，精准自适应对齐切帧，合成丝滑无缝循环动图。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Web Version](https://img.shields.io/badge/Web%20App-Pure%20HTML%2FJS-blueviolet.svg)](web/index.html)
[![API Platform](https://img.shields.io/badge/API%20Platform-HrioAPI-orange.svg)](https://hrioapi.hrio.site)

---

## 🌟 效果展示 (Demo Showcase)

| 1. AI 渲染九宫格原图 (纯净无角标) | 2. 智能去底透明背景循环动图 (支持 WebP / GIF) |
| :---: | :---: |
| <img src="examples/sample_grid.jpg" width="380" alt="九宫格原图" /> | <img src="examples/sample_crying_transparent.gif" width="300" alt="透明背景无缝循环动图" /> |

---

## 🌐 纯 Web 前端免安装方案 (Pure Web SPA)

如果你不想配置 Python 环境，可以直接使用项目中附带的**纯前端单页应用 (`web/index.html`)**：
* **零后端、免装环境**：只需双击 `web/index.html` 即可在任意浏览器（Edge、Chrome、Safari）中打开运行；
* **支持 GitHub Pages 一键托管**：在仓库设置中开启 GitHub Pages，即可拥有全网可访问的个人在线生成站；
* **浏览器端纯算法抠图与切片**：内置基于 HTML5 Canvas 的外边缘 BFS 去底与九宫格裁切算法，毫秒级响应；
* **离线模式**：甚至支持在断网情况下，直接将本地已有的九宫格大图拖拽入网页，进行纯本地离线切图、透明化与 GIF 动图合成！

---

## 🔑 获取 API Key

本项目默认内置封装了轻量级原生 SDK，直连 **HrioAPI** 官方平台（全面接入 `gemini-nano-banana-2.1`、`gpt-image-2`、`gemini-3.1-flash-image` 等主流多模态生图大模型）：

1. 前往官方网站注册登录：👉 **[https://hrioapi.hrio.site](https://hrioapi.hrio.site)**
2. 进入用户后台创建并复制您的专属 API Key (`sk-xxxxxxxx`)。
3. 配置环境变量或直接在命令行中传入：
   ```bash
   # Linux / macOS
   export HRIO_API_KEY="sk-xxxxxxxx"

   # Windows (CMD)
   set HRIO_API_KEY=sk-xxxxxxxx

   # Windows (PowerShell)
   $env:HRIO_API_KEY="sk-xxxxxxxx"
   ```

---

## 💎 4K 超高清出图与自适应裁切 (`--4k`)

大模型已具备 4K 级别的图像输出能力，`banano2gif` 全面升级为**分辨率自适应流水线**：
* **4096 × 4096 超高分辨率生成**：只需传入 `--4k` 参数，即可调用 4K 规格九宫格大图；
* **自适应中心裁切**：算法动态计算图像尺寸，1024 图切出 320px 单元格，**4K 图直接切出 1280 × 1280 单帧原生超清大图**！
* **高质量超采样缩放 (`--export-size`)**：若用于微信/QQ 表情包，可通过 `--export-size 320` 自动将 4K 帧进行 Lanczos 超采样缩放——相比直接生成小图，**线条更锐利、噪点为零、画质呈现降维打击**！

---

## 🚀 四大核心生成模式 (All-in-One Multimodal)

### 1. 🎭 动作生成迁移 (Motion Transfer)
直接将**现有的表情包动图 (.gif, .webp) 或一段短视频 (.mp4)** 中的神态动作，迁移至**全新的目标角色图**上！
```bash
python main.py --image "my_avatar.png" --motion-source "funny_dance.gif" --transparent
```

### 2. 🖼️ 图生动图 / 参考图生图 (Image-to-GIF)
传入用户的头像、照片或立绘作为**参考图（垫图）**，在保持角色面部、五官、发型与穿搭高度一致的前提下，生成专属动作表情包！
```bash
python main.py "委屈哭泣流眼泪" --image "avatar.png" --preset crying --4k --transparent
```

### 3. 📝 文生动图 (Text-to-GIF)
输入纯文本提示词或选用内置预设，AI 自动根据 9 帧微幅渐变机理生成连续无缝的九宫格并切片合成动图。
```bash
python main.py "可爱的3D柴犬戴着红色围巾" --preset waving --transparent
```

### 4. 🎥 视频转动图 (Video-to-GIF)
支持 MP4、MOV、WebM、AVI 等任意格式视频，自动采样关键帧并进行中心正方形裁切，直接转换为高画质轻量表情包。
```bash
python main.py --video "dance.mp4" --fps 10
```

---

## 👻 智能透明背景去底化 (`--transparent`)

加上 `--transparent` 参数，算法将通过**外边缘泛洪填充 (Exterior Boundary BFS)** 自动提取背景并生成 Alpha 通道，**100% 保护角色体内的白色衣服、高光与发夹不被误扣**：
- **WebP 格式**：支持**完整的 8-bit Alpha 通道（256 级半透明羽化抗锯齿）**，边缘如丝般顺滑，文件体积轻量，特别适合现代即时通信软件与网页展示。
- **GIF 格式**：自动映射透明调色板并配置 `disposal=2`，杜绝传统透明 GIF 的层叠残影问题。

---

## 💻 快速安装与使用

### 1. 纯 Web 界面运行
直接双击打开 `web/index.html`，输入你的 API Key 即可全图形化操作。

### 2. Python 命令行使用
```bash
git clone https://github.com/moki-flank/banano2gif.git
cd banano2gif
pip install -r requirements.txt

# 查看所有支持的内置微动作预设
python main.py --list-presets

# 4K 图生动图并开启透明背景
python main.py "委屈哭泣" --image "avatar.png" --preset crying --4k --transparent
```

---

## 📚 内置常用微动作预设列表

| 预设代码 (`--preset`) | 动作名称 | 动作循环逻辑与幅度 |
| :--- | :--- | :--- |
| `waving` | **挥手打招呼** | 手臂从胸前抬起 -> 掌心向前左右摆动 15° -> 欢快微笑 -> 降回胸前闭环循环 |
| `petting` | **温柔抚摸宠物** | 手掌凌空逼近 -> 掌心触碰额头 -> 顺滑抚摸至后颈/背部 -> 猫咪眯眼仰头享受 -> 归位闭环 |
| `laughing` | **哈哈大笑/欢脱** | 微笑挑眉 -> 仰头放声大笑 -> 肩膀微微颤动欢脱 -> 缓和回笑闭环 |
| `crying` | **委屈哭泣/泪目** | 憋嘴泛泪 -> 泪珠滑落 -> 爆出动漫瀑布泪花 -> 抽泣擦泪闭环 |
| `heart_wink` | **眨眼比心** | 灿烂微笑 -> 右眼眨眼 Wink -> 手指搓出爱心光波飘起 -> 归位闭环 |
| `thumbs_up` | **竖大拇指点赞** | 握拳抬臂 -> 伸出大拇指向前挺进点赞 -> 闪烁星芒好评 -> 缓缓收回闭环 |

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源协议。欢迎 Star 与 PR！
