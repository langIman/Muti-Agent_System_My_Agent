class FeedbackCollector:
    """收集用户和系统反馈"""

    def __init__(self):
        self.feedbacks = []

    def collect_user_feedback(self, task: str, rating: int, comment: str = ""):
        self.feedbacks.append({"task": task, "rating": rating, "comment": comment, "source": "user"})

    def collect_system_feedback(self, task: str, success: bool, error: str = ""):
        self.feedbacks.append({"task": task, "success": success, "error": error, "source": "system"})

    def get_recent(self, n: int = 10) -> list:
        return self.feedbacks[-n:]
