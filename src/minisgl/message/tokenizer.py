"""
Modified minisgl/message/tokenizer.py
Changes: added `client_id: str` to TokenizeMsg so it survives the
API server → tokenizer → scheduler pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from minisgl.core import SamplingParams

from .utils import deserialize_type, serialize_type


@dataclass
class BaseTokenizerMsg:
    @staticmethod
    def encoder(msg: BaseTokenizerMsg) -> Dict:
        return serialize_type(msg)

    @staticmethod
    def decoder(json: Dict) -> BaseTokenizerMsg:
        return deserialize_type(globals(), json)


@dataclass
class BatchTokenizerMsg(BaseTokenizerMsg):
    data: List[BaseTokenizerMsg]


@dataclass
class DetokenizeMsg(BaseTokenizerMsg):
    uid: int
    next_token: int
    finished: bool


@dataclass
class TokenizeMsg(BaseTokenizerMsg):
    uid: int
    text: str | List[Dict[str, str]]
    sampling_params: SamplingParams
    # --- added for DLPM / telemetry ---
    # Set by api_server.py from the HTTP "client_id" field.
    # Defaults to "" so existing callers work without changes.
    client_id: str = ""


@dataclass
class AbortMsg(BaseTokenizerMsg):
    uid: int
