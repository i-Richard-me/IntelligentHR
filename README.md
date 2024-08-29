# IntelligentHR
Intelligent HR solutions for the data-driven enterprise.

智能HR助手是一个实验性的人力资源管理工具集，旨在探索AI技术在HR领域的应用潜力。
工具集涵盖了从数据处理、文本分析到决策支持的多个HR工作分析环节，致力于为人力资源管理提供全方位的智能化解决方案。

## 快速开始

1. 克隆仓库:
   ```
   git clone https://github.com/i-Richard-me/IntelligentHR
   cd IntelligentHR
   ```

2. 配置环境变量:
   复制 `.env.example` 为 `.env` 并填写必要的 API 密钥。

3. 使用Docker启动服务:
   
   基础服务启动:
   ```
   docker-compose up --build
   ```
   
   如果您没有现有的Langfuse和Milvus服务,可以使用以下命令启动所有服务:
   ```
   docker-compose --profile langfuse --profile milvus up --build
   ```
   
   如果您只需要其中一个服务:
   - 仅启动Langfuse: `docker-compose --profile langfuse up --build`
   - 仅启动Milvus: `docker-compose --profile milvus up --build`

4. 访问应用:
   - 智能HR助手: 打开浏览器,访问 `http://localhost:8510`
   - Langfuse服务 (如果启用): 访问 `http://localhost:3000`
   - Milvus Attu界面 (如果启用): 访问 `http://localhost:3010`

5. 使用现有服务:
   如果您已有Langfuse或Milvus服务,请确保在 `.env` 文件中正确配置相关连接信息,无需启动对应的Docker服务。

6. 其他可用服务 (如果启用):
   - PostgreSQL数据库: 可通过 localhost:5432 访问
   - Minio对象存储: 控制台可通过 `http://localhost:9001` 访问
   - Milvus服务: 可通过 localhost:19530 连接

注意: 请根据您的实际需求和现有环境选择适当的启动方式。

## 贡献

我们欢迎并感谢任何形式的贡献。请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目。

## 行为准则

本项目采用了贡献者公约定义的行为准则，以营造一个开放和友好的社区环境。详情请见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 许可

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 免责声明

本项目处于实验阶段，主要用于学习和研究目的。在实际应用中使用时请谨慎，并自行承担相关风险。