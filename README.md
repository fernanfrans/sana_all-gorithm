## PJDSC 2025
# Radar Reflectivity-Based Nowcasting Framework for Short-Term Rainfall Prediction

### Sana All-gorithm
Fernan Frans B. Pelobello\
Maxine Van L. Caparas\
Ma. Angelika C. Regoso\
Pamela Anne C. Serrano

## Requirements
- Python: https://www.python.org/downloads
  - **Note**: Python versions `3.13.x` and above do not work properly with this web app. Install an older version (up to `3.12.x`)
- pip (pre-installed with Python): https://pypi.org/project/pip/

## Setting-up
- Clone the project with `https://github.com/fernanfrans/sana_all-gorithm.git`
- Move to the main directory with `cd sana_all-gorithm`
- Create a virtual environment with `python3 -m venv venv`
  - **Note**: If starting the command with `python3` does not work, use the exact Python version installed (e.g., `python3.12`)
- Activate the virtual environment with `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix/MacOS)
- Install the dependencies with `pip install -r requirements.txt`
- Create `/.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example` for required fields).

## Running the Web App
- In the same directory, start the application with `streamlit run rainloop.py`
- Usually, the web app page automatically opens on a certain browser. If not, open the application by going to `localhost:8501` on any browser.
