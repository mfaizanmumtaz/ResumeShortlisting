from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
import os,asyncio,warnings

warnings.filterwarnings("ignore")

os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"]= "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"
os.environ["LANGCHAIN_PROJECT"]="default"

def flatteningdocs(data,job_description):
    flatten =  [item for sublist in data for item in sublist]
    return [{"source":cv.metadata['source'],"cv":cv.page_content,"job_des":job_description} for cv in flatten]

def get_data(file_path):
    try:
        pages = UnstructuredFileLoader(file_path=file_path).load()
        if pages[0].page_content:
            return pages
        
        return []
    
    except Exception as e:
        return []

async def main(pdfs_dir,job_description):
    pdfs_path = [f"{pdfs_dir}/{pdf}" for pdf in os.listdir(pdfs_dir)]
    content_chain = RunnablePassthrough() | get_data
    return flatteningdocs(await content_chain.abatch(pdfs_path),job_description)

prompt_template = """
<job description>
{job_des}
</job description>
------------
<cv>
{cv}
</cv>
"""

template = PromptTemplate(
        template=prompt_template,
        input_variables=["job_des", "cv"])

# Note that the docstrings here are crucial, as they will be passed along
# to the model along with the class name.
class cv_score(BaseModel):
    """You are a powerful HR assistant. Your task is to review the given CV and determine if it matches the job requirements specified in the job description, and give a score between 0 and 1 based on their relevancy. Please do your best; it is very important for my career. If both or any of the fields are empty, then also return 0. Also, return the matching score between 0 and 1.
    > Relevant Score Between (0 and 1):
    """

    # selection: str = Field(..., description="YES/NO")
    score: str = Field(..., description="Give a score to the CV between 0 and 1")

# groq = ChatGroq(temperature=0,max_retries=0,model_name="mixtral-8x7b-32768")
# groq2 = ChatGroq(api_key="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",temperature=0,max_retries=0,model_name="mixtral-8x7b-32768").with_fallbacks([groq])

google = ChatGoogleGenerativeAI(max_retries=0,temperature=0,model="gemini-1.5-flash",google_api_key=os.getenv("dgoogle_api_key"))
google2 = ChatGoogleGenerativeAI(max_retries=0,temperature=0,model="gemini-1.5-flash",google_api_key=os.getenv("google_api_key")).with_fallbacks([google])
# ,tool_choice="predict_bool"
llm_with_tools = google2.bind_tools([cv_score])

job_des_cv_chain = RunnablePassthrough.assign(
selection_Bool = RunnablePassthrough.assign(
    source = (lambda x:x["source"]),
    job_des = (lambda x:x["job_des"]),
    cv = (lambda x:x["cv"])) | template | llm_with_tools | PydanticToolsParser(tools=[cv_score]))

def shortlist_cvs(cv_list,percentage):
    scored_cvs = [(cv.get("source"),float(cv.get("selection_Bool")[0].score)) for cv in cv_list]
    
    # Sort CVs based on relevance scores in descending order
    scored_cvs.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate the number of CVs to shortlist based on the percentage
    shortlist_count = int(len(cv_list) * percentage / 100)
    
    # Select the top N percent CVs
    shortlisted_cvs = scored_cvs[:shortlist_count]
    
    return [cv[0] for cv in shortlisted_cvs]

def compression(pdf_dir,job_description,percentage):
    pdfs_content = asyncio.run(main(pdf_dir,job_description))
    cv_score_list = job_des_cv_chain.batch(pdfs_content)
    shortlisted_cvs = shortlist_cvs(cv_score_list,percentage)
    return shortlisted_cvs