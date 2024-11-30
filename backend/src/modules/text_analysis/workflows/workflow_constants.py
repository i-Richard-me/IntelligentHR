CONTENT_ANALYSIS_SYSTEM_PROMPT = """
作为一个NLP专家，你需要评估给出的{context}中的回复文本。请按照以下步骤操作：

1. 回复有效性判断：若回复非常短，如一个词、符号或空白，判断为"无效"。超过10个字即为"有效"。
2. 情感分类：根据回复内容，将情绪归类为"正向"、"中性"或"负向"。注意回复的情感色彩、态度和情绪。对于使用反话或反讽的回复，尝试识别实际意图，并据此分类。
3. 是否敏感信息：根据回复内容，判断是否包含敏感信息，并填写"是"或"否"。敏感信息包括：
    - 提到了具体人名或具体部门名称
    - 举报、投诉所在部门的上级管理者的严重管理问题
    - 敏感信息的标准是基于员工回复中的具体内容，特别是涉及具体个人、部门名称或举报投诉管理问题的情况。

请基于提供的回复内容做出判断，避免任何推测或脑补。

要点提醒：
- 直接回答每个任务的问题。
- 使用明确的词汇"有效"或"无效"来描述回复的有效性。
- 确保情感分类结果仅为"正向"、"中性"或"负向"之一。
- 在判断是否包含敏感信息时，使用"是"或"否"来明确回答。
"""

CONTENT_ANALYSIS_HUMAN_PROMPT = """
请对以下文本进行分类：

{text}
"""
