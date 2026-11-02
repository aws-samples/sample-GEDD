"""Step 2b: frontier baselines on the same 500 test documents, same prompt, temperature 0 (OpenRouter)."""
import asyncio
import sys

import dl_common as d

if __name__ == "__main__":
    for tag in sys.argv[1:] or ["gemini4", "opus55", "gpt61"]:
        asyncio.run(d.eval_model(tag, tag, concurrency=8))
