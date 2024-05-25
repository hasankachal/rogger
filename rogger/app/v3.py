from rogger.util.logging import logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from rogger.vectorizer.e5 import E5Retriever
from rogger.vectorizer.bm25 import BM25Retriever
from rogger.vectorizer.tfidf import TfIdfRetriever
from rogger.retriever.manual import create_vec_store
from rogger.util.globals import *
from rogger.util.config import *
import streamlit as st
import time
from langchain_community.llms import Ollama
from rogger.llm.aya import Aya101LLM


st.set_page_config(layout='wide')


st.title('🦜🔗 BB-Assistant')
st.session_state.theme = "dark"
st.session_state.bot = "beaver"

st.markdown(
    """
<style>
    stChatMessage{
        text-align: right;
        direction:rtl;

    }
    .st-emotion-cache-janbn0 {
        flex-direction: row-reverse;
    }
    .st-emotion-cache-4oy321{
        text-align: left;
    }
    textarea {
        font-size: 16px;
        text-align: right;
        direction:rtl;
    }
    p {
        text-align: right;
        direction:rtl;
    }
</style>
""",
    unsafe_allow_html=True,
)
def _save(name,buffer):
    with open(f"assets/test/{name}.json","w",encoding='utf-8') as file:
        json.dump(buffer,file,ensure_ascii=False,indent=4)

def retrieve_topic(retriever:BaseRetriever,query:str) -> List[Document]:
    buffer = []
    result = retriever.invoke(query)
    for doc in result:
        classname = retriever.__repr__()[:13]
        logger.info(f"appending from {classname} CLASS")
        try:
            buffer.append(Document(page_content=doc.metadata["content"]))
        except Exception as fail:
            logger.error(f"failed to collect contnet metadata {doc} {fail}")
    _save(name="topic",buffer=[x.page_content for x in buffer])
    return buffer

def retrieve_page_content(retriever:BaseRetriever,query:str) -> List[Document]:
    buffer = []
    result = retriever.invoke(query)
    for doc in result:
        classname = retriever.__repr__()[:13]
        logger.info(f"appending from {classname} CLASS")
        buffer.append(Document(page_content=doc.page_content))
    _save(name="raw",buffer=[x.page_content for x in buffer])
    return buffer

    
    return buffer
if "e5" not in st.session_state:
    logger.info("Initiating E3Embeddings ...")
    st.session_state.e5 = E5Retriever
if "bm25" not in st.session_state:
    logger.info("Initiating Bm25Embeddings ...")
    st.session_state.bm25 = BM25Retriever
if "tfidf" not in st.session_state:
    logger.info("Initiating Bm25Embeddings ...")
    st.session_state.tfidf = TfIdfRetriever
if "chat_id" not in st.session_state:
    logger.info("Initiating ChatId ...")
    st.session_state.chat_id = None
if "docs_raw" not in st.session_state:
    logger.info("Initiating Docs ...")
    st.session_state.docs_raw = create_docs(raw=True)
if "docs_topic" not in st.session_state:
    logger.info("Initiating Docs ...")
    st.session_state.docs_topic = create_docs(raw=False)
if "vecstore_tfidf" not in st.session_state or "vecstore_2" not in st.session_state:
    logger.info("Initiating retriever on page content...")
    st.session_state.vecstore_tfidf = create_vec_store(retriever=st.session_state.tfidf,docs=st.session_state.docs_raw)
    st.session_state.vecstore_bm25 = create_vec_store(retriever=st.session_state.bm25,docs=st.session_state.docs_topic)
if "llm" not in st.session_state:
    logger.info("Initiating LLM ...")
    st.session_state.llm = Ollama(model="mistral")
if "chat_history" not in st.session_state:
    logger.info("Initiating chat-history")
    st.session_state.chat_history = []
# if "translator" not in st.session_state:
#     logger.info("Initiating chat-history")
#     st.session_state.translator = Aya101LLM()
# if "reranker" not in st.session_state:
#     logger.info("Initiating reranker ...")
#     st.session_state.reranker = Reranker()

def click_button():
    st.session_state.clear()
def make_prompt(message:str="",context:list=[]):
    raw_context = '\n'.join(context)
    # Answer my question which is found between <QUESTION> and <END OF QUESTION> based on the information found between <CONTEXT> and <END OF CONTEXT>.
    template = f"""
        Read the section in <CONTEXT> to find description about any content related to my text in <QUESTION> tag and answer it accordingly.

        <CONTEXT>
        {raw_context}
        <END CONTEXT>
        
        
        <QUESTION>
        {message} 
        <END QUESTION>
        """
    logger.info(f"Invoking {template}")
    return template
st.button("Reset", type="primary",on_click=click_button)
for message in st.session_state.chat_history:
    if message["src"] == "Human":
        with st.chat_message("Human"):
            st.markdown(message["text"])
    elif message["src"] == "AI":
        with st.chat_message("AI"):
            st.markdown(message["text"])
def generate_response_llm(input_text,session):
    logger.info("Invoking prompt to LLM ...")
    english_prompt = st.session_state.translator.invoke(input=f"translate this sentence from persian to english and if you seen any unknown(<UNK>) words in text just leave the word untranslated in the related position: {input_text}")
    logger.info(f"translated prompt to {english_prompt}")
    raw_context = retrieve_page_content(st.session_state.vecstore_bm25,english_prompt)
    
    # topic_based_context = retrieve_topic(st.session_state.bm25,input_text)[:12]
    # raw_context.extend(topic_based_context)
    _save(name="merged",buffer=[x.page_content for x in raw_context])
    query = make_prompt(english_prompt,context=[x.page_content for x in raw_context])
    logger.info(f"query LLM with {query}")
    response = st.session_state.llm.invoke(query)
    persian_response = st.session_state.translator.invoke(input=f"translate this english text to persian and if you seen any unknown(<UNK>) words in text just leave the word untranslated in the related position:: {response}")
    for letter in persian_response:
        time.sleep(0.01)
        yield letter
    session.append({"src":"AI","text":persian_response})


user_query = st.chat_input("Enter a prompt here")
if user_query is not None and user_query != "":
    st.session_state.chat_history.append({"src":"Human","text":user_query})

    with st.chat_message("Human"):
        st.markdown(user_query,unsafe_allow_html=True)
    with st.chat_message("AI"):
        st.write_stream(generate_response_llm(user_query,st.session_state.chat_history))

