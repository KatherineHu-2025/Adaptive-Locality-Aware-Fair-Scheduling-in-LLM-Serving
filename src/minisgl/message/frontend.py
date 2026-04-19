from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .utils import deserialize_type, serialize_type


@dataclass
class BaseFrontendMsg:
    @staticmethod
    def encoder(msg: "BaseFrontendMsg") -> Dict:
        return serialize_type(msg)

    @staticmethod
    def decoder(json: Dict) -> "BaseFrontendMsg":
        return deserialize_type(globals(), json)


@dataclass
class BatchFrontendMsg(BaseFrontendMsg):
    data: List[BaseFrontendMsg]


@dataclass
class UserReply(BaseFrontendMsg):
    uid: int
    incremental_output: str
    finished: bool
    # Scheduler metadata for workload instrumentation.
    cached_len: int = -1
    q_at_scheduling: float = -1.0
    jain_control: float = -1.0
    jain_prompt: float = -1.0
    p99_ttft_ms: float = -1.0
    aimd_violated: bool = False
    aimd_violation_reason: str = "none"
    aimd_step: int = -1
