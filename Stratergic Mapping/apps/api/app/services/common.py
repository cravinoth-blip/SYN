from app.models import SectionName, SourceType


SECTIONS: list[str] = [section.value for section in SectionName]

SOURCE_ORDER: list[str] = [
    SourceType.INTERNAL_UPLOAD.value,
    SourceType.PUBMED.value,
    SourceType.PMC.value,
    SourceType.CLINICAL_TRIALS.value,
    SourceType.GUIDELINE.value,
    SourceType.REGULATORY.value,
    SourceType.HTA.value,
    SourceType.EPIDEMIOLOGY.value,
    SourceType.CONGRESS.value,
    SourceType.NEWS.value,
    SourceType.ADVOCACY.value,
]


SECTION_GUIDANCE: dict[str, str] = {
    "Condition": "disease understanding, epidemiology, unmet need, diagnostics, pathways",
    "Compound": "mechanism, efficacy, safety, lifecycle, trial design, evidence caveats",
    "Context": "market, regulatory, access, policy, geography-specific divergence",
    "Company": "portfolio fit, pipeline posture, scientific reputation, strategic priorities",
    "Customer": "stakeholder mapping, HCP segmentation, patient journey, behavioral hypotheses",
    "Channel": "medical/commercial engagement, ecosystem touchpoints, influence flows",
    "Competition": "therapeutic landscape, competitor compounds, comparative evidence, timing",
}

