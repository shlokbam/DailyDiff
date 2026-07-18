# DailyDiff — 2026-07-18
*We scan the noise. Five things survive.*

---

## 👀 KEEP AN EYE ON THIS: Nous Research Releases Hermes Agent

**What Happened:** Nous Research has open-sourced hermes-agent, an agentic framework designed to transition AI agents from static, prompt-based wrappers into stateful, self-improving systems. It features a continuous learning loop that dynamically creates skills and persists user context across sessions.

**Why It Matters:** Traditional agents are stateless and struggle to retain long-term context or adapt without manual prompt engineering. Hermes Agent embeds memory and skill creation directly into the runtime, allowing agents to evolve on minimal, low-cost infrastructure.

**Who Cares:** AI engineers, agent developers, and LLM application architects building personalized or autonomous digital assistants.

**Source:** [https://github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

**Verdict:** `WATCH` | **Confidence:** `88%`

---

## 🧠 RESEARCH IDEA: RxBrain: Embodied AI with Joint Language-Visual Imagination

**What Happened:** Researchers have introduced Hy-Embodied-RxBrain, an embodied cognition foundation model that unifies textual task planning and visual world-state prediction into a single Mixture-of-Transformers sequence.

**Why It Matters:** Unlike standard vision-language models that only describe scenes, RxBrain allows robots to 'imagine' physical subgoals and predict future states. This enables continuous action generation without relying on massive, pre-existing robot action datasets.

**Who Cares:** Robotics engineers, embodied AI researchers, and autonomous agent developers.

**Source:** [https://huggingface.co/papers/2607.14187](https://huggingface.co/papers/2607.14187)

**Verdict:** `READ` | **Confidence:** `82%`

---

## 🔥 WORTH KNOWING: LongStraw: Million-Token RL Training on a Fixed GPU Budget

**What Happened:** A new training method called LongStraw enables million-token Group Relative Policy Optimization (GRPO) post-training on a fixed GPU budget, bridging the gap between long-context inference and RL training limits.

**Why It Matters:** Standard RL post-training is typically bottlenecked at 256K tokens due to extreme memory overhead. LongStraw decouples prompt evaluation from autograd and replays response branches sequentially, drastically reducing memory usage so developers can train long-horizon agents without massive clusters.

**Who Cares:** LLM infrastructure engineers, reinforcement learning researchers, and platform teams optimizing GPU utilization.

**Source:** [https://huggingface.co/papers/2607.14952](https://huggingface.co/papers/2607.14952)

**Verdict:** `WATCH` | **Confidence:** `80%`

---

