from tenacity import (
    retry,
    wait_fixed,
    stop_after_attempt,
    retry_if_exception_type
)
import openai
from openai import APIConnectionError, RateLimitError, BadRequestError
from .config import models
from openai import OpenAI



class OpenAIClient:
    def __init__(self, model_name: str):
        if model_name not in models:
            raise ValueError(f"""Model "{model_name}" is not available.""")
        
        self.client = OpenAI(**models[model_name])
        self.model = model_name
    
    @retry(
        wait=wait_fixed(300),                              # 重试间隔30秒
        stop=stop_after_attempt(5),                          # 最多重试5次
        retry=(
            retry_if_exception_type(APIConnectionError)      # 仅对特定错误重试
            | retry_if_exception_type(RateLimitError)
            | retry_if_exception_type(BadRequestError)
        ),
        before_sleep=lambda _: print("Retrying...")          # 重试前的日志
    )
    def call_openai(self, messages, stream=True, stop=None, temperature=0.001):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            stop=stop,
            temperature=temperature,
        )
        return response