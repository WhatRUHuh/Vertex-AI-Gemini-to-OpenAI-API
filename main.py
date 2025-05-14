# -*- coding: utf-8 -*-
import json
import os # 导入 os 模块来访问环境变量
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from google import genai
import requests
from dotenv import load_dotenv # 导入 load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# —— 环境 & 客户端初始化 —— #

# 从环境变量中读取 Vertex AI & 反代密钥
VERTEX_AI_API_KEY = os.getenv("VERTEX_AI_API_KEY")
PROXY_API_KEY = os.getenv("PROXY_API_KEY")

# 检查密钥是否成功加载
if not VERTEX_AI_API_KEY:
    raise ValueError("VERTEX_AI_API_KEY 环境变量没有设置哦！快去 .env 文件看看！")
if not PROXY_API_KEY:
    raise ValueError("PROXY_API_KEY 环境变量没有设置哦！是不是忘记写在 .env 文件里啦？")

# 初始化 Vertex SDK 客户端（用作流式）
client = genai.Client(vertexai=True, api_key=VERTEX_AI_API_KEY)

# HTTP 反代时用到的基础 Endpoint（非流式分支仍然用它）
VERTEX_AI_BASE_ENDPOINT = "https://aiplatform.googleapis.com/v1/publishers/google/models/"

app = FastAPI()


# —— Pydantic 模型 —— #

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.7
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Any = None
    max_tokens: int = 1024
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    logit_bias: Dict[str, float] = None
    user: str = None


# —— 辅助函数 —— #

def parse_chunk_text(chunk):
    """参考你本地 SDK 测试逻辑，提取 chunk 文本"""
    try:
        return chunk.candidates[0].content.parts[0].text
    except Exception:
        return None


# —— 主接口 —— #

@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    authorization: str = Header(None)
):
    # 1. 验证反代密钥
    if authorization is None or authorization.replace("Bearer ", "") != PROXY_API_KEY:
        raise HTTPException(status_code=401, detail="无效的反代密钥，您是不是输错了？")

    # 2. 构造 Vertex AI HTTP payload（给非流式用）
    vertex_ai_endpoint = f"{VERTEX_AI_BASE_ENDPOINT}{request.model}:generateContent"
    vertex_ai_contents = []
    system_message = ""
    for msg in request.messages:
        if msg.role == "system":
            system_message += msg.content + "\n"
        elif msg.role == "user":
            if system_message:
                vertex_ai_contents.append({
                    "role": "user",
                    "parts": [{"text": system_message + msg.content}]
                })
                system_message = ""
            else:
                vertex_ai_contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })
        elif msg.role == "assistant":
            vertex_ai_contents.append({
                "role": "model",
                "parts": [{"text": msg.content}]
            })
    if system_message:
        vertex_ai_contents.append({
            "role": "user",
            "parts": [{"text": system_message}]
        })

    generation_config = {
        "temperature": request.temperature,
        "topP": request.top_p,
        "maxOutputTokens": request.max_tokens
    }
    http_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": VERTEX_AI_API_KEY
    }

    # 3. 流式分支 —— 直接用 SDK 的 generate_content_stream
    if request.stream:
        def generate_stream():
            sdk_stream = client.models.generate_content_stream(
                model=request.model,
                contents=vertex_ai_contents
            )
            for chunk in sdk_stream:
                text = parse_chunk_text(chunk)
                if text:
                    openai_chunk = {
                        "id": "chatcmpl-xxxx",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    # 4. 非流式分支 —— 保留原 HTTP 转发逻辑
    try:
        resp = requests.post(
            vertex_ai_endpoint,
            headers=http_headers,
            json={
                "contents": vertex_ai_contents,
                "generationConfig": generation_config
            },
            stream=False
        )
        resp.raise_for_status()
        data = resp.json()

        # 提取回答
        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0]["content"]["parts"]
            text_content = "".join(part.get("text", "") for part in parts)

            # finish_reason 映射
            fr = data["candidates"][0].get("finishReason")
            finish_reason = None
            if fr == "STOP":
                finish_reason = "stop"
            elif fr == "MAX_OUTPUT_TOKENS":
                finish_reason = "length"

            usage = data.get("usageMetadata", {})
            openai_resp = {
                "id": "chatcmpl-xxxx",
                "object": "chat.completion",
                "created": 0,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text_content},
                    "finish_reason": finish_reason
                }],
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0)
                }
            }
            return JSONResponse(content=openai_resp)
        else:
            raise HTTPException(status_code=500, detail="Vertex AI 未返回有效的 candidates。")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"请求 Vertex AI 时发生错误：{e}")


# —— 本地启动 —— #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
