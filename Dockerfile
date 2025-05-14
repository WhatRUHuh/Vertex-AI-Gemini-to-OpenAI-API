# 使用官方Python运行时作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .

# 暴露应用运行的端口
EXPOSE 8001

# 启动应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]