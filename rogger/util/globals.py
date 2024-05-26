
import json
from langchain_core.retrievers import BaseRetriever
from typing import Any, Callable, Dict, Iterable, List, Optional,Union
from langchain_core.documents import Document
from rogger.util.globals import *
from flashrank import Ranker, RerankRequest
import pandas as pd



def create_docs(raw:bool=True):
    filepath = "assets/2_landbased_air_defence_radars.xlsx"
    base_data = pd.read_excel(filepath)
    docs_buffer = []
    for _, row in base_data.iterrows():
        output = f"""{row['chapter_title']} > {row['country']} > {row['radar_name']} > """
        for col_name in [
            "subtitle_one",
            "subtitle_two",
            "subtitle_three",
            "subtitle_four",
            "subtitle_five",
        ]:
            if not pd.isna(row[col_name]):
                # last_section = row[col_name]
                output += row[col_name] + " > "

        output += " " + str(row["text"])

        if not pd.isna(row["keywords"]):
            output += " Keywords:" + ", ".join(row["keywords"].split(";"))
        tmp_doc = Document(page_content=output)
        tmp_doc.metadata = {"content":row['text']}
        docs_buffer.append(tmp_doc)
    return docs_buffer

ms = "ms-marco-MultiBERT-L-12"
zf = "rank_zephyr_7b_v1_full"
class Reranker:
    def __init__(
        self, model_name: str = ms, cache_dir: str = "assets/cache/"
    ) -> None:
        self.ranker = None
        self.model_name = model_name
        self.cache_dir = cache_dir

    def load(self):
        if self.ranker is None:
            self.ranker = Ranker(model_name=self.model_name, cache_dir=self.cache_dir, max_length=59000)

    def rerank(
        self,
        question: str,
        retrieved_documents: List[Document],
        top_k: Union[int, None] = None,
    ) -> List[Document]:

        self.load()

        formatted_documents_for_reranking = [
            {"id": i, "text": x.page_content, "meta": x.metadata}
            for i, x in enumerate(retrieved_documents)
        ]

        rerankrequest = RerankRequest(
            query=question, passages=formatted_documents_for_reranking
        )
        reranked_documents = self.ranker.rerank(rerankrequest)

        if top_k is None:
            top_k = len(reranked_documents)

        reranking_results = []
        for i in range(top_k):
            reranking_results.append(
                Document(page_content=reranked_documents[i]["text"])
            )
        return reranking_results
