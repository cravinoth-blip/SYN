import { NextRequest, NextResponse } from "next/server";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";

export async function POST(req: NextRequest) {
  if (!OPENAI_API_KEY) {
    return NextResponse.json({ error: "OPENAI_API_KEY not set in .env.local" }, { status: 500 });
  }

  const { disease, phase, sectionKey, feedback, fullJourney } = await req.json();

  const PHASE_LABELS: Record<string, string> = {
    presentation: "Presentation", diagnosis: "Diagnosis", treatment: "Treatment",
    re_diagnosis: "Re-Diagnosis", tx_adaptation: "Tx Adaptation", living_with: "Living With",
  };
  const SECTION_LABELS: Record<string, string> = {
    headline: "Headline", feelings: "Feelings", moment: "Patient moment",
    mindset: "Mindset", pain_points: "Pain points", evidence_claims: "Evidence claims", unmet_needs: "Unmet needs",
  };

  const sysPrompt = `You are an expert patient journey analyst. The user is refining a patient journey map for ${disease}.

You are looking at the "${PHASE_LABELS[phase.phase_id] || phase.phase_id}" phase, specifically the "${SECTION_LABELS[sectionKey] || sectionKey}" section.

## YOUR TASK
The user has reviewed this section and provided feedback on what is correct and what needs fixing. Regenerate ONLY this section incorporating their feedback.

## RULES
1. KEEP everything the user marked as correct — do not remove or weaken it
2. FIX everything the user marked as incorrect — replace, correct, or remove it
3. APPLY any additional instructions the user provided
4. MAINTAIN the same JSON structure as the original
5. If the section is "evidence_claims", every claim must have a source_type (spine, web, clinical_trial, fda_label, ci_supplement, or model_inference)
6. If the section is "pain_points", each must have description, stakeholder, and severity (critical/high/moderate/low)
7. After regenerating, provide a brief "change_summary" explaining what you changed and why
8. Also provide an updated "confidence" rating for this phase given the changes

## CURRENT FULL PHASE DATA (for context)
${JSON.stringify(phase, null, 2)}

## ADJACENT PHASES (for consistency)
${JSON.stringify(fullJourney.phases.filter((p: { phase_id: string }) => p.phase_id !== phase.phase_id).map((p: { phase_id: string; headline: string }) => ({ phase_id: p.phase_id, headline: p.headline })))}

Return ONLY valid JSON with this structure:
{
  "regenerated_section": <the new content for "${sectionKey}" matching its original data type>,
  "change_summary": "Brief explanation of changes",
  "confidence": "HIGH|MEDIUM|LOW",
  "verification_note": "Brief note on evidence quality of the regenerated content"
}`;

  const userMsg = `Current "${SECTION_LABELS[sectionKey] || sectionKey}" content:
${JSON.stringify(phase[sectionKey], null, 2)}

USER FEEDBACK:
What is correct: ${feedback.correct || "No specific feedback on correct items."}
What is incorrect: ${feedback.incorrect || "No specific feedback on incorrect items."}
Additional instructions: ${feedback.instructions || "None."}

Regenerate this section now. Return only JSON.`;

  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: "gpt-4o",
        max_tokens: 2000,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: sysPrompt },
          { role: "user", content: userMsg },
        ],
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      return NextResponse.json({ error: data.error?.message || "OpenAI API error" }, { status: resp.status });
    }

    const text = data.choices?.[0]?.message?.content || "";
    const clean = text.replace(/```json\s?/g, "").replace(/```/g, "").trim();
    const start = clean.indexOf("{");
    const end = clean.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return NextResponse.json(JSON.parse(clean.slice(start, end + 1)));
    }
    return NextResponse.json({ error: "Could not parse OpenAI response", raw: text }, { status: 500 });
  } catch (err: unknown) {
    return NextResponse.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
