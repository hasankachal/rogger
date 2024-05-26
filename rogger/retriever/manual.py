from rogger.util.globals import *
import pandas as pd



def create_vec_store(retriever:BaseRetriever,docs:List[Document]):
    bm25_retriever = retriever.from_documents(documents=docs)
    bm25_retriever.k = 15
    return bm25_retriever

