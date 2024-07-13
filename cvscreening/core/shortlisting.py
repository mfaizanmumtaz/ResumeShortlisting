from langchain_core.runnables import RunnableParallel,RunnablePassthrough,RunnableLambda
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
import os,warnings

warnings.filterwarnings("ignore")

class cv_score(BaseModel):
    """You are a powerful HR assistant. Your task is to review the given CV and determine if it matches the job requirements specified in the job description, and give a score between 0 and 1 based on their relevancy. Please do your best; it is very important for my career. If both or any of the fields are empty, then also return 0. Also, return the matching score between 0 and 1.
    > Relevant Score Between (0 and 1):
    """
    score: str = Field(..., description="Give a score to the CV between 0 and 1")

google = ChatGoogleGenerativeAI(temperature=0,model="gemini-1.5-flash",google_api_key="l1Jm8jpIpq6IvfqES5LEDUQp9CkSINmjiwYoLNtD")

google2 = ChatGoogleGenerativeAI(temperature=0,model="gemini-1.5-flash",google_api_key="AIzaSyARfxSKQwobd0MNuOAt6yUjmNUFGX4k_eI").with_fallbacks([google])
# ,tool_choice="predict_bool"
llm_with_tools = google2.bind_tools([cv_score])

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
            metadata=metadata)][0]

    else:
        return pages[0]

def process_score(cv_score):
    try:
        return float(cv_score[0].score)
    except Exception as e:
        return 0.50
    
template = PromptTemplate.from_template("""
<job description>
{job_des}
</job description>
------------
<cv>
{cv}
</cv>
""")

cv_score_cal = template | llm_with_tools | PydanticToolsParser(tools=[cv_score]) | process_score

def process_data(dict_input: dict) -> dict:
    pdf_data:Document = dict_input["pdf_data"]
    return {
        "source": pdf_data.metadata["source"],
        "cv": pdf_data.page_content,
        "job_des": dict_input["job_des"]
    }

pdfs_dir = "data"
job_description = "HI looking for python developer"

content_chain = RunnableParallel(
    {
        "pdf_data": lambda x: get_data(x["pdf_path"]),
        "job_des": lambda x: x["job_des"]
    } 
) | RunnableLambda(process_data) | RunnablePassthrough.assign(cv_score = (lambda x:x) | cv_score_cal)

def shortlist_cvs(scored_cvs:list[dict],percentage:int) -> list[str]:
    scored_cvs.sort(key=lambda x:x.get("cv_score",0),reverse=True)

    # Calculate the number of CVs to shortlist based on the percentage
    shortlist_count = int(len(scored_cvs) * percentage / 100)
    
    # Select the top N percent CVs
    shortlisted_cvs = scored_cvs[:shortlist_count]
    
    return [cv.get("source") for cv in shortlisted_cvs]

def compression(pdfs_path:list[dict],percentage:int):
    scored_cvs_list:list[dict] = content_chain.batch(pdfs_path)
    shortlisted_cvs:list[str] = shortlist_cvs(scored_cvs_list,percentage)
    return shortlisted_cvs