# Google Drive Setup for ETL Pipeline

## Overview

The ETL notebook (`ETL_Code_Dec.ipynb`) is designed to run on Google Colab with Google Drive integration. It reads source documents (PDFs, DOCX, etc.) from a Google Drive folder, processes them into chunks with embeddings, and uploads the results to Snowflake.

## How It Works

The notebook mounts your Google Drive as a local filesystem inside Google Colab at `/content/drive`. This gives the ETL code direct file access to all your Drive files without needing any API keys or OAuth setup.

## Setup Steps

### 1. Organize Documents in Google Drive

Create a folder in your Google Drive to hold the source documents. For example:

```
My Drive/
  RAG/
    documents/    <-- put your PDFs here
```

### 2. Upload the Notebook to Google Colab

- Go to [Google Colab](https://colab.research.google.com/)
- File > Upload notebook
- Select `ETL_Code_Dec.ipynb` from your local machine

### 3. Configure Folder Paths (Cell 3)

Update these variables in the notebook:

```python
INPUT_FOLDER = "/content/drive/MyDrive/RAG/documents/"  # Folder with your PDFs
OUTPUT_FOLDER = "/content/drive/MyDrive/RAG/output/"     # Folder for CSV output
CSV_FILENAME = "Example_name.csv"                        # Name for the output CSV
```

- `INPUT_FOLDER` - Path to your Google Drive folder containing source documents
- `OUTPUT_FOLDER` - Path where the processed CSV (with embeddings) will be saved
- `CSV_FILENAME` - Name of the output CSV file

Note: Google Drive paths in Colab always start with `/content/drive/MyDrive/`.

### 4. Configure Snowflake and Upload Settings (Cell 3)

```python
TABLE_NAME = "TABLE_NAME".upper()   # Your Snowflake table name
UPLOAD_MODE = "append"              # "replace", "append", or "upsert"
RECREATE_TABLE = True               # True to recreate the table from scratch
GENERATE_NEW_CSV = True             # True to run the full ETL pipeline
UPLOAD_TO_SNOWFLAKE = True          # True to upload results to Snowflake
```

### 5. Run the Notebook

- Run all cells (Runtime > Run all)
- The first cell will prompt you to authorize Google Drive access — click "Allow"
- The pipeline will:
  1. Read documents from `INPUT_FOLDER`
  2. Extract text, chunk, and generate metadata
  3. Generate embeddings via OpenAI (`text-embedding-3-small`)
  4. Save the CSV to `OUTPUT_FOLDER`
  5. Upload to Snowflake (if enabled)

## Common Upload Mode Usage

| Scenario | Settings |
|----------|----------|
| First time with new papers | `GENERATE_NEW_CSV=True, UPLOAD_TO_SNOWFLAKE=True, UPLOAD_MODE="replace"` |
| Re-upload same data (saves money) | `GENERATE_NEW_CSV=False, UPLOAD_TO_SNOWFLAKE=True, UPLOAD_MODE="replace"` |
| Add new papers to existing collection | `GENERATE_NEW_CSV=True, UPLOAD_TO_SNOWFLAKE=True, UPLOAD_MODE="append"` |
| Just test processing without uploading | `GENERATE_NEW_CSV=True, UPLOAD_TO_SNOWFLAKE=False` |

## Environment Variables

The notebook requires these (set in Colab via Colab Secrets):

- `OPENAI_API_KEY` - For generating embeddings and metadata
- `SNOWFLAKE_ACCOUNT` - Snowflake account identifier
- `SNOWFLAKE_USER` - Snowflake username
- `SNOWFLAKE_WAREHOUSE` - Snowflake warehouse name
- `SNOWFLAKE_DATABASE` - Snowflake database name
- `SNOWFLAKE_SCHEMA` - Snowflake schema name
- `SNOWFLAKE_PRIVATE_KEY` - PEM format private key for Snowflake auth
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` - Passphrase for the private key

## Alternative Local Options

- **Google Drive Desktop App**: Install Google Drive for Desktop, which mounts your Drive as a local folder. Point `INPUT_FOLDER` to that local path (e.g., `~/Google Drive/My Drive/RAG/documents/`).
- **Google Drive API**: Use `google-api-python-client` with OAuth to download files programmatically. Requires a Google Cloud project and `credentials.json`.
