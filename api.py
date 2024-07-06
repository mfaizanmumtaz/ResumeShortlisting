from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
import shutil,os,uuid
from zipfile import ZipFile
from typing import List

app = FastAPI()

SECRET_KEY = "123"

@app.post("/uploadfiles/")
async def upload_files(
    files: List[UploadFile] = File(...),
    api_key: str = Form(...),
    job_description : str = Form(...)):

    if api_key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validate all files are PDFs
    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="All files must be PDF.")

    with open('job_description.txt', 'w') as f:
        f.write(job_description)

    file_paths = []

    for file in files:
        file_location = f"files/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_paths.append(file_location)

    zip_filename = str(uuid.uuid4()) + ".zip"

    with ZipFile(zip_filename, 'w') as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))

    os.remove(zip_filename)
    for file in files:
        file_location = f"files/{file.filename}"
        os.remove(file_location)

    return FileResponse(zip_filename, media_type='application/zip', filename=zip_filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
