# 使用官方Python运行时作为父镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器的/app目录
COPY . /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露Streamlit默认端口
EXPOSE 8510

# 运行应用
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8510", "--server.address=0.0.0.0"]