from fastapi import FastAPI, File, UploadFile, HTTPException, Form,BackgroundTasks
from fastapi.responses import FileResponse
import shutil,os,uuid
from zipfile import ZipFile
from typing import List

app = FastAPI()

# Define the compression function (replace with your actual logic)
def process_files(files_dir,job_description,percentage):
    from app import compression
    return compression(job_description, files_dir,percentage)

# Get the secret key from environment variable
SECRET_KEY = "123"
def cleanup_directory(path: str):
    shutil.rmtree(path)

@app.post("/uploadfiles/")
def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    api_key: str = Form(...),
    percentage: int = Form(...),
    job_description : str = Form(...)):

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

    file_paths = []
    main_path = f"data/resumes/{str(uuid.uuid4())}"

    # Create the directory if it doesn't exist
    os.makedirs(main_path, exist_ok=True)

    for file in files:
        file_location = f"{main_path}/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_paths.append(file_location)

    try:
        short_listed_files_paths = process_files(job_description, main_path,percentage)
        zip_filename = f"{main_path}/{str(uuid.uuid4())}.zip"

        with ZipFile(zip_filename, 'w') as zipf:
            for file_path in short_listed_files_paths:
                zipf.write(file_path, os.path.basename(file_path))

        # Return the file response and clean up after sending
        background_tasks.add_task(cleanup_directory, main_path)
        return FileResponse(zip_filename, media_type='application/zip', filename=zip_filename)

    except Exception as e:
        cleanup_directory(main_path)
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)