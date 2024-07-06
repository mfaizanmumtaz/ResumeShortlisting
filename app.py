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
import os,asyncio,warnings,shutil,uuid
warnings.filterwarnings("ignore")

def syncdata(data_dir):
    if pdfs:=[os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith(".pdf")]:
        return pdfs[:5]


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

async def main(pdfs):
    content_chain = RunnablePassthrough() | get_data
    return flatteningdocs(await content_chain.abatch(pdfs))

def find_percent(number):
    return int(number * 0.70)

def indexing(content,pdfcount):
    selected = find_percent(pdfcount)
    collection_name = str(uuid.uuid4())
    model_name = "sentence-transformers/all-mpnet-base-v2"
    embedding = HuggingFaceEmbeddings(model_name=model_name)

    return Chroma.from_documents(embedding=embedding,documents=content,collection_name=collection_name).as_retriever(
        search_kwargs={'k':selected})

# print("Total PDF's are:",pdfcounts)
# print("Top Seventy Percent will be selected:",selected)


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

def compression_retriever(retriever):

    return ContextualCompressionRetriever(
        base_compressor=_filter, base_retriever=retriever)

# from utils import des

def compression(job_description,data_dir):
    if os.path.isdir(data_dir):
        pdfs_path = syncdata(data_dir)
        pdfs_content = asyncio.run(main(pdfs_path))

        print("Indexing...")
        retriever = indexing(pdfs_content,len(pdfs_content))

        print("Compression...")
        compressed_docs = compression_retriever(retriever).invoke(job_description)

        shortlisted_cvs = [cv.metadata['source'] for cv in compressed_docs]
        destination = 'shortlisted_resume'
        os.makedirs(destination,exist_ok=True)

        for file in os.listdir(destination):
            os.remove(os.path.join(destination, file))

        for filename in shortlisted_cvs:
            shutil.copy(filename, destination)
        retriever.delete_collection()

def calculate_percentage(selected, total):
    return int((selected / total) * 100)

compression('i am looking for job','data')

# percentage = calculate_percentage(len(shortlisted_cvs), pdfcounts)
