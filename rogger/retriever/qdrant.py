# from langchain.vectorstores import Qdrant
from langchain.vectorstores import qdrant
from qdrant_client import QdrantClient
from rogger.util.globals import *
client = QdrantClient(host="localhost", port=6333)
def create_vec_store(retriever:BaseRetriever,docs:List[Document]):
    doc_store = qdrant(
        client=client, 
        collection_name="BBZR", 
        embeddings=retriever,
    )

