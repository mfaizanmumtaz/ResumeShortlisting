from langchain.retrievers.document_compressors import LLMChainFilter
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_groq import ChatGroq
import os,asyncio,warnings,uuid
warnings.filterwarnings("ignore")

os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"]="CV"

def flatteningdocs(data):
    return [item for sublist in data for item in sublist]

def get_data(file_path):
    pages = PyPDFLoader(file_path=file_path).load()
    if len(pages) > 1:
        pdfstring = ""
        metadata = {}
        for page in pages:
            pdfstring += page.page_content
            metadata.update(page.metadata)

        return [Document(
            page_content=pdfstring,
            metadata=metadata)]
        
    else:
        return pages

async def main(pdfs_dir):
    pdfs_path = [f"{pdfs_dir}/{pdf}" for pdf in os.listdir(pdfs_dir)]
    content_chain = RunnablePassthrough() | get_data
    return flatteningdocs(await content_chain.abatch(pdfs_path))

def indexing(content):
    collection_name = str(uuid.uuid4())
    model_name = "sentence-transformers/all-mpnet-base-v2"
    embedding = HuggingFaceEmbeddings(model_name=model_name)
    
    return Chroma.from_documents(embedding=embedding,documents=content,persist_directory="db",collection_name=collection_name)

Groq = ChatGroq(
    temperature=0,
    model="llama3-70b-8192").with_fallbacks([ChatGoogleGenerativeAI(model="gemini-1.5-flash",google_api_key=os.getenv("google_api_key"))])

prompt_template = """You are a powerfull assistant your task is to check weather the given CV match the given job requirements.Return only Yes if it match else return No.
<job description>{question}</job description>
# <cv>{context}</cv>
> Relevant (YES / NO):"""

def _get_default_chain_prompt() -> PromptTemplate:
    return PromptTemplate(
        template=prompt_template,
        input_variables=["question", "context"],
        output_parser=BooleanOutputParser())

_filter = LLMChainFilter.from_llm(Groq,prompt=_get_default_chain_prompt())
def find_percent(pdfcount):
    if pdfcount > 20:
        return int(pdfcount * 0.70)
    else:
        return int(pdfcount)

def compression_retriever(retriever,pdfcount):
    selected = find_percent(pdfcount)

    return ContextualCompressionRetriever(
        base_compressor=_filter, base_retriever=retriever.as_retriever(
        search_kwargs={'k':selected}))

def compression(job_description,pdfs_dir):
        pdfs_content = asyncio.run(main(pdfs_dir))

        print("Indexing...")
        retriever = indexing(pdfs_content)

        print("Compression...")
        compressed_docs = compression_retriever(retriever,len(pdfs_content)).invoke(job_description)

        shortlisted_cvs = [cv.metadata['source'] for cv in compressed_docs]
        retriever.delete_collection()
        return shortlisted_cvs