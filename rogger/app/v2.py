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
from langchain_community.llms.ollama import Ollama
from rogger.llm.aya import Aya101LLM

# from googletrans import Translator

st.set_page_config(layout="wide")


st.title("🦜🔗 Rogger")
st.session_state.theme = "dark"

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
    .st-emotion-cache-vdokb0{
        text-align: right;
        direction:rtl;
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


def _save(name, buffer):
    with open(f"assets/test/{name}.json", "w", encoding="utf-8") as file:
        json.dump(buffer, file, ensure_ascii=False, indent=4)


def retrieve_page_content(retriever: BaseRetriever, query: str) -> List[Document]:
    buffer = []
    result = retriever.invoke(query)
    for doc in result:
        classname = retriever.__repr__()[:13]
        logger.info(f"appending from {classname} CLASS")
        buffer.append(Document(page_content=doc.page_content))
    _save(name="raw", buffer=[x.page_content for x in buffer])
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
    st.session_state.docs_raw = create_docs()
if "vecstore_bm25" not in st.session_state or "vecstore_e5" not in st.session_state:
    logger.info("Initiating retriever on page content...")
    st.session_state.vecstore_e5 = create_vec_store(
        retriever=st.session_state.e5, docs=st.session_state.docs_raw
    )
    st.session_state.vecstore_bm25 = create_vec_store(
        retriever=st.session_state.bm25, docs=st.session_state.docs_raw
    )
if "llm" not in st.session_state:
    logger.info("Initiating LLM ...")
    st.session_state.llm = Ollama(
        model="aya:35b-23", base_url="http://192.168.202.254:11434", temperature=0
    )
if "chat_history" not in st.session_state:
    logger.info("Initiating chat-history")
    st.session_state.chat_history = []


# if "reranker" not in st.session_state:
#     logger.info("Initiating reranker ...")
#     st.session_state.reranker = Reranker()


def click_button():
    st.session_state.clear()


def make_prompt(message: str = "", context: list = []):
    #     template = f"""با خواندن مطالب موجود در بخش اطلاعات پیشین قست های مرتبط با سوال من رو پیدا کن و به سوال من که در بخش سوال آمده است پاسخ بده
    # من فقط فارسی را به خوبی صحبت میکنم. از این جهت تا حد ممکن پاسخ ها را به فارسی بگو.

    # اطلاعات پیشین:
    # {context}

    # سوال:
    # {message}"""

    template = f"""{message}

اطلاعات پیشین:
{context}

فقط بر اساس اطلاعات موجود در بخش اطلاعات پیشین جواب خود را بگو و در صورتی که پاسخ در اطلاعات پیشین نیامده بود بگو نمی دانم.
"""

    logger.info(f"Invoking {template}")
    return template


st.button("Reset", type="primary", on_click=click_button)
for message in st.session_state.chat_history:
    if message["src"] == "Human":
        with st.chat_message("Human"):
            st.markdown(message["text"])
    elif message["src"] == "AI":
        with st.chat_message("AI"):
            st.markdown(message["text"])


def generate_response_llm(input_text, session):
    print(len(st.session_state.docs_raw))
    logger.info("Invoking prompt to LLM ...")
    raw_context = retrieve_page_content(st.session_state.vecstore_bm25, input_text)
    extend_context = retrieve_page_content(st.session_state.vecstore_e5, input_text)
    raw_context.extend(extend_context)
    ctx_list = list(set([x.page_content for x in raw_context]))
    _save(name="merged", buffer=ctx_list)
    context = "\n".join(ctx_list)
    query = make_prompt(input_text, context=context)
    logger.info(f"query LLM with {query}")
    response = st.session_state.llm.invoke(query)
    logger.warning(f"raw response from llm {response}")
    response.replace(":", "")
    for letter in response:
        time.sleep(0.01)
        yield letter
    session.append({"src": "AI", "text": response})


user_query = st.chat_input("Enter a prompt here")
if user_query is not None and user_query != "":
    st.session_state.chat_history.append({"src": "Human", "text": user_query})

    with st.chat_message("Human"):
        st.markdown(user_query, unsafe_allow_html=True)
    with st.chat_message("AI"):
        st.write_stream(
            generate_response_llm(user_query, st.session_state.chat_history)
        )
