
from __future__ import annotations
from typing import Any, List
from rogger.util.globals import *
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any, List, Optional
import tiktoken
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from typing import Any, Dict, Iterator, List, Mapping, Optional
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma

e5_checkpoint = "intfloat/multilingual-e5-large-instruct"

e5_model = SentenceTransformer(e5_checkpoint)
# e5_model.max_seq_length = 1000

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
class E5Embeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        global e5_model
        embeddings = e5_model.encode(
            texts, convert_to_tensor=True, normalize_embeddings=True
        )
        return [embedding.tolist() for embedding in embeddings]

    def embed_query(self, text: str) -> List[float]:
        task_description = (
            "Given a web search query, retrieve relevant passages that answer the query"
        )
        query = f"Instruct: {task_description}\nQuery: {text}"
        resp = self.embed_documents([query])[0]
        return resp
    
class E5Retriever(BaseRetriever):
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
        tfidf_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ):
        # try:
        #     from sklearn.feature_extraction.text import TfidfVectorizer
        #     from sklearn.metrics.pairwise import cosine_similarity
        # except ImportError:
        #     raise ImportError(
        #         "Could not import sklearn TfIdf,cosin-similarity please install with `pip install "
        #         "sklearn`."
        #     )

        # texts_processed = [preprocess_func(t) for t in texts]
        tfidf_params = tfidf_params or {}
        vectorizer = E5Embeddings()
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
        e5_params: Optional[Dict[str, Any]] = None,
        preprocess_func: Callable[[str], List[str]] = preprocess_text,
        **kwargs: Any,
    ):
        texts, metadatas = zip(*((d.page_content, d.metadata) for d in documents))
        return cls.from_texts(
            texts=texts,
            e5_params=e5_params,
            metadatas=metadatas,
            preprocess_func=preprocess_func,
            **kwargs,
        )

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        retriver = Chroma.from_documents(documents=self.docs,embedding=self.vectorizer,persist_directory="assets/cache").as_retriever()
        return_docs = retriver.invoke(query)
        return return_docs

