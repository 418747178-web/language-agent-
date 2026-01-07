import datetime

class MemoryManager:
    def __init__(self):
        # 实际项目中应连接数据库，此处用 dict 模拟
        self.user_memory = {
            "apple": {"score": 5, "status": "mastered"},
            "paradigm": {"score": 0, "status": "learning"}
        }

    def update_on_query(self, word: str):
        """当用户点击查询或 Agent 归纳生词时调用"""
        if word not in self.user_memory:
            self.user_memory[word] = {"score": -1, "status": "learning", "last_seen": datetime.datetime.now()}
        else:
            # 再次查询，分数降低
            self.user_memory[word]["score"] -= 1
            self.user_memory[word]["status"] = "learning"
        
    def update_on_passive_seen(self, word: str):
        """
        核心算法：当文本中出现该词，但用户没有查询它。
        我们假设用户可能已经记住了。
        """
        if word in self.user_memory:
            self.user_memory[word]["score"] += 1
            # 阈值判断：如果连续 3 次看到没查，且分数 > 2，设为掌握
            if self.user_memory[word]["score"] >= 3:
                self.user_memory[word]["status"] = "mastered"

    def get_known_words(self) -> list:
        """获取所有已掌握的词汇列表"""
        return [w for w, data in self.user_memory.items() if data["status"] == "mastered"]

# --- 集成到 Agent 状态中 ---

def memory_bridge_node(state: AgentState):
    """
    这是一个中间件 Node，专门负责在 Linguist Agent 运行前，
    从 Memory 中提取该用户的“熟知词库”。
    """
    mem = MemoryManager() # 实际应从数据库加载
    known = mem.get_known_words()
    return {"known_words": known}