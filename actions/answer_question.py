import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import logging
from datetime import datetime


from langchain.chains.mapreduce import MapReduceChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ReduceDocumentsChain, MapReduceDocumentsChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import WebBaseLoader
from langchain.chains.summarize import load_summarize_chain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.document_loaders import DirectoryLoader
from langchain.document_loaders import TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter


logging.basicConfig()
logging.getLogger('langchain.retrievers.multi_query').setLevel(logging.INFO)

def answer_question(directory, question):
    text_loader_kwargs={'autodetect_encoding': True}
    loader = DirectoryLoader(directory, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs, show_progress=True, use_multithreading=True)

    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 10000, chunk_overlap = 100)
    all_splits = text_splitter.split_documents(docs)

    llm = ChatOpenAI(temperature=0.3, model="gpt-4")

    vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings())

    map_template = f"""Use the following portion of a long document to see if any of the text is relevant to answer the question.
    Return any relevant text verbatim. 
    Focus on the question and do not write meaningless or irrelevant information.
    Focus objective information, including as many facts and numbers as possible. 
    Ignore subjective statements, especially when a company writes about itself or competitors. Ignore mission or vision statements.
    Focus on recent information. The date and time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Mention all url sources at the beginning of your summary in apa format.
    If none of the information is relevant to the question, just say that there is no relevant information, don't try to make up an answer.
    Context: {{context}}
    Question: {{question}}
    Helpful Answer:"""
    MAP_PROMPT = PromptTemplate.from_template(map_template)

    reduce_template = f"""Use the following summaries to write a report on the question at the end. 
    Focus on the question and do not write meaningless or irrelevant information.
    Write the report in a structured, informative way.
    Focus objective information, including as many facts and numbers as possible. 
    Ignore subjective statements, especially when a company writes about itself or competitors. Ignore mission or vision statements.
    Focus on recent information. The date and time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    The report should have a minimum of 500 and a maximum of 1000 words.
    Name all sources (urls), that you used, at the end of the report in apa format.
    If you do not have any information above in this instruction, do not write a summary, but say that you would like to conduct further research.
    Summaries: {{summaries}}
    Question: {{question}}
    Helpful Answer:"""
    REDUCE_PROMPT = PromptTemplate.from_template(reduce_template)

    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vectorstore.as_retriever(search_kwargs={'k': 10}),
        chain_type="map_reduce",
        chain_type_kwargs={"question_prompt": MAP_PROMPT, "combine_prompt": REDUCE_PROMPT}
    )

    answer = qa_chain({"query": question})

    return(answer['result'])
