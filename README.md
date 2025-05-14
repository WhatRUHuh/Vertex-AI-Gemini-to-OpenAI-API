# Vertex AI Gemini to OpenAI API 

本项目提供一个基于 FastAPI 的代理服务，旨在将 vertex ai快速模式 API 的请求转换为 OpenAI Chat Completion API 兼容的格式。通过此服务，原先为 OpenAI 模型开发的应用能够以最小的代码改动与 vertex ai快速模式 模型进行交互。

## 主要特性

*   **OpenAI API 兼容性**：模拟 OpenAI 的 `/v1/chat/completions` 接口，支持流式及非流式响应。
*   **Vertex AI 集成**：后端通过 Google Vertex AI SDK 与 `gemini` 模型通信。
*   **Docker 化部署**：包含 `Dockerfile` 与 `docker-compose.yml`，便于快速部署。
*   **环境变量配置**：API 密钥等敏感信息通过 `.env` 文件管理，增强安全性。

## 环境准备

*   Docker
*   Docker Compose

## 快速启动

1.  **克隆代码库**：
    ```bash
    git clone https://github.com/WhatRUHuh/Vertex-AI-Gemini-to-OpenAI-API
    cd Vertex-AI-Gemini-to-OpenAI-API
    ```

2.  **配置环境变量**：
    *   复制 `.env.example` 文件为 `.env`:
        ```bash
        cp .env.example .env
        ```
    *   编辑 `.env` 文件，填入您的 API 密钥：
        ```env
        VERTEX_AI_API_KEY="请替换为您的Vertex AI API密钥"
        PROXY_AI_KEY="请替换为您设定的代理访问密钥"
        ```

3.  **使用 Docker Compose 构建并运行**：
    ```bash
    docker-compose up --build -d
    ```
    首次构建可能需要一些时间。

4.  **接口测试**：
    服务默认监听于 `http://localhost:8001`，可向 `/v1/chat/completions` 端点发送 POST 请求。

    **请求示例（非流式）**：
    ```bash
    curl -X POST http://localhost:8001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer 您的PROXY_API_KEY" \
    -d '{
        "model": "gemini-pro",
        "messages": [
            {"role": "user", "content": "你好！"}
        ],
        "stream": false
    }'
    ```

## 项目结构

```
.
├── .env                # 环境变量 (Git忽略)
├── .env.example        # 环境变量示例
├── .gitignore          # Git忽略配置
├── Dockerfile          # Docker镜像定义
├── docker-compose.yml  # Docker Compose配置
├── main.py             # FastAPI应用主逻辑
├── README.md           # 本文档
└── requirements.txt    # Python依赖