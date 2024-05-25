
from __future__ import annotations
import tiktoken
from typing import Any, Callable, Dict, Iterable, List, Optional,Union
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from rogger.util.globals import *

def preprocess_text(text: str | List[str]) -> List[str]:
    enc = tiktoken.encoding_for_model("gpt-4")
    if isinstance(text, str):
        lowered = " " + text.lower()
        lowered = lowered.replace("\n"," ")
        tokens = enc.encode(lowered)
        output = [str(token) for token in tokens]
        return output
    elif isinstance(text, list):
        outputs = []
        for t in text:
            lowered = " " + t.lower()
            lowered = lowered.replace("\n"," ")
            tokens = enc.encode(lowered)
            outputs.append([str(token) for token in tokens])
        return outputs

class BM25Retriever(BaseRetriever):
    vectorizer: Any
    docs: List[Document] = Field(repr=False)
    k: int = 4
    preprocess_func: Callable[[str], List[str]] = preprocess_text

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_texts(
        cls,
        texts: Iterable[str],
        metadatas: Optional[Iterable[dict]] = None,
        bm25_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ) -> BM25Retriever:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            raise ImportError(
                "Could not import rank_bm25, please install with `pip install "
                "rank_bm25`."
            )

        texts_processed = [preprocess_func(t) for t in texts]
        bm25_params = bm25_params or {}
        vectorizer = BM25Okapi(texts_processed, **bm25_params)
        metadatas = metadatas or ({} for _ in texts)
        docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
        return cls(
            vectorizer=vectorizer, docs=docs, preprocess_func=preprocess_func, **kwargs
        )

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[Document],
        *,
        bm25_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ) -> BM25Retriever:
        texts, metadatas = zip(*((d.page_content, d.metadata) for d in documents))
        return cls.from_texts(
            texts=texts,
            bm25_params=bm25_params,
            metadatas=metadatas,
            preprocess_func=preprocess_func,
            **kwargs,
        )

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        processed_query = self.preprocess_func(query)
        return_docs = self.vectorizer.get_top_n(processed_query, self.docs, n=self.k)
        return return_docs

