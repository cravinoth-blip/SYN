"""
Quickstart — Run the pipeline with minimal setup.

1. Set your API keys:
   export OPENAI_API_KEY="sk-..."
   export TAVILY_API_KEY="tvly-..."

2. (Optional) Ingest your evidence spine:
   python ingest_spine.py ./data/my_research/*.pdf

3. Run this script:
   python quickstart.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import PatientJourneyPipeline


def main():
    # ── Verify API keys ────────────────────────────────────────
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY environment variable")
        print("  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    if not os.getenv("TAVILY_API_KEY"):
        print("WARNING: TAVILY_API_KEY not set — web search tool will fail")
        print("  export TAVILY_API_KEY='tvly-...'")
        print("  (Pipeline will still run using other tools)\n")

    # ── Run the pipeline ───────────────────────────────────────
    pipeline = PatientJourneyPipeline()

    result = pipeline.run(
        disease="Systemic Lupus Erythematosus",

        # Optional: provide a locked research plan
        plan={
            "focus_areas": [
                "Diagnosis delay and its emotional impact",
                "Treatment burden and adherence challenges",
                "Flare management and quality of life",
                "Specialist access and care coordination gaps",
            ],
            "target_audience": "Medical affairs and brand strategy team",
            "geographic_focus": "United States",
        },

        # Optional: paths to supplemental datasets
        supplements=[
            # "./data/competitive_landscape.xlsx",
            # "./data/lupus_epi_data.csv",
        ],
    )

    # ── Inspect results ────────────────────────────────────────
    print("\n" + "="*50)
    print("PIPELINE RESULTS")
    print("="*50)

    print(f"\nDisease:      {result.disease}")
    print(f"Run ID:       {result.run_id}")
    print(f"Duration:     {result.duration_seconds:.1f}s")
    print(f"Tool calls:   {result.total_tool_calls}")
    print(f"\nDeliverable:  {result.deliverable_path}")
    print(f"Audit trail:  {result.audit_trail_path}")
    print(f"Audit JSON:   {result.audit_json_path}")

    if result.artifact_paths:
        print(f"\nArtifacts:")
        for p in result.artifact_paths:
            print(f"  • {p}")

    # ── Show phase-level confidence from Pass 2 ────────────────
    phases = result.pass2_json.get("phases", [])
    if phases:
        print(f"\nPhase confidence (from Pass 2 verification):")
        for phase in phases:
            conf = phase.get("confidence", "N/A")
            name = phase.get("phase_id", "unknown").replace("_", " ").title()
            emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🟠", "UNSUPPORTED": "🔴"}.get(conf, "⚪")
            print(f"  {emoji} {name}: {conf}")
            if phase.get("gaps"):
                for gap in phase["gaps"][:2]:
                    print(f"      ↳ Gap: {gap[:80]}")


if __name__ == "__main__":
    main()
