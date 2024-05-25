import transformers
from transformers import AutoTokenizer
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from torch import cuda, bfloat16
from langchain_core.language_models.llms import LLM
from typing import Any, Dict, Iterator, List, Mapping, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16,
)
mistral_checkpoint = "mistralai/Mistral-7B-v0.1"
mistral_tokenizer = AutoTokenizer.from_pretrained(mistral_checkpoint)
mistral_model = AutoModelForSeq2SeqLM.from_pretrained(
        mistral_checkpoint, quantization_config=bnb_config
    )


class MistralLLM(LLM):
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        global mistral_model
        global mistral_tokenizer

        inputs = mistral_tokenizer.encode(prompt, return_tensors="pt").to("cuda")
        outputs = mistral_tokenizer.generate(inputs, max_new_tokens=1024)
        resp_content = mistral_tokenizer.decode(outputs[0], skip_special_tokens=True)
        return resp_content

    @property
    def _llm_type(self) -> str:
        return "aya101"
    

# embeddings = E5Embeddings()
# llm = Ollama(model="mistral")
# embeddings = OllamaEmbeddings(model="nomic-embed-text")
# embeddings = E5Embeddings()