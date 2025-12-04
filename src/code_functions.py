
def clean_call_transcript(inputs: dict) -> dict:
    # This is a stub function of a simple cleaning text function, not a real text cleaning process
    transcript = inputs.get("raw_transcript", "")
    # Simple cleaning: remove extra whitespace and convert to lowercase
    cleaned_transcript = ' '.join(transcript.split()).lower()
    return {"cleaned_transcript": cleaned_transcript}
