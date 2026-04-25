"""
Modified minisgl/message/backend.py
Changes:
  - added `client_id: str` to UserMsg
  - added ResetBackendMsg so tokenizer/control messages can reset scheduler
    experiment state without restarting the service
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import torch
from minisgl.core import SamplingParams

from .utils import deserialize_type, serialize_type


@dataclass
class BaseBackendMsg:
    def encoder(self) -> Dict:
        return serialize_type(self)

    @staticmethod
    def decoder(json: Dict) -> BaseBackendMsg:
        return deserialize_type(globals(), json)


@dataclass
class BatchBackendMsg(BaseBackendMsg):
    data: List[BaseBackendMsg]


@dataclass
class ExitMsg(BaseBackendMsg):
    pass


@dataclass
class UserMsg(BaseBackendMsg):
    uid: int
    input_ids: torch.Tensor  # CPU 1D int32 tensor
    sampling_params: SamplingParams
    # --- added for DLPM / telemetry ---
    # Populated by api_server.py from the HTTP "client_id" field (defaults to
    # str(uid) so existing callers that don't set it still get a unique ID).
    client_id: str = ""
    # Frontend/API receive timestamp from time.perf_counter().
    # If unset, scheduler falls back to its own receive time.
    arrival_time: float = 0.0


@dataclass
class AbortBackendMsg(BaseBackendMsg):
    uid: int


@dataclass
class ResetBackendMsg(BaseBackendMsg):
    scope: str = "experiment"
