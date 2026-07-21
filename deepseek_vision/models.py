from dataclasses import dataclass
from typing import Optional


@dataclass
class PowChallenge:
    """PoW challenge from DeepSeek API"""
    algorithm: str
    challenge: str
    salt: str
    difficulty: int
    expire_at: int
    signature: str
    target_path: str


@dataclass
class PowSolution:
    """PoW solution to send back"""
    algorithm: str
    challenge: str
    salt: str
    answer: float
    signature: str
    target_path: str

    def to_base64(self) -> str:
        import base64
        import json
        answer = int(self.answer) if self.answer == int(self.answer) else self.answer
        data = {
            "algorithm": self.algorithm,
            "challenge": self.challenge,
            "salt": self.salt,
            "answer": answer,
            "signature": self.signature,
            "target_path": self.target_path,
        }
        return base64.b64encode(json.dumps(data).encode()).decode()


@dataclass
class ChatMessage:
    """Parsed chat message from SSE stream"""
    message_id: int
    parent_id: Optional[int]
    role: str
    content: str
    status: str
    model_type: Optional[str] = None
