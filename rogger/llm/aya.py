from langchain_core.language_models.llms import LLM
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from torch import cuda, bfloat16
from langchain_core.language_models.llms import LLM
from typing import Any, Dict, Iterator, List, Mapping, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
import transformers

bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16,
)
aya_checkpoint = "CohereForAI/aya-101"
aya_tokenizer = AutoTokenizer.from_pretrained(aya_checkpoint)
aya_model = AutoModelForSeq2SeqLM.from_pretrained(
        aya_checkpoint, quantization_config=bnb_config
    )


class Aya101LLM(LLM):
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        global aya_model
        global aya_tokenizer

        inputs = aya_tokenizer.encode(prompt, return_tensors="pt").to("cuda")
        outputs = aya_model.generate(inputs, max_new_tokens=1024)
        resp_content = aya_tokenizer.decode(outputs[0], skip_special_tokens=True)
        return resp_content

    @property
    def _llm_type(self) -> str:
        return "aya101"
