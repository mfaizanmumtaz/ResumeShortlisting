from langchain_core.runnables import (
    RunnablePassthrough,
)
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader

from langchain_huggingface import HuggingFaceEmbeddings

# from langchain_cohere import CohereEmbeddings
import warnings, uuid
from langchain_community.vectorstores import Chroma

warnings.filterwarnings("ignore")

embeddings = HuggingFaceEmbeddings()
# embeddings = CohereEmbeddings()


def get_data(file_path):
    pages = PyMuPDFLoader(file_path=file_path).load()
    if len(pages) > 1:
        pdfstring = ""
        metadata = {}
        for page in pages:
            pdfstring += page.page_content
            metadata.update(page.metadata)

        return Document(page_content=pdfstring, metadata=metadata)

    else:
        return pages[0]


def shortlist_cvs(top_ranked_cvs: list[Document], percentage: int) -> list[str]:

    # Calculate the number of CVs to shortlist based on the percentage
    shortlist_count = int(len(top_ranked_cvs) * percentage / 100)

    # Select the top N percent CVs
    shortlisted_cvs = top_ranked_cvs[:shortlist_count]

    return [cv.metadata.get("source") for cv in shortlisted_cvs]


def embedd_docs(docs: dict[Document], job_description: str, files_count: int):
    collection_name = uuid.uuid4()
    vector_store = Chroma.from_documents(
        embedding=embeddings,
        documents=docs,
        collection_name=str(collection_name),
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": files_count})
    top_ranked_cvs = retriever.invoke(job_description)
    vector_store.delete_collection()
    return top_ranked_cvs


def compression(files_paths: list[str], job_description: str, percentage: int):
    content_chain = RunnablePassthrough() | get_data
    docs = content_chain.batch(files_paths)

    top_ranked_cvs = embedd_docs(docs, job_description, len(files_paths))

    shortlisted_cvs: list[str] = shortlist_cvs(top_ranked_cvs, percentage)
    return shortlisted_cvs
