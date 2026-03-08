# Snowflake Setup for RAG Pipeline

## Prerequisites

- A Snowflake account (sign up at [snowflake.com](https://www.snowflake.com/) if you don't have one)
- Access to a Snowflake worksheet (Worksheets > + to create a new one)

## Setup Steps

Run each block in a Snowflake worksheet. Paste the SQL, then hit **Ctrl + Enter** to execute.

### Block 1: Create Warehouse

```sql
CREATE WAREHOUSE IF NOT EXISTS RAG_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;
```

This creates a minimal compute warehouse that auto-suspends after 60 seconds of inactivity to save credits.

### Block 2: Create Database and Schema

```sql
CREATE DATABASE IF NOT EXISTS RAG_DB;
CREATE SCHEMA IF NOT EXISTS RAG_DB.RAG_SCHEMA;
```

This creates the database and schema where your RAG table with embeddings will live.

### Block 3: Verify Vector Support

```sql
SELECT [1.0, 2.0, 3.0]::VECTOR(FLOAT, 3);
```

If this returns a result (not an error), your Snowflake account supports the `VECTOR` data type needed for embedding storage and similarity search.

### Block 4: Set Defaults

```sql
USE WAREHOUSE RAG_WH;
USE DATABASE RAG_DB;
USE SCHEMA RAG_SCHEMA;
```

Sets the active warehouse, database, and schema for your current session.

## Environment Variables

After setup, use these values in your `.env` file or Colab Secrets:

```
SNOWFLAKE_WAREHOUSE=RAG_WH
SNOWFLAKE_DATABASE=RAG_DB
SNOWFLAKE_SCHEMA=RAG_SCHEMA
```

You will also need `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY`, and `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` — get these from your Snowflake admin.
