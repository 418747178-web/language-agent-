import streamlit as st
from main import (
    app, 
    get_known_words_from_csv,
    save_analysis_history,
    load_analysis_history,
    get_analysis_by_id,
    mark_word_as_mastered,
    get_all_words_from_csv
)  # 导入 app 和记忆加载函数
# 初始化 Session State 用于保存当前会话的历史记录
if 'session_history' not in st.session_state:
    st.session_state.session_history = []

st.set_page_config(page_title="LingoContext AI", layout="wide")
st.set_page_config(page_title="LingoContext AI", layout="wide")

# 添加朗读功能的 JavaScript 代码（使用 components.html 确保在所有页面可用）
import streamlit.components.v1 as components

# 定义朗读函数 - 使用更可靠的方式
speak_js = """
<script>
(function() {
    // 确保函数在全局作用域可用
    window.speakWord = function(word, lang='en-US') {
        console.log('尝试朗读:', word, '语言:', lang);
        if ('speechSynthesis' in window) {
            // 停止当前正在播放的语音
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(word);
            utterance.lang = lang;
            utterance.rate = 0.8; // 语速稍慢，便于学习
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            utterance.onerror = function(event) {
                console.error('语音合成错误:', event);
                alert('朗读失败，请检查浏览器设置');
            };
            
            utterance.onstart = function() {
                console.log('开始朗读:', word);
            };
            
            window.speechSynthesis.speak(utterance);
        } else {
            alert('您的浏览器不支持语音合成功能，请使用 Chrome、Edge 或 Safari 浏览器');
        }
    };
    
    console.log('朗读函数已加载');
})();
</script>
"""

# 在页面加载时注入 JavaScript
components.html(speak_js, height=0)

# --- 语言检测函数 ---
def detect_language(word):
    """
    检测单词的语言类型
    返回语言代码：'en-US', 'zh-CN', 'fr-FR', 'de-DE', 'ja-JP', 'ru-RU', 'es-ES', 'it-IT'
    """
    if not word:
        return 'en-US'
    
    word_lower = word.lower()
    
    # 检测日语字符（优先级最高，因为可能包含汉字）
    # 平假名：\u3040-\u309F
    # 片假名：\u30A0-\u30FF
    # 日文汉字：\u4E00-\u9FAF（与中文重叠，但日语通常伴随假名）
    has_hiragana = any('\u3040' <= char <= '\u309F' for char in word)
    has_katakana = any('\u30A0' <= char <= '\u30FF' for char in word)
    if has_hiragana or has_katakana:
        return 'ja-JP'
    
    # 检测俄语字符（西里尔字母）
    # 俄语字母范围：\u0400-\u04FF
    if any('\u0400' <= char <= '\u04FF' for char in word):
        return 'ru-RU'
    
    # 检测中文字符（在日语检测之后，避免误判）
    if any('\u4e00' <= char <= '\u9fff' for char in word):
        return 'zh-CN'
    
    # 检测法语特征字符：é, è, ê, à, ç, ù, û, ô, î, ï, ë, ü
    french_chars = ['é', 'è', 'ê', 'à', 'ç', 'ù', 'û', 'ô', 'î', 'ï', 'ë', 'ü', 'œ', 'æ']
    if any(char in word_lower for char in french_chars):
        return 'fr-FR'
    
    # 检测德语特征字符：ä, ö, ü, ß
    german_chars = ['ä', 'ö', 'ü', 'ß']
    if any(char in word_lower for char in german_chars):
        return 'de-DE'
    
    # 检测西班牙语特征字符：ñ, á, é, í, ó, ú, ü
    spanish_chars = ['ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü']
    if any(char in word_lower for char in spanish_chars):
        return 'es-ES'
    
    # 检测意大利语特征字符：à, è, é, ì, ò, ù
    italian_chars = ['à', 'è', 'é', 'ì', 'ò', 'ù']
    if any(char in word_lower for char in italian_chars):
        return 'it-IT'
    
    # 默认返回英文
    return 'en-US'

st.title("🚀 LingoContext: 你的 AI 语言助教")
st.markdown("输入一段外语，AI 将为你归纳大意、提取生词、分析语法并提供文本细读。")

col1, col2 = st.columns([1, 1])

with col1:
    user_input = st.text_area("粘贴你想学习的文本:", height=300)
    if st.button("开始分析", type="primary"):
        if user_input:
            with st.spinner("Agent 正在深度思考中..."):
                # 运行 LangGraph
                # 加载已掌握单词
                known_words = get_known_words_from_csv()
                initial_state = {"input_text": user_input, "known_words": known_words} 
                result = app.invoke(initial_state)
                st.session_state['result'] = result
                st.session_state['current_input'] = user_input
                # 保存到历史记录
                                # 保存到历史记录
                save_analysis_history(user_input, result)
                
                # 同时保存到 Session State（当前会话）
                import datetime
                session_record = {
                    "id": len(st.session_state.session_history) + 1,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "input_text": user_input,
                    "result": result
                }
                st.session_state.session_history.append(session_record)
                
                st.success("分析完成！已保存到历史记录。")
                st.success("分析完成！已保存到历史记录。")
        else:
            st.warning("请输入内容")

with col2:
    if 'result' in st.session_state:
        res = st.session_state['result']
        
        # 显示当前查看的是历史记录还是新分析
        if st.session_state.get('viewing_history'):
            st.info("📜 正在查看历史记录")
            if st.button("返回新分析"):
                st.session_state.pop('viewing_history', None)
                st.session_state.pop('result', None)
                st.session_state.pop('current_input', None)
                st.rerun()
        
        # 显示原始文本（如果是历史记录）
        if 'current_input' in st.session_state:
            with st.expander("📄 原始文本", expanded=False):
                st.text_area("", st.session_state['current_input'], height=100, disabled=True, key="original_text_display")
        
        # 文本大意
        st.subheader("📝 文本大意")
        if res.get('summary_result'):
            st.info(res['summary_result'])
        else:
            st.info("暂无摘要")
        
        # 文本细读
        st.subheader("📖 文本细读")
        if res.get('detailed_reading'):
            with st.expander("点击展开详细分析", expanded=True):
                st.markdown(res['detailed_reading'])
        else:
            st.info("暂无细读内容")

# 在主内容区域下方显示生词和语法
if 'result' in st.session_state:
    res = st.session_state['result']
    
    st.divider()
    
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.subheader("📚 建议生词")
        vocabulary = res['analysis_result'].get('vocabulary', [])
        
        # 获取已掌握的单词列表
        known_words = get_known_words_from_csv()
        
        if vocabulary:
            for idx, word_info in enumerate(vocabulary):
                # 处理两种情况：字符串列表或字典列表
                if isinstance(word_info, str):
                    word = word_info
                    phonetic = ""
                    definition = ""
                    example = ""
                elif isinstance(word_info, dict):
                    word = word_info.get('word', '')
                    phonetic = word_info.get('phonetic', '')
                    definition = word_info.get('definition', '暂无释义')
                    example = word_info.get('example', '暂无例句')
                else:
                    continue
                
                # 检查是否已掌握
                is_mastered = word.lower() in [w.lower() for w in known_words]
                
                # 创建三列布局：单词信息、朗读按钮、掌握按钮
                word_col, audio_col, btn_col = st.columns([3, 1, 1])
                
                with word_col:
                    # 标题显示单词和音标
                    expander_title = f"**{word}**"
                    if phonetic:
                        expander_title += f" [{phonetic}]"
                    if is_mastered:
                        expander_title += " ✅"
                    
                    with st.expander(expander_title, expanded=False):
                        if isinstance(word_info, dict):
                            st.markdown(f"**中文释义：** {definition}")
                            if example and example != '暂无例句':
                                st.markdown(f"**例句：** {example}")
                        else:
                            st.info(f"单词: {word}")
                
                with audio_col:
                    # 朗读按钮 - 使用计数器确保每次点击都能朗读
                    # 使用智能语言检测
                    lang = detect_language(word)
                    
                    # 初始化计数器
                    counter_key = f"speak_counter_{word}_{idx}"
                    if counter_key not in st.session_state:
                        st.session_state[counter_key] = 0
                    
                    # 使用 Streamlit 按钮
                    speak_key = f"speak_{word}_{idx}"
                    if st.button("🔊", key=speak_key, use_container_width=True, help="点击朗读"):
                        # 增加计数器，确保每次点击都触发新的朗读
                        st.session_state[counter_key] = st.session_state[counter_key] + 1
                        st.rerun()
                    
                    # 如果计数器大于0，执行朗读
                    if st.session_state.get(counter_key, 0) > 0:
                        # 执行朗读的 JavaScript（使用计数器确保每次都是新的执行）
                        counter = st.session_state[counter_key]
                        speak_script = f"""
                        <script>
                        (function() {{
                            if ('speechSynthesis' in window) {{
                                window.speechSynthesis.cancel();
                                const utterance = new SpeechSynthesisUtterance('{word.replace("'", "\\'")}');
                                utterance.lang = '{lang}';
                                utterance.rate = 0.8;
                                utterance.pitch = 1.0;
                                utterance.volume = 1.0;
                                window.speechSynthesis.speak(utterance);
                            }}
                        }})();
                        </script>
                        """
                        components.html(speak_script, height=0)
                
                with btn_col:
                    if not is_mastered:
                        # 标记为已掌握按钮
                        if st.button("✅ 已掌握", key=f"master_{word}_{idx}", use_container_width=True):
                            mark_word_as_mastered(word)
                            st.success(f"'{word}' 已标记为已掌握！")
                            st.rerun()
                    else:
                        st.success("✅ 已掌握")
        else:
            st.info("未发现生词")
    
    with col4:
        st.subheader("💡 语法难点")
        # 处理 grammar_points 或 grammar
        grammar_data = res['analysis_result'].get('grammar_points') or res['analysis_result'].get('grammar')
        if grammar_data:
            if isinstance(grammar_data, list):
                for idx, g in enumerate(grammar_data):
                    if isinstance(g, dict):
                        point = g.get('point', '语法点')
                        explanation = g.get('explanation', '暂无讲解')
                        with st.expander(f"**{point}**", expanded=False):
                            st.markdown(explanation)
                    else:
                        st.success(str(g))
            elif isinstance(grammar_data, str):
                st.success(grammar_data)
        else:
            st.info("未发现语法难点")

# 侧边栏：历史记录和统计
st.sidebar.title("📚 学习记录")

# 历史记录部分
st.sidebar.subheader("分析历史")
history = load_analysis_history()

if history:
    # 显示历史记录列表（倒序，最新的在前）
    history_reversed = list(reversed(history))
    
    # 辅助函数：提取文本前三个词作为标题
    def get_title_from_text(text):
        """从文本中提取前三个词作为标题"""
        if not text or not text.strip():
            return "无标题"
        
        # 去除首尾空格和换行符
        text = text.strip().replace('\n', ' ').replace('\r', ' ')
        
        # 对于英文：按空格分割
        # 对于中文：每个字符作为一个词
        # 先尝试按空格分割（英文）
        words = text.split()
        
        if len(words) >= 3:
            # 英文文本，取前三个词
            title = " ".join(words[:3])
        elif len(words) > 0:
            # 英文文本，但少于三个词
            title = " ".join(words)
        else:
            # 可能是中文或其他语言，按字符取前15个字符
            title = text[:15] if len(text) >= 15 else text
        
        # 如果标题太长，截断
        if len(title) > 50:
            title = title[:50] + "..."
        
        return title
    
    # 显示当前分析（如果有）
    if 'result' in st.session_state:
        st.sidebar.markdown("**📌 当前分析**")
        if st.sidebar.button("查看当前分析", key="view_current", use_container_width=True):
            st.session_state.pop('viewing_history', None)
            st.rerun()
        st.sidebar.divider()
    
    # 显示历史记录标题列表
    st.sidebar.markdown("**历史记录列表：**")
    
    # 为每条记录创建可点击的标题
    for idx, record in enumerate(history_reversed):
        title = get_title_from_text(record['input_text'])
        timestamp = record['timestamp']
        
        # 创建可点击的按钮样式标题
        if st.sidebar.button(
            f"📄 {title}\n*{timestamp}*",
            key=f"history_btn_{record['id']}",
            use_container_width=True
        ):
            st.session_state['result'] = record['result']
            st.session_state['current_input'] = record['input_text']
            st.session_state['viewing_history'] = True
            st.session_state['selected_history_id'] = record['id']
            st.rerun()
        
        # 添加分隔线（最后一条不添加）
        if idx < len(history_reversed) - 1:
            st.sidebar.markdown("---")
    
        # 显示历史记录数量
    st.sidebar.info(f"共保存 {len(history)} 条记录")
    
    # 导出和导入历史记录
    st.sidebar.divider()
    st.sidebar.subheader("📥 数据管理")
    
    # 导出历史记录
    if st.sidebar.button("📥 导出历史记录", use_container_width=True):
        import datetime
        import json
        
        # 准备导出的数据
        export_data = {
            "export_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_records": len(history),
            "history": history
        }
        
        # 创建下载按钮
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.sidebar.download_button(
            label="⬇️ 下载 JSON 文件",
            data=json_str,
            file_name=f"lingocontext_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # 导入历史记录
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader(
        "📤 导入历史记录",
        type=['json'],
        help="选择之前导出的 JSON 文件来恢复历史记录"
    )
    
    if uploaded_file is not None:
        try:
            import json
            # 读取上传的文件
            content = uploaded_file.read().decode('utf-8')
            import_data = json.loads(content)
            
            # 检查数据格式
            if 'history' in import_data and isinstance(import_data['history'], list):
                # 合并历史记录
                existing_history = load_analysis_history()
                existing_ids = {r.get('id') for r in existing_history}
                
                # 添加新记录（避免重复）
                new_records = []
                for record in import_data['history']:
                    # 如果 ID 不存在，添加记录
                    if record.get('id') not in existing_ids:
                        new_records.append(record)
                
                if new_records:
                    # 合并并保存
                    merged_history = existing_history + new_records
                    # 按时间戳排序
                    merged_history.sort(key=lambda x: x.get('timestamp', ''))
                    # 只保留最近 100 条
                    if len(merged_history) > 100:
                        merged_history = merged_history[-100:]
                    
                    # 保存到文件
                    import os
                    os.makedirs("data", exist_ok=True)
                    with open("data/analysis_history.json", 'w', encoding='utf-8') as f:
                        json.dump(merged_history, f, ensure_ascii=False, indent=2)
                    
                    st.sidebar.success(f"✅ 成功导入 {len(new_records)} 条记录！")
                    st.rerun()
                else:
                    st.sidebar.info("ℹ️ 没有新记录需要导入（可能已存在）")
            else:
                st.sidebar.error("❌ 文件格式不正确，请确保是导出的历史记录文件")
        except Exception as e:
            st.sidebar.error(f"❌ 导入失败: {str(e)}")
    
    # 清空历史记录按钮
    st.sidebar.divider()
    if st.sidebar.button("🗑️ 清空历史记录", type="secondary"):
        import os
        import json
        history_file = "data/analysis_history.json"
        if os.path.exists(history_file):
            os.remove(history_file)
            st.sidebar.success("历史记录已清空")
            st.rerun()
else:
    st.sidebar.info("暂无历史记录")
    
    # 即使没有历史记录，也显示导入功能
    st.sidebar.divider()
    st.sidebar.subheader("📥 数据管理")
    uploaded_file = st.sidebar.file_uploader(
        "📤 导入历史记录",
        type=['json'],
        help="选择之前导出的 JSON 文件来恢复历史记录"
    )
    
    if uploaded_file is not None:
        try:
            import json
            import os
            content = uploaded_file.read().decode('utf-8')
            import_data = json.loads(content)
            
            if 'history' in import_data and isinstance(import_data['history'], list):
                # 确保 data 目录存在
                os.makedirs("data", exist_ok=True)
                
                # 保存导入的历史记录
                with open("data/analysis_history.json", 'w', encoding='utf-8') as f:
                    json.dump(import_data['history'], f, ensure_ascii=False, indent=2)
                
                st.sidebar.success(f"✅ 成功导入 {len(import_data['history'])} 条记录！")
                st.rerun()
            else:
                st.sidebar.error("❌ 文件格式不正确")
        except Exception as e:
            st.sidebar.error(f"❌ 导入失败: {str(e)}")
st.sidebar.divider()

# 生词管理
st.sidebar.subheader("📖 生词管理")
if st.sidebar.button("查看所有生词", use_container_width=True):
    st.session_state['show_word_manager'] = True

# 学习统计
st.sidebar.subheader("学习统计")
try:
    import pandas as pd
    df = pd.read_csv("data/user_words.csv")
    mastered_count = len(df[df['status'] == 'mastered'])
    learning_count = len(df[df['status'] == 'learning'])
    total_count = len(df)
    st.sidebar.metric("已掌握单词量", mastered_count)
    st.sidebar.metric("学习中单词", learning_count)
    st.sidebar.metric("总单词数", total_count)
except:
    st.sidebar.metric("已掌握单词量", "0")
    st.sidebar.metric("学习中单词", "0")
    st.sidebar.metric("总单词数", "0")

# 生词管理页面
if st.session_state.get('show_word_manager', False):
    st.divider()
    st.subheader("📖 生词管理")
    
    if st.button("❌ 关闭生词管理"):
        st.session_state['show_word_manager'] = False
        st.rerun()
    
    try:
        all_words = get_all_words_from_csv()
        
        if all_words:
            # 创建标签页：全部、已掌握、学习中
            tab1, tab2, tab3 = st.tabs(["全部", "✅ 已掌握", "📚 学习中"])
            
            with tab1:
                st.write(f"**共 {len(all_words)} 个单词**")
                for word_data in all_words:
                    word = word_data.get('word', '')
                    status = word_data.get('status', 'learning')
                    score = word_data.get('score', 0)
                    last_queried = word_data.get('last_queried', 'N/A')
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        status_icon = "✅" if status == 'mastered' else "📚"
                        st.write(f"{status_icon} **{word}** (分数: {score}, 最后查询: {last_queried})")
                    with col2:
                        # 朗读按钮 - 使用计数器确保每次点击都能朗读
                        lang = detect_language(word)
                        
                        # 初始化计数器
                        counter_key = f"manage_speak_counter_{word}"
                        if counter_key not in st.session_state:
                            st.session_state[counter_key] = 0
                        
                        speak_key = f"manage_speak_{word}"
                        if st.button("🔊", key=speak_key, use_container_width=True, help="点击朗读"):
                            # 增加计数器，确保每次点击都触发新的朗读
                            st.session_state[counter_key] = st.session_state[counter_key] + 1
                            st.rerun()
                        
                        # 如果计数器大于0，执行朗读
                        if st.session_state.get(counter_key, 0) > 0:
                            counter = st.session_state[counter_key]
                            speak_script = f"""
                            <script>
                            (function() {{
                                if ('speechSynthesis' in window) {{
                                    window.speechSynthesis.cancel();
                                    const utterance = new SpeechSynthesisUtterance('{word.replace("'", "\\'")}');
                                    utterance.lang = '{lang}';
                                    utterance.rate = 0.8;
                                    utterance.pitch = 1.0;
                                    utterance.volume = 1.0;
                                    window.speechSynthesis.speak(utterance);
                                }}
                            }})();
                            </script>
                            """
                            components.html(speak_script, height=0)
                    with col3:
                        if status != 'mastered':
                            if st.button("✅ 已掌握", key=f"manage_master_{word}"):
                                mark_word_as_mastered(word)
                                st.success(f"'{word}' 已标记为已掌握！")
                                st.rerun()
                    with col4:
                        if status == 'mastered':
                            if st.button("📚 重新学习", key=f"manage_learn_{word}"):
                                # 将状态改回 learning
                                import pandas as pd
                                df = pd.read_csv("data/user_words.csv")
                                df.loc[df['word'] == word, 'status'] = 'learning'
                                df.loc[df['word'] == word, 'score'] = 0
                                df.to_csv("data/user_words.csv", index=False)
                                st.success(f"'{word}' 已标记为重新学习")
                                st.rerun()
            
            with tab2:
                mastered_words = [w for w in all_words if w.get('status') == 'mastered']
                st.write(f"**已掌握 {len(mastered_words)} 个单词**")
                for word_data in mastered_words:
                    word = word_data.get('word', '')
                    score = word_data.get('score', 0)
                    last_queried = word_data.get('last_queried', 'N/A')
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"✅ **{word}** (分数: {score}, 最后查询: {last_queried})")
                    with col2:
                        # 朗读按钮 - 使用计数器确保每次点击都能朗读
                        lang = detect_language(word)
                        
                        # 初始化计数器
                        counter_key = f"tab2_speak_counter_{word}"
                        if counter_key not in st.session_state:
                            st.session_state[counter_key] = 0
                        
                        speak_key = f"tab2_speak_{word}"
                        if st.button("🔊", key=speak_key, use_container_width=True, help="点击朗读"):
                            # 增加计数器，确保每次点击都触发新的朗读
                            st.session_state[counter_key] = st.session_state[counter_key] + 1
                            st.rerun()
                        
                        # 如果计数器大于0，执行朗读
                        if st.session_state.get(counter_key, 0) > 0:
                            counter = st.session_state[counter_key]
                            speak_script = f"""
                            <script>
                            (function() {{
                                if ('speechSynthesis' in window) {{
                                    window.speechSynthesis.cancel();
                                    const utterance = new SpeechSynthesisUtterance('{word.replace("'", "\\'")}');
                                    utterance.lang = '{lang}';
                                    utterance.rate = 0.8;
                                    utterance.pitch = 1.0;
                                    utterance.volume = 1.0;
                                    window.speechSynthesis.speak(utterance);
                                }}
                            }})();
                            </script>
                            """
                            components.html(speak_script, height=0)
            
            with tab3:
                learning_words = [w for w in all_words if w.get('status') == 'learning']
                st.write(f"**学习中 {len(learning_words)} 个单词**")
                for word_data in learning_words:
                    word = word_data.get('word', '')
                    score = word_data.get('score', 0)
                    last_queried = word_data.get('last_queried', 'N/A')
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"📚 **{word}** (分数: {score}, 最后查询: {last_queried})")
                    with col2:
                        # 朗读按钮 - 使用计数器确保每次点击都能朗读
                        lang = detect_language(word)
                        
                        # 初始化计数器
                        counter_key = f"tab3_speak_counter_{word}"
                        if counter_key not in st.session_state:
                            st.session_state[counter_key] = 0
                        
                        speak_key = f"tab3_speak_{word}"
                        if st.button("🔊", key=speak_key, use_container_width=True, help="点击朗读"):
                            # 增加计数器，确保每次点击都触发新的朗读
                            st.session_state[counter_key] = st.session_state[counter_key] + 1
                            st.rerun()
                        
                        # 如果计数器大于0，执行朗读
                        if st.session_state.get(counter_key, 0) > 0:
                            counter = st.session_state[counter_key]
                            speak_script = f"""
                            <script>
                            (function() {{
                                if ('speechSynthesis' in window) {{
                                    window.speechSynthesis.cancel();
                                    const utterance = new SpeechSynthesisUtterance('{word.replace("'", "\\'")}');
                                    utterance.lang = '{lang}';
                                    utterance.rate = 0.8;
                                    utterance.pitch = 1.0;
                                    utterance.volume = 1.0;
                                    window.speechSynthesis.speak(utterance);
                                }}
                            }})();
                            </script>
                            """
                            components.html(speak_script, height=0)
                    with col3:
                        if st.button("✅ 已掌握", key=f"tab3_master_{word}"):
                            mark_word_as_mastered(word)
                            st.success(f"'{word}' 已标记为已掌握！")
                            st.rerun()
        else:
            st.info("暂无生词记录")
    except Exception as e:
        st.error(f"加载生词数据失败: {e}")