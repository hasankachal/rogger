

from __future__ import annotations
from typing import Any, List
from rogger.util.globals import *
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any, List, Optional
import tiktoken
from typing import Any, Callable, Dict, Iterable, List, Optional,Union
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from sklearn.metrics.pairwise import cosine_similarity

def preprocess_text(text: str | List[str]) -> List[str]:
        try:
            import tiktoken
        except ImportError:
            raise ImportError(
                "Could not import tiktoken requirements"
            )
        enc = tiktoken.encoding_for_model("gpt-4")
        if isinstance(text, str):

            tokens = enc.encode(text)
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
class TfIdfRetriever(BaseRetriever):
    vectorizer: Any
    docs: List[Document] = Field(repr=False)
    features:Any
    k: int = 4
    preprocess_func: Callable[[str], List[str]] = preprocess_text

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_texts(
        cls,
        texts: Iterable[str],
        metadatas: Optional[Iterable[dict]] = None,
        tfidf_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
        except ImportError:
            raise ImportError(
                "Could not import sklearn TfIdf,cosin-similarity please install with `pip install "
                "sklearn`."
            )

        texts_processed = [preprocess_func(t) for t in texts]
        tfidf_params = tfidf_params or {}
        vectorizer = TfidfVectorizer(encoding='utf-8-sig')
        metadatas = metadatas or ({} for _ in texts)
        features = vectorizer.fit_transform(texts)
        docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
        return cls(
            vectorizer=vectorizer, docs=docs,features=features, preprocess_func=preprocess_func, **kwargs
        )

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[Document],
        *,
        bm25_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ):
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
        # processed_query = self.preprocess_func(query)
        query_vec = self.vectorizer.transform([query])
        return_docs = []
        results = cosine_similarity(self.features,query_vec).flatten()
        for i in results.argsort()[:-11:-1]:
            return_docs.append(self.docs[i])
        return return_docs

