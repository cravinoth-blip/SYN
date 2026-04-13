# Patient Journey Pipeline — 4-Pass Agentic Orchestrator

## Architecture

```
orchestrator.py          ← Main pipeline controller (run this)
config.py                ← API keys, model settings, file paths
tools/                   ← The 6-tool harness
  __init__.py
  base.py                ← Base tool class + audit logging
  spine_search.py        ← Vector store file search
  code_interpreter.py    ← Sandboxed Python execution
  web_search.py          ← Web search via Tavily/Bing
  clinical_trials.py     ← ClinicalTrials.gov API wrapper
  fda_labelling.py       ← openFDA drug label API wrapper
  ci_supplements.py      ← User-uploaded Excel/CSV reader
passes/                  ← The 4 passes
  __init__.py
  pass1_generate.py      ← Deep generation (30+ tool calls)
  pass2_verify.py        ← Verification & deepening
  pass3_artifacts.py     ← Excel/CSV artifact construction
  pass4_polish.py        ← Editorial polish → Word doc
schema/
  __init__.py
  journey_schema.py      ← Patient journey JSON schema
audit/
  __init__.py
  logger.py              ← Audit trail builder
```

## Setup

```bash
pip install openai tiktoken openpyxl python-docx requests tavily-python chromadb pandas
```

## Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."
```

## Usage

```python
from orchestrator import PatientJourneyPipeline

pipeline = PatientJourneyPipeline()
result = pipeline.run(
    disease="Systemic Lupus Erythematosus",
    supplements=["./data/competitive_landscape.xlsx", "./data/epi_data.csv"]
)
# result.deliverable   → path to final .docx
# result.artifacts     → list of Excel/CSV file paths
# result.audit_trail   → path to audit markdown
```
