import abc
import copy

from lagent.llms import HFTransformer
from lagent.schema import ModelStatusCode
from typing import Dict, List, Optional, Union


class BaseLLM(HFTransformer):
    """
    Base class for the LLM backbone.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _load_model(self, path: str, model_kwargs: dict):
        import torch
        from transformers import AutoModelForCausalLM
        model_kwargs.setdefault('torch_dtype', torch.float16)
        self.model = AutoModelForCausalLM.from_pretrained(
            path, trust_remote_code=True, **model_kwargs)
        self.model.eval()
    
    def chat(self,
             prompt: str,
             do_sample: bool = True,
             **kwargs,
             ):
        """
        Return the chat results at once.

        Args:
            prompt (str): The prompt to be completed.
            do_sample (bool): Do sampling if enabled
        Returns:
            The final response
        """
        return self.generate(prompt, do_sample, **kwargs)
    
    def stream_chat(
        self,
        prompt: str,
        do_sample: bool = True,
        **kwargs,
    ):
        """
        Return the chat completions in stream mode.

        Args:
            prompt (str): The prompt to be completed.
            do_sample (bool): do sampling if enabled
        Returns:
            the text/chat completion
        """
        yield from self.stream_generate(prompt, do_sample, **kwargs)
    
    @abc.abstractmethod
    def apply_chat_template(self, messages: List[Dict], add_generation_prompt=True) -> str:
        """
        Apply chat template to raw messages
        
        Args:
            messages: A list of raw messages.

        Returns:
            prompt: Complete prompt for LLM.
        """
        raise NotImplementedError

    def stream_generate(
        self,
        inputs: List[str],
        do_sample: bool = True,
        **kwargs,
    ):
        """Return the chat completions in stream mode.

        Args:
            inputs (Union[str, List[str]]): input texts to be completed.
            do_sample (bool): do sampling if enabled
        Returns:
            tuple(Status, str, int): status, text/chat completion,
            generated token number
        """
        import torch
        from torch import nn
        with torch.no_grad():
            batched = True
            if isinstance(inputs, str):
                inputs = [inputs]
                batched = False
            inputs = self.tokenizer(
                inputs, padding=True, return_tensors='pt', return_length=True)
            input_length = inputs['length']
            for k, v in inputs.items():
                inputs[k] = v.cuda()
            input_ids = inputs['input_ids']
            attention_mask = inputs['attention_mask']
            batch_size = input_ids.shape[0]
            input_ids_seq_length = input_ids.shape[-1]
            generation_config = self.model.generation_config
            generation_config = copy.deepcopy(generation_config)
            new_gen_params = self.update_gen_params(**kwargs)
            generation_config.update(**new_gen_params)
            generation_config.update(**kwargs)
            model_kwargs = generation_config.to_dict()
            model_kwargs['attention_mask'] = attention_mask
            _, eos_token_id = (  # noqa: F841  # pylint: disable=W0612
                generation_config.bos_token_id,
                generation_config.eos_token_id,
            )
            if eos_token_id is None:
                if self.gcfg.eos_token_id is not None:
                    eos_token_id = self.gcfg.eos_token_id
                else:
                    eos_token_id = []
            if isinstance(eos_token_id, int):
                eos_token_id = [eos_token_id]
            if self.additional_eos_token_id is not None:
                eos_token_id.extend(self.additional_eos_token_id)
            eos_token_id_tensor = torch.tensor(eos_token_id).to(
                input_ids.device) if eos_token_id is not None else None
            generation_config.max_length = (
                generation_config.max_new_tokens + input_ids_seq_length)
            # Set generation parameters if not already defined
            logits_processor = self.logits_processor
            stopping_criteria = self.stopping_criteria

            logits_processor = self.model._get_logits_processor(
                generation_config=generation_config,
                input_ids_seq_length=input_ids_seq_length,
                encoder_input_ids=input_ids,
                prefix_allowed_tokens_fn=self.prefix_allowed_tokens_fn,
                logits_processor=logits_processor,
            )

            stopping_criteria = self.model._get_stopping_criteria(
                generation_config=generation_config,
                stopping_criteria=stopping_criteria)
            logits_warper = self.model._get_logits_warper(generation_config)

            unfinished_sequences = input_ids.new(batch_size).fill_(1)
            scores = None
            while True:
                model_inputs = self.model.prepare_inputs_for_generation(
                    input_ids, **model_kwargs)
                # forward pass to get next token
                outputs = self.model(
                    **model_inputs,
                    return_dict=True,
                    output_attentions=False,
                    output_hidden_states=False,
                )

                next_token_logits = outputs.logits[:, -1, :]

                # pre-process distribution
                next_token_scores = logits_processor(input_ids,
                                                     next_token_logits)
                next_token_scores = logits_warper(input_ids, next_token_scores)

                # sample
                probs = nn.functional.softmax(next_token_scores, dim=-1)
                if do_sample:
                    next_tokens = torch.multinomial(
                        probs, num_samples=1).squeeze(1)
                else:
                    next_tokens = torch.argmax(probs, dim=-1)

                # update generated ids, model inputs,
                # and length for next step
                input_ids = torch.cat([input_ids, next_tokens[:, None]],
                                      dim=-1)
                model_kwargs = self.model._update_model_kwargs_for_generation(  # noqa: E501
                    outputs,
                    model_kwargs,
                    is_encoder_decoder=False)
                unfinished_sequences = unfinished_sequences.mul(
                    next_tokens.tile(eos_token_id_tensor.shape[0], 1).ne(
                        eos_token_id_tensor.unsqueeze(1)).prod(dim=0))
                output_token_ids = input_ids.cpu().tolist()
                for i in range(len(output_token_ids)):
                    output_token_ids[i] = output_token_ids[i][:][
                        input_length[i]:]
                    # Find the first occurrence of
                    # an EOS token in the sequence
                    first_eos_idx = next(
                        (idx
                         for idx, token_id in enumerate(output_token_ids[i])
                         if token_id in eos_token_id), None)
                    # If an EOS token is found, only the previous
                    # part of it is retained
                    if first_eos_idx is not None:
                        output_token_ids[i] = output_token_ids[
                            i][:first_eos_idx]

                response = self.tokenizer.batch_decode(output_token_ids)
                # print(response)
                if not batched:
                    response = response[0]
                yield ModelStatusCode.STREAM_ING, response, None
                # stop when each sentence is finished,
                # or if we exceed the maximum length
                if (unfinished_sequences.max() == 0
                        or stopping_criteria(input_ids, scores)):
                    break
            yield ModelStatusCode.END, response, None
    