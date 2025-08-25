import guidance

from typing import List, Dict


class BaseAgent:
    def __init__(self, llm):
        """
        Args:
            llm:  The language model object.
        """
        self.llm = llm
    
    def form_chat_template(self, system_prompt: str, messages: list[dict]):
        """
        Form chat template
        Args:
            system_prompt: The system prompt.
        """
        with guidance.system():
            gen_lm = self.llm + system_prompt
        
        for message in messages[:-1]:
            with eval(f"guidance.{message['role']}()"):
                gen_lm += message["content"]
        
        # For the last message, add the role start and content
        gen_lm += self.llm.chat_template.get_role_start("assistant")
        gen_lm += messages[-1]["content"]

        return gen_lm
        
    def stream_chat(self, **kwargs):
        """
        Stream chat with the user
        """
        raise NotImplementedError