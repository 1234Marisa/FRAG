# FRAG (Factual Retrieval and Answer Generation)

一个基于事实检索和答案生成的智能问答系统。

## 功能特点

- 基于树状思维的角度分析
- 多源信息检索
- 智能答案生成

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/你的用户名/FRAG.git
cd FRAG
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scriptsctivate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 设置 API 密钥：
```bash
export OPENAI_API_KEY='你的OpenAI密钥'
export SERPAPI_API_KEY='你的SerpAPI密钥'
```

2. 运行程序：
```bash
python main.py
```

## 项目结构

- `aspects_generation/`: 角度树生成模块
- `retrieval/`: 信息检索模块
- `answer_generator/`: 答案生成模块
- `data/`: 数据文件

## 许可证

MIT License
