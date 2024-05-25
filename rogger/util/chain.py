from __future__ import annotations

import logging

from langchain_chroma import Chroma
from langchain.storage import InMemoryStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.llms.ollama import Ollama
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts.chat import ChatPromptTemplate


from os.path import exists as file_exists
from llama_index.readers.smart_pdf_loader import SmartPDFLoader
from langchain_core.documents import Document
from langchain_core.language_models.llms import LLM

from typing import List, Union

from util.globals import *


logging.basicConfig(level=logging.INFO)


class RagChain:
    def __init__(
        self,
        pdf_path: str,
        main_llm: Ollama,
        summarizer: LLM,
        embeddings: Embeddings,
    ) -> None:
        # Check and load PDF
        if (pdf_path is None) or (pdf_path == "") or (not file_exists(pdf_path)):
            raise Exception("invalid pdf_path.")

        self.__pdf_path = pdf_path
        self.embeddings = embeddings
        self.main_llm = main_llm
        self.summarizer = summarizer

        # Load PDF
        self.__initial_document: Union[List[Document], None] = None

        # Setup Vector
        self.vectorstore = Chroma(embedding_function=self.embeddings)
        self.vectorstore.delete_collection()

        # Initialize Retriever
        self.retriever = False

        # Initialize chat history
        self.chat_history: List[Message] = []
        self.summarization_history: List[Message] = []

        self.load_pdf()
        self.initialize_retriever()

    def load_pdf(self):
        if self.__initial_document is None:
            logging.info(f"Loading {self.__pdf_path} started")

            llmsherpa_api_url = "http://localhost:5010/api/parseDocument?renderFormat=all&applyOcr=yes&useNewIndentParser=yes"
            pdf_loader = SmartPDFLoader(llmsherpa_api_url=llmsherpa_api_url)
            documents = pdf_loader.load_data(self.__pdf_path)
            self.__initial_document = [Document(page_content=x.text) for x in documents]

            logging.info(f"Loading Finished")

    def initialize_retriever(self):
        self.load_pdf()

        if self.retriever is False:
            logging.info("Retriever Initialization started")
            # Setup BM25
            self.bm25_retriever = BM25Retriever.from_documents(
                documents=self.__initial_document
            )
            self.bm25_retriever.k = 8
            logging.info("BM25 retriever Initialized")

            # Setup neural retriever
            lower_docs = [
                Document(page_content=" " + x.page_content.lower().replace("\n", " "))
                for x in self.__initial_document
            ]
            self.vectorstore = Chroma.from_documents(lower_docs, self.embeddings)
            self.neural_retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 8}
            )
            logging.info("Neural retriever Initialized")

            self.retriever = True

            logging.info("Retriever Initialization Finished")

    def retrive_rerank_documents(self, question: str) -> List[Document]:
        logging.info(f"Retrieving for {question}")

        nueral_retriever_results = self.neural_retriever.invoke(question)
        bm25_results = self.bm25_retriever.invoke(question)
        aggregated_results = [
            x.page_content.strip().replace("\n", " ") for x in nueral_retriever_results
        ]
        aggregated_results += [
            x.page_content.lower().replace("\n", " ") for x in bm25_results
        ]
        aggregated_results = list(set(aggregated_results))

        aggregated_results = [Document(page_content=x) for x in aggregated_results]
        logging.info(f"Retrieved documents:\n{aggregated_results}")

        logging.info(f"Reranked documents:\n{aggregated_results}")
        return aggregated_results

    def format_prompt(
        self,
        question: str,
        context_documents: List[Document],
    ) -> str:
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Your name is Naser and you are my intelligent helpful research assistant.",
                ),
                (
                    "human",
                    """As the mighty proffessor, I am trying to read and understand a textbook and most often I am encountering questions in my mind. I study the book and I come up with pieces of text that might contain just enough information to answer my question. I want you to read these text contained between <CONTEXT> and <END OF CONTEXT> and answer my question which is found between <QUESTION> and <END OF QUESTION>. I am NOT interested in your own knowledge or opinions and I want you to say I don't know if the provided information is not enough. You have to consider that the text contains various types of names and models which are cruicial to the answer so you Must include them in your response. There will be some parts in the context which does not have any information about the question, you MUST ignore them completely and attend to the parts that contain the information.

<CONTEXT>
{context} 
<END OF CONTEXT>

<CHAT HISTORY>
{history}
<END OF CHAT HISTORY>

<QUESTION> 
{question} 
<END OF QUESTION>""",
                ),
            ]
        )
        logging.info(f"Formatting prompt")

        context = []
        for i, x in enumerate(context_documents):
            context.append(
                f"""<PART {i}>
            {x.page_content}
            <END OF PART {i}>"""
            )

        prompt = prompt_template.invoke(
            {
                "question": question,
                "context": "\n\n".join([x for x in context]),
                "history": "\n".join(
                    [f"{m.role}: {m.message}" for m in self.chat_history]
                ),
            }
        )
        logging.info(f"Prompt:\n{prompt.to_string()}")

        return prompt

    def record_history(self, message: Message):
        self.chat_history.append(message)

    def clear_history(self):
        self.chat_history = []

    def get_history(self):
        return self.chat_history

    def record_summarization_history(self, message: Message):
        self.summarization_history.append(message)

    def clear_summarization_history(self):
        self.summarization_history = []

    def get_summarization_history(self):
        return self.summarization_history

    def contextualize_question(self, question: str, history: List[Message]):
        if len(history) == 0:
            # We should reformulate the user question based on the history
            return question

        logging.info(f"Non Contextualized question:\n{question}")

        chat_history = "\n".join([x.message for x in history if x.role == "user"])

        prompt = f"""System: Your name is Naser and you are my intelligent helpful research assistant.
Human: There is a chat history between a user and an assistant which you can find in Chat History. Now the user is asking another question which you can find in Latest user question section. The question might reference context in the chat history. I want you to formulate a standalone question which can be understood in absence of chat history. I am not intersted in your own answer but rather I only want you to include chat history in the latest user question. Just give me the question.

Chat History:
{chat_history}

Lates user question:
{question}"""
        logging.info(f"Contextualized Prompt:\n{prompt}")

        contextualized_question = self.main_llm.invoke(prompt)
        logging.info(f"Contextualized question:\n{contextualized_question}")

        return contextualized_question

    def summarize_response(self, response: str) -> str:
        logging.info(f"Initial response: {response}")
        summarized_response = self.summarizer.invoke(
            f"Translate to Persian: {response}"
        )
        logging.info(f"Summarized response: {summarized_response}")
        return summarized_response

    def summarize_question(self, question: str) -> str:
        logging.info(f"Initial question: {question}")
        summarized_question = self.summarizer.invoke(
            f"Translate to English: {question}"
        )
        logging.info(f"Summarized question: {summarized_question}")
        return summarized_question

    def invoke(self, question: str):
        summarized_question = self.summarize_question(question)
        contextualized_question = self.contextualize_question(
            question=summarized_question, history=self.get_history()
        )
        context = self.retrive_rerank_documents(question=contextualized_question)
        prompt = self.format_prompt(
            question=summarized_question, context_documents=context
        )
        llm_response = self.main_llm.invoke(prompt)
        self.record_history(Message(role="user", message=summarized_question))
        self.record_history(Message(role="assistant", message=llm_response))

        summarized_response = self.summarize_response(llm_response)

        self.record_summarization_history(Message(role="user", message=question))
        self.record_summarization_history(
            Message(role="assistant", message=summarized_response)
        )

        return summarized_response
