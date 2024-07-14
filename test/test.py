import sys, os

# Get the directory containing the test.py file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(current_dir, "..")))

from cvscreening import compression, get_data

job_description = "i am looing for ml book could you please help me in this regard."

# Get the absolute path of the current directory
current_dir = os.path.abspath(os.path.dirname(__file__))

# Construct the path to the "data" directory
data_dir = os.path.join(current_dir, "data")

# Create a list of dictionaries with PDF paths and job description
pdfs_path_with_description = [
    {"pdf_path": os.path.join(data_dir, pdf_path), "job_des": job_description}
    for pdf_path in os.listdir(data_dir)
]
pdfs_path_with_description = [
    os.path.join(data_dir, pdf_path) for pdf_path in os.listdir(data_dir)
]

# res =compression(pdfs_path_with_description,70)
# print(res)

log_file = os.path.join(os.path.dirname(__file__), "logs", "log.log")
print(log_file)