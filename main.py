import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# 加载环境变量
load_dotenv()

# 禁用 LangSmith 追踪（如果未配置 API key）
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_ENDPOINT", "")

# --- 辅助函数：创建 LLM 实例 ---
def create_llm():
    """
    创建 LLM 实例，支持 DeepSeek 和 OpenAI
    优先使用 DeepSeek，如果没有配置则使用 OpenAI
    支持从 .env 文件或 Streamlit secrets 读取配置
    """
    # 尝试从 Streamlit secrets 读取（用于 Cloud 部署）
    try:
        import streamlit as st
        deepseek_key = st.secrets.get("DEEPSEEK_API_KEY", None)
        openai_key = st.secrets.get("OPENAI_API_KEY", None)
    except:
        # 如果不在 Streamlit 环境中，从环境变量读取
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
    
    # 如果 secrets 中没有，尝试从环境变量读取（本地开发）
    if not deepseek_key:
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if not openai_key:
        openai_key = os.getenv("OPENAI_API_KEY")
    
    if deepseek_key and deepseek_key != "your_key_here":
        # 使用 DeepSeek
        return ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=deepseek_key,
            model="deepseek-chat",
            temperature=0,
            timeout=60,
            max_retries=2
        )
    elif openai_key and openai_key != "your_key_here":
        # 使用 OpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=60,
            max_retries=2
        )
    else:
        return None

# --- 1. 定义状态 ---
class AgentState(TypedDict):
    input_text: str
    known_words: List[str]
    analysis_result: dict  # 存储生词和语法
    summary_result: str    # 存储大意
    detailed_reading: str  # 存储文本细读
    mastered_new_words: List[str] # 本次学习后可能掌握的词

# --- 2. 工具函数：CSV 记忆管理 ---
def get_known_words_from_csv():
    try:
        df = pd.read_csv("data/user_words.csv")
        return df[df['status'] == 'mastered']['word'].tolist()
    except FileNotFoundError:
        return []

def mark_word_as_mastered(word: str, level: str = "N/A"):
    """将单词标记为已掌握并保存到 CSV"""
    import datetime
    
    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)
    
    try:
        # 尝试读取现有数据
        df = pd.read_csv("data/user_words.csv")
    except FileNotFoundError:
        # 如果文件不存在，创建新的 DataFrame
        df = pd.DataFrame(columns=['word', 'level', 'last_queried', 'score', 'status'])
    
    # 检查单词是否已存在
    if word in df['word'].values:
        # 更新已有单词状态
        df.loc[df['word'] == word, 'status'] = 'mastered'
        df.loc[df['word'] == word, 'score'] = 5
        df.loc[df['word'] == word, 'last_queried'] = datetime.date.today().strftime('%Y-%m-%d')
        if level != "N/A":
            df.loc[df['word'] == word, 'level'] = level
    else:
        # 插入新单词
        new_row = {
            'word': word,
            'level': level,
            'last_queried': datetime.date.today().strftime('%Y-%m-%d'),
            'score': 5,
            'status': 'mastered'
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    # 保存到 CSV
    df.to_csv("data/user_words.csv", index=False)
    return True

def get_all_words_from_csv():
    """获取所有单词（包括已掌握和未掌握的）"""
    try:
        df = pd.read_csv("data/user_words.csv")
        return df.to_dict('records')
    except FileNotFoundError:
        return []

# --- 2.1 历史记录管理 ---
HISTORY_FILE = "data/analysis_history.json"

def save_analysis_history(input_text: str, result: dict):
    """保存分析结果到历史记录"""
    import datetime
    
    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)
    
    # 读取现有历史记录
    history = load_analysis_history()
    
    # 创建新记录
    new_record = {
        "id": len(history) + 1,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_text": input_text,
        "result": result
    }
    
    # 添加到历史记录（最多保存 100 条）
    history.append(new_record)
    if len(history) > 100:
        history = history[-100:]  # 只保留最近 100 条
    
    # 保存到文件
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录失败: {e}")

def load_analysis_history():
    """加载分析历史记录"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载历史记录失败: {e}")
    return []

def get_analysis_by_id(history_id: int):
    """根据 ID 获取历史记录"""
    history = load_analysis_history()
    for record in history:
        if record.get('id') == history_id:
            return record
    return None

# --- 3. 定义 Agent 节点 ---

def linguist_node(state: AgentState):
    """
    节点 1: 提取生词和分析语法
    调用 LLM 并注入 prompts/linguist.md
    """
    print("--- [Linguist] 正在分析文本生词与语法... ---")
    
    try:
        # 创建 LLM 实例
        llm = create_llm()
        if llm is None:
            print("⚠️ 警告: 未配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY，请在 .env 文件中设置")
            return {"analysis_result": {"vocabulary": [], "grammar_points": []}}
        
        # 1. 加载提示词模板
        with open("prompts/linguist.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 2. 注入动态上下文（已知单词）
        known_words_str = ", ".join(state['known_words']) if state['known_words'] else "无"
        user_content = f"待分析文本：{state['input_text']}\n\n注意：以下单词用户已掌握，请在词汇表中剔除：{known_words_str}"
        
        # 3. 发起请求
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ])
        
        # 4. 解析结果 (由于 Prompt 要求 JSON 格式)
        try:
            # 兼容处理 LLM 可能返回的 Markdown 标签
            clean_content = response.content.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(clean_content)
        except Exception as e:
            print(f"解析失败: {e}")
            print(f"原始响应: {response.content}")
            analysis = {"vocabulary": [], "grammar_points": []}
        
        return {"analysis_result": analysis}
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        # 返回空结果作为降级处理
        return {"analysis_result": {"vocabulary": [], "grammar_points": []}}

def summarizer_node(state: AgentState):
    """
    节点 2: 提取大意和文本细读
    """
    print("--- [Summarizer] 正在生成文本大意和细读... ---")
    
    try:
        # 创建 LLM 实例
        llm = create_llm()
        if llm is None:
            print("⚠️ 警告: 未配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY，请在 .env 文件中设置")
            return {
                "summary_result": "请配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 后重试",
                "detailed_reading": "请配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 后重试"
            }
        
        # 1. 加载提示词模板
        with open("prompts/summarizer.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 2. 构建用户输入
        user_content = f"请分析以下文本：\n\n{state['input_text']}"
        
        # 3. 发起请求
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ])
        
        # 4. 解析结果
        try:
            # 兼容处理 LLM 可能返回的 Markdown 标签
            clean_content = response.content.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_content)
            summary = result.get("summary", "")
            detailed_reading = result.get("detailed_reading", "")
        except Exception as e:
            print(f"解析失败: {e}")
            print(f"原始响应: {response.content}")
            # 如果解析失败，尝试直接使用响应内容
            summary = response.content
            detailed_reading = response.content
        
        return {
            "summary_result": summary,
            "detailed_reading": detailed_reading
        }
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        # 返回降级结果
        return {
            "summary_result": "无法生成摘要，请检查 API 配置。",
            "detailed_reading": "无法生成细读，请检查 API 配置。"
        }

def memory_updater_node(state: AgentState):
    """
    节点 3: 记忆更新（核心算法逻辑）
    将本次提取的生词写入或更新到 user_words.csv（状态为 learning）
    """
    print("--- [Memory] 正在更新用户词库频率... ---")
    
    # 获取本次分析的生词
    vocabulary = state.get('analysis_result', {}).get('vocabulary', [])
    new_words = []
    
    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)
    
    try:
        # 尝试读取现有数据
        df = pd.read_csv("data/user_words.csv")
    except FileNotFoundError:
        # 如果文件不存在，创建新的 DataFrame
        df = pd.DataFrame(columns=['word', 'level', 'last_queried', 'score', 'status'])
    
    # 处理每个生词
    for word_info in vocabulary:
        if isinstance(word_info, dict):
            word = word_info.get('word', '')
            if word:
                # 检查单词是否已存在
                if word not in df['word'].values:
                    # 新单词，添加到词库（状态为 learning）
                    import datetime
                    new_row = {
                        'word': word,
                        'level': 'N/A',
                        'last_queried': datetime.date.today().strftime('%Y-%m-%d'),
                        'score': 0,  # 初始分数为 0
                        'status': 'learning'  # 初始状态为学习中
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    new_words.append(word)
                else:
                    # 单词已存在，更新查询时间
                    import datetime
                    df.loc[df['word'] == word, 'last_queried'] = datetime.date.today().strftime('%Y-%m-%d')
    
    # 保存到 CSV
    if not df.empty:
        df.to_csv("data/user_words.csv", index=False)
    
    return {"mastered_new_words": new_words}

# --- 4. 构建图逻辑 ---

workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("linguist_agent", linguist_node)
workflow.add_node("summarizer_agent", summarizer_node)
workflow.add_node("memory_manager", memory_updater_node)

# 设置逻辑连线
workflow.set_entry_point("linguist_agent")
workflow.add_edge("linguist_agent", "summarizer_agent")
workflow.add_edge("summarizer_agent", "memory_manager")
workflow.add_edge("memory_manager", END)

# 编译
app = workflow.compile()

# --- 5. 启动程序 ---
if __name__ == "__main__":
    test_text = "The cognitive paradigm shift in AI is inevitable."
    
    # 初始状态加载记忆
    initial_input = {
        "input_text": test_text,
        "known_words": get_known_words_from_csv()
    }
    
    # 执行
    results = app.invoke(initial_input)
    
    print("\n" + "="*30)
    print("分析完成！")
    print(f"大意: {results['summary_result']}")
    print(f"建议学习生词: {results['analysis_result']['vocabulary']}")
    print("="*30)