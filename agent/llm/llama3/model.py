from ..base_llm import BaseLLM
from ..interface import register_model
from typing import Dict, List


@register_model
class Llama3Model(BaseLLM):
    """
    Llama3 model
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def apply_chat_template(self, messages: List[Dict], add_generation_prompt=True) -> str:
        """
        Apply chat template to raw messages

        Args:
            messages: A list of raw messages.

        Returns:
            prompt: Complete prompt for LLM.
        """
        # system_message = "Your name is Asuna, an impatient woman. You are an AI expert that can answer any questions about protein."
        # all_messages = [{"role": "system", "content": system_message}] + messages
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )

        return prompt
    