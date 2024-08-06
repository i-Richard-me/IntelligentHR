# 贡献指南

非常感谢您对智能HR助手项目感兴趣！我们欢迎并鼓励社区成员参与项目的开发和改进。本文档将指导您如何为项目做出贡献。

## 如何贡献

有多种方式可以为项目做出贡献：

1. 报告 Bug
2. 提出新功能建议
3. 提交代码改进
4. 完善文档
5. 分享使用经验和反馈

### 报告 Bug

如果您发现了 Bug，请通过 GitHub Issues 报告。创建 Issue 时，请包含以下信息：

- 清晰简洁的标题
- Bug 的详细描述
- 重现 Bug 的步骤
- 预期行为和实际行为
- 相关的截图（如果有）
- 您的运行环境（操作系统、Python 版本等）

### 提出新功能建议

如果您有新功能的想法，也请通过 GitHub Issues 提出。创建 Issue 时，请包含以下信息：

- 清晰简洁的标题
- 详细的功能描述
- 使用场景和潜在收益
- 可能的实现方式（如果有）

### 提交代码改进

1. Fork 项目仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 将您的改动推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个 Pull Request

在提交 Pull Request 之前，请确保：

- 您的代码符合项目的编码规范
- 您已经为新功能添加了相应的测试
- 所有测试都能通过
- 您已经更新了相关文档（如果需要）

### 完善文档

文档对于项目的可用性和可维护性至关重要。如果您发现文档中有不清晰、过时或错误的地方，欢迎提交改进。

### 分享使用经验和反馈

您的使用经验和反馈对我们非常宝贵。您可以通过以下方式分享：

- 在项目的 Discussions 区分享您的使用案例
- 在社交媒体上谈论项目，并给我们反馈
- 写博客文章介绍如何使用项目

## 开发环境设置

1. 克隆仓库：
   ```
   git clone https://github.com/i-Richard-me/IntelligentHR
   cd IntelligentHR
   ```

2. 创建并激活虚拟环境：
   ```
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上使用 venv\Scripts\activate
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 配置环境变量：
   复制 `.env.example` 为 `.env` 并填写必要的 API 密钥。

5. 运行测试：
   ```
   python -m unittest discover tests
   ```

## 代码规范

- 遵循 PEP 8 编码规范
- 使用有意义的变量名和函数名
- 为函数和类添加文档字符串
- 保持代码简洁，避免不必要的复杂性

## 提问

如果您有任何问题，欢迎在 GitHub Issues 中提问。我们会尽快回复您的问题。

再次感谢您的贡献！