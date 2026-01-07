import os
import sys
import pandas as pd

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def init_project():
    # 1. 创建必要的文件夹
    folders = ['data', 'prompts', 'scripts']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✅ 已创建文件夹: {folder}")

    # 2. 初始化 CSV 记忆文件
    csv_path = 'data/user_words.csv'
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=['word', 'level', 'last_queried', 'score', 'status'])
        df.to_csv(csv_path, index=False)
        print(f"✅ 已创建初始词库: {csv_path}")

    # 3. 初始化 System Prompts
    prompts = {
        "linguist.md": """# Role
你是一位精通多国语言的语言学专家。
# Task
1. 识别文本中 B2 以上级别的生词。
2. 剔除用户已掌握的词汇。
3. 必须输出 JSON 格式。
# Output Format
{
  "vocabulary": [{"word": "...", "phonetic": "...", "definition": "...", "example": "..."}],
  "grammar_points": [{"point": "...", "explanation": "..."}]
}""",
        "summarizer.md": """# Role
你是一位资深内容分析师。
# Task
请用中文概括文章大意，并分条目列出核心逻辑。"""
    }

    for filename, content in prompts.items():
        path = os.path.join('prompts', filename)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已创建提示词模板: {path}")

    # 4. 创建 .env 模板
    if not os.path.exists('.env'):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# DeepSeek API Key (推荐使用)\n")
            f.write("DEEPSEEK_API_KEY=your_deepseek_key_here\n")
            f.write("\n# OpenAI API Key (可选，如果没有 DeepSeek 可以使用)\n")
            f.write("OPENAI_API_KEY=your_openai_key_here\n")
            f.write("\n# Tavily API Key (可选，用于搜索功能)\n")
            f.write("TAVILY_API_KEY=your_tavily_key_here\n")
            f.write("\n# 禁用 LangSmith 追踪\n")
            f.write("LANGCHAIN_TRACING_V2=false\n")
        print("✅ 已创建 .env 配置文件，请记得填写 API Key！")
        print("   优先使用 DEEPSEEK_API_KEY，如果没有可以配置 OPENAI_API_KEY")

if __name__ == "__main__":
    init_project()
    print("\n🚀 项目环境初始化完成！请按照以下顺序操作：")
    print("1. 在 .env 中填写你的 OpenAI Key")
    print("2. 运行 streamlit run gui.py 启动界面")