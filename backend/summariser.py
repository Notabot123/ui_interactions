import os
from typing import List
from dotenv import load_dotenv
from models import InteractionEvent

load_dotenv()


def compact_timeline(events: List[InteractionEvent], limit: int = 120) -> str:
    lines = []
    for e in events[-limit:]:
        label = e.element_label or e.element_id
        component = f" component={e.component_id}" if e.component_id else ""
        value = f" value={e.value[:40]}" if e.value else ""
        lines.append(f"{e.event_type.upper()} {label}{component}{value}")
    return "\n".join(lines)


def mock_summary(events: List[InteractionEvent]) -> str:
    searches = [e for e in events if e.element_id == "tree-search"]
    tree_clicks = [e for e in events if "tree-item" in e.element_id]
    form_events = [e for e in events if e.event_type in {"input", "change"}]
    hovers = [e for e in events if e.event_type == "hover"]
    return f"""Session overview:\nThe user generated {len(events)} tracked interactions. They used search {len(searches)} times, selected tree items {len(tree_clicks)} times, interacted with form controls {len(form_events)} times, and produced {len(hovers)} hover signals.\n\nObserved friction:\n- Heavy search usage may indicate that the component tree is too dense or that common items are difficult to discover.\n- Repeated tree selection and hover activity can indicate exploration before committing to an action.\n- Form interaction after component selection suggests the main workflow combines navigation, inspection, and annotation.\n\nUX recommendations:\n- Add quick actions such as “Open Diagram” and “Maintenance History” directly to search results.\n- Consider pinning recently viewed components above the tree.\n- Surface likely next actions in the component viewer once a component is selected.\n- Log longer sessions over time and replace the heuristic predictor with an LSTM or Transformer sequence model once enough labelled behaviour exists.\n"""


def summarise_with_openai(events: List[InteractionEvent]) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        return mock_summary(events), "mock-summary"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        timeline = compact_timeline(events)
        prompt = f"""
You are a UX analytics assistant for complex engineering software.
Analyse this user interaction session and return concise, actionable findings.

Focus on:
- signs of confusion or inefficient navigation
- discoverability issues
- likely user intent
- UI improvement recommendations
- whether live next-action prediction would be useful

Interaction timeline:\n{timeline}
""".strip()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You write concise UX research findings for engineering software teams."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or mock_summary(events), model
    except Exception as exc:
        return mock_summary(events) + f"\n\nOpenAI fallback note: {exc}", "mock-summary-fallback"
