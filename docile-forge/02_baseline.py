"""Step 2: baseline GLM 5.3 Flash on the locked 500-document test set (plain prompt, temperature 0).

Default images are 1,600 px (tag "glm"); with DOCILE_MAX_SIDE=1344 the tag is "glm_1344", matching the fine-tune's scoring.
"""
import asyncio

import dl_common as d

if __name__ == "__main__":
    tag = "glm" if d.MAX_SIDE == 1600 else f"glm_{d.MAX_SIDE}"
    asyncio.run(d.eval_model("glm", tag, concurrency=12))
