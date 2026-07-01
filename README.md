# GitHub Trending Audio

> 自动获取 GitHub 最新高价值项目 → 生成通俗易懂的音频文档 → 合成 MP3 语音

站在巨人的肩膀上，不重复造轮子：基于 **GitHub 官方 API** + **edge-tts（微软免费 TTS）**，零成本实现从代码仓库到音频播客的全流程自动化。

## 核心特性

- **零成本**：edge-tts 使用微软 Edge 在线语音服务，完全免费，无需 API Key，无需 GPU
- **高质量语音**：神经网络语音引擎，音质接近商业 TTS 服务（Azure / 讯飞）
- **双语支持**：中文（晓晓、云希等）和英文（Jenny、Guy 等）多款语音可选
- **智能文档**：自动提取 README 关键信息，生成播客式口语化脚本
- **LLM 增强**（可选）：接入大模型生成更生动的内容，支持 OpenAI / DeepSeek / 通义千问
- **灵活过滤**：按编程语言、topic、star 数、时间范围筛选项目

## 工作流程

```
GitHub Search API          edge-tts (微软 TTS)
      │                          │
      ▼                          │
┌──────────┐    ┌──────────┐     │
│ 获取趋势  │ -> │ 生成文档  │ ──→ │ → MP3 音频
│ 高价值项目│    │ (模板/LLM)│     │
└──────────┘    └──────────┘     │
     │              │            │
     ▼              ▼            ▼
  README 提取   Markdown + 脚本  语音合成
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 基本用法

```bash
# 获取最近 7 天的 Python 热门项目，生成中文音频
python main.py --days 7 --limit 3 --language python

# 获取 50 个项目（自动分页，突破单页限制）
python main.py --limit 50 --language python

# 串行模式：逐个项目处理，边获取边生成（适合大量项目）
python main.py --limit 100 --serial --language python

# 获取 AI/LLM 相关项目
python main.py --topic llm --limit 5

# 英文播客
python main.py --lang en --voice en-US-GuyNeural

# 调整语速（加速 10%）
python main.py --rate "+10%"
```

### 3. 输出文件

运行后在 `output_YYYYMMDD_HHMMSS/` 目录下生成：

| 文件 | 说明 |
|------|------|
| `owner_repo.md` | Markdown 格式的项目文档 |
| `owner_repo_script.txt` | TTS 朗读脚本（纯文本） |
| `owner_repo.mp3` | 最终音频文件 |

## 可选配置

### GitHub Token（提高 API 配额）

```bash
export GITHUB_TOKEN=ghp_xxxxx
```

无 Token：每小时 10 次搜索（日常够用）
有 Token：每小时 30 次搜索 + 5000 次普通请求

### LLM 增强（更生动的播客脚本）

```bash
pip install openai

# 使用 OpenAI
export LLM_API_KEY=sk-xxx
python main.py --use-llm --limit 2

# 使用 DeepSeek（更便宜）
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat
python main.py --use-llm --limit 2

# 使用通义千问
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export LLM_MODEL=qwen-plus
python main.py --use-llm --limit 2
```

## 可用语音

```bash
# 查看预设语音
python main.py --list-voices
```

| 语言 | 别名 | 语音名称 | 特点 |
|------|------|----------|------|
| 中文 | female_warm | zh-CN-XiaoxiaoNeural | 晓晓，温暖亲切（默认） |
| 中文 | male_warm | zh-CN-YunxiNeural | 云希，温暖沉稳 |
| 中文 | female_lively | zh-CN-XiaoyiNeural | 晓伊，活泼自然 |
| 中文 | male_calm | zh-CN-YunyangNeural | 云扬，沉稳大气 |
| 英文 | female_warm | en-US-JennyNeural | Jenny，温暖亲切（默认） |
| 英文 | male_warm | en-US-GuyNeural | Guy，温暖自然 |
| 英文 | female_calm | en-US-AriaNeural | Aria，沉稳优雅 |
| 英文 | male_calm | en-US-DavisNeural | Davis，沉稳低沉 |

完整语音列表：[Azure TTS 支持的语言](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--days` | 7 | 查看最近 N 天创建的项目 |
| `--limit` | 5 | 获取前 N 个项目 |
| `--language` | None | 按编程语言过滤（python、rust 等） |
| `--topic` | None | 按 topic 过滤（ai、llm、web 等） |
| `--min-stars` | 50 | 最低 star 数阈值 |
| `--lang` | zh | 输出语言（zh / en） |
| `--voice` | 自动 | 指定语音名称 |
| `--rate` | +0% | 语速（+10% 加速，-10% 减速） |
| `--use-llm` | False | 启用 LLM 增强 |
| `--serial` | False | 串行模式（逐个项目处理，适合大量项目） |
| `--token` | None | GitHub Token |
| `--output` | 自动 | 输出目录 |
| `--list-voices` | - | 列出可用语音 |

## 分页与串行模式

### 分页获取（默认）

`--limit` 支持超过 30 的值，工具会自动翻页获取：

- 每页最多 100 条（GitHub API 上限）
- 自动翻页直到达到 `--limit` 数量
- GitHub Search API 总上限 1000 条
- 突破了原先单页 30 条的限制

### 串行模式（`--serial`）

默认批量模式下，工具先获取所有项目再统一处理。串行模式则逐个项目完整处理：

```
项目1: 获取 → README → 文档 → 音频  ✓ 立即可用
项目2: 获取 → README → 文档 → 音频  ✓ 立即可用
项目3: 获取 → README → 文档 → 音频  ✓ 立即可用
...
```

| 对比 | 批量模式（默认） | 串行模式（`--serial`） |
|------|-----------------|----------------------|
| 获取方式 | 先全部获取 | 逐个获取 |
| 首个音频产出 | 等所有项目获取完 | 第一个项目处理完即产出 |
| 内存占用 | 缓存全部结果 | 仅当前项目 |
| 容错性 | 某步失败影响整批 | 某项目失败不影响其他 |
| 适用场景 | 少量项目（< 30） | 大量项目（30+） |

## 技术选型说明

### 为什么选 edge-tts？

| 方案 | 成本 | 质量 | 部署难度 | 中文支持 |
|------|------|------|----------|----------|
| **edge-tts** | **免费** | **高** | **极低（pip install）** | **优秀** |
| Azure TTS | 按字符收费 | 高 | 低 | 优秀 |
| ElevenLabs | 按字符收费 | 极高 | 低 | 一般 |
| ChatTTS | 免费（需 GPU） | 高 | 高（需显卡） | 优秀 |
| Bark | 免费（需 GPU） | 高 | 高（需显卡） | 一般 |
| Coqui TTS | 免费（需 GPU） | 中高 | 中 | 一般 |

edge-tts 在"成本、质量、易用性"三者间取得最佳平衡：调用微软云端服务，本地无需 GPU，零成本且音质优秀。

### 为什么用 GitHub Search API 而非爬虫？

- 官方 API 稳定可靠，不受页面改版影响
- 支持精细过滤（语言、topic、star 数、时间范围）
- 免费，无需第三方爬虫服务

## 项目结构

```
gh_trending_audio/
├── main.py                          # 入口文件
├── requirements.txt                 # 依赖
├── README.md                        # 本文档
└── gh_trending_audio/
    ├── __init__.py
    ├── github_fetcher.py            # GitHub API 获取趋势项目
    ├── document_generator.py        # 生成音频文档（模板/LLM）
    ├── tts_engine.py                # edge-tts 语音合成
    ├── llm_enhancer.py              # 可选 LLM 增强
    └── cli.py                       # 命令行界面
```

## License

MIT
