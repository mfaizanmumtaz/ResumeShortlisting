from fastapi import FastAPI, File, UploadFile, HTTPException, Form,BackgroundTasks
from fastapi.responses import FileResponse
import shutil,os,uuid,asyncio,logging
from zipfile import ZipFile
from typing import List

app = FastAPI()

# Get the secret key from environment variable
SECRET_KEY = "123"

def cleanup_directory(path: str):
    shutil.rmtree(path)

def data_validation(files: List[UploadFile],api_key:str,percentage:int,job_description:str):
    if api_key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not (5 <= len(files) <= 900):
        raise HTTPException(status_code=400, detail="Number of files must be between 20 and 900.")

    if percentage < 0 or percentage > 100:
        raise HTTPException(status_code=400, detail="Percentage must be between 0 and 100.")

    # Validate all files are PDFs
    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="All files must be PDF.")
        
    # Check the length of the job description
    job_description_length = len(job_description.split())
    if job_description_length < 20 or job_description_length > 1000:
        raise HTTPException(status_code=400, detail="Job description must be between 20 and 1000 words.")
    
def handling_logs():
    log_file = os.path.join(os.path.dirname(__file__), 'logs', 'log.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@app.post("/uploadfiles/")
def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    api_key: str = Form(...),
    percentage: int = Form(...),
    job_description : str = Form(...)):

    data_validation(files,api_key,percentage,job_description)

    # creating a data/resumes/unique_folder_name in the parent dir
    # Define the base path two levels up from the script's location
    base_path = os.path.join(os.path.dirname(__file__),'..', 'data', 'resumes')

    # Create the unique directory path
    main_path = os.path.join(base_path, str(uuid.uuid4()))

    # Create the directory
    os.makedirs(main_path, exist_ok=True)

    pdfs_paths = []
    for file in files:
        file_location = f"{main_path}/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        pdfs_paths.append(file_location)

    try:
        pdfs_path_with_description = [{"pdf_path":pdf_path,"job_des":job_description} for pdf_path in pdfs_paths]

        from core import compression
        # short_listed_files_paths = asyncio.run(compression(pdfs_path_with_description,percentage))
        short_listed_files_paths = compression(pdfs_path_with_description,percentage)

        zip_filename = f"{main_path}/{str(uuid.uuid4())}.zip"

        with ZipFile(zip_filename, 'w') as zipf:
            for file_path in short_listed_files_paths:
                zipf.write(file_path, os.path.basename(file_path))

        # Return the file response and clean up after sending
        background_tasks.add_task(cleanup_directory, main_path)
        return FileResponse(zip_filename, media_type='application/zip', filename=zip_filename)

    except Exception as e:
        handling_logs()
        logging.error(f"Error occurr-ed: {str(e)}")
        cleanup_directory(main_path)
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)