import os
#from PyPDF2 import PdfReader
from langchain_community.document_loaders import PyPDFLoader, PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools import ArxivQueryRun
#from langchain.embeddings import GooglePalmEmbeddings
#from langchain.llms import GooglePalm
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool
from langchain.agents import create_openai_tools_agent, AgentExecutor
#from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain import hub
import tempfile
from dotenv import load_dotenv
import torch
from src.logger import logging


load_dotenv()
#GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  
#os.environ['GOOGLE_API_KEY'] =  GOOGLE_API_KEY
os.environ["HUGGINGFACEHUB_API_TOKEN"]=os.getenv("HUGGINGFACEHUB_API_TOKEN")
## Langsmith tracking
#os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["GROQ_API_KEY"]=os.getenv("GROQ_API_KEY")
groq_api_key=os.environ['GROQ_API_KEY']

# Check for GPU availability
device = 'cuda' if torch.cuda.is_available() else 'cpu'

huggingface_embeddings=HuggingFaceBgeEmbeddings(
    #model_name="BAAI/bge-small-en-v1.5",  #sentence-transformers/all-MiniLM-l6-v2
    model_name="all-MiniLM-L6-v2",    
    model_kwargs={'device':device},
    encode_kwargs={'normalize_embeddings':True}
)

## Wiki Tool
wiki_wrapper=WikipediaAPIWrapper(top_k_results=1,doc_content_chars_max=200)
wiki=WikipediaQueryRun(api_wrapper=wiki_wrapper)

## Arxiv Tool
arxiv_wrapper=ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=200)
arxiv=ArxivQueryRun(api_wrapper=arxiv_wrapper)

# Get the prompt to use
prompt = hub.pull("hwchase17/openai-functions-agent")

def get_pdf_text(uploaded_pdf_docs):
    #text=""
    logging.info("=========list of pdf files========",uploaded_pdf_docs)
    for pdf in uploaded_pdf_docs:
        original_file_name = pdf.name  
        logging.info("=========The actual path========",original_file_name)
        if pdf.name.lower().endswith('.pdf'):
            if pdf is not None:
                # Read the file as bytes
                file_bytes = pdf.read()
                
                # Save the file to a temporary location
                with open(original_file_name, "wb") as f:
                    f.write(file_bytes)
                
                # Load the PDF using PyPDFLoader
                pdf_loader = PyPDFLoader(original_file_name)
                print('pdf_loader is loaded')
                pages=pdf_loader.load()
                print(pages[3])

                # Clean up the temporary file
                os.remove(original_file_name)
    return pages



def get_text_chunks(pages):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(pages)
    #chunks = text_splitter.split_text(text)
    print(chunks[10])
    return chunks



def get_vector_store(text_chunks):
    #embeddings = GooglePalmEmbeddings()
    embeddings = huggingface_embeddings
    #vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store = FAISS.from_documents(text_chunks, embedding=embeddings)
    pdf_retriever=vector_store.as_retriever()
    pdf_retriever_tool=create_retriever_tool(pdf_retriever,"pdf_search",
                      "Search for information related to pdf content. For any questions from uploaded pdf docs, you must use this tool!")
    return  pdf_retriever_tool

def get_tool_list(pdf_retriever_tool):
    tools=[pdf_retriever_tool,arxiv,wiki]
    return tools

def get_conversational_chain(tools):
    #llm=GooglePalm()
    llm=ChatGroq(groq_api_key=groq_api_key,
         model_name="mixtral-8x7b-32768",
         #max_tokens=2000
         )
    memory = ConversationBufferMemory(memory_key = "chat_history", k=5, return_messages=True)
    
    try:
        agent = create_openai_tools_agent(llm, tools, prompt)
        logging.info("Agent created successfully with conversational retrieval chain")
    except Exception as e:
        raise RuntimeError("Failed to create the agent with conversational retrieval chain.") from e
    
    try:
        conversation_chain = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)
        logging.info("Agent executor successfully created with conversational retrieval chain.")
    except Exception as e:
        raise RuntimeError("Failed to create the agent executor with conversational retrieval chain.") from e
    
    return conversation_chain
