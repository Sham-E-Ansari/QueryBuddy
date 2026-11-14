from openai import APIStatusError, OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODELS


def ask_with_fallback(messages):
    """Try each configured model in order until one answers."""
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    last_error = None

    for model in LLM_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=LLM_MAX_TOKENS,
                messages=messages,
            )
            text = response.choices[0].message.content
            # some free models return an empty reply, treat that as a miss
            if text and text.strip():
                return text.strip()
            last_error = f"{model} returned an empty reply"
        except APIStatusError as error:
            # 429 = rate limited, 5xx/404 = model down or gone: try the next one
            if error.status_code in (404, 429) or error.status_code >= 500:
                last_error = error
                continue
            raise

    raise RuntimeError(f"All models are busy or unavailable. Last error: {last_error}")
