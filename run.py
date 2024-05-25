# from loaders.dataloader import translator
import pandas as pd
import json
from rogger.retriever.manual import *

def read_data(name):
    with open(f"assets/{name}","r",encoding='utf-8') as file:
        content = json.load(file)
    return content
def create_docs():
    filepath = "assets/fa.json"
    base_data = read_data("fa.json")
    docs_buffer = []
    for chunk in base_data:
        temp_doc = Document(page_content=chunk['content'])
        temp_doc.metadata = {"source":filepath,"id":chunk['id']}
        docs_buffer.append(temp_doc)
    return docs_buffer

def load_retriever():
    docs = create_docs()
    bm25_retriever = BM25Retriever.from_documents(documents=docs)
    bm25_retriever.k = 8
    result = bm25_retriever.invoke("حضرت ابولفظل")
    buffer = []
    for doc in result:
        content = doc.page_content.replace("\n","")
        sections = content.split(".")
        buffer.extend(sections)
    with open(f"s.txt","w",encoding='utf-8') as file:
        content = json.dump(buffer,file,ensure_ascii=False,indent=4)
if __name__ == "__main__":
    # fix()
    # translator()
    ret = load_retriever()

