# 03 · Autonomous Scientific Discovery
### AI 自主科研：机器能否选择真正的未知、开展实验，并因现实反馈而改变下一步？

**The scientific ambition:** An AI scientist should do more than propose attractive hypotheses or write plausible papers. It should select meaningful research frontiers, make predictions that reality can refute, learn from negative results and seek domain or laboratory capabilities only when the problem actually requires them.

Strong prior work exists: [Co-Scientist (Nature, 2026)](https://www.nature.com/articles/s41586-026-10644-y) and [The AI Scientist (Nature, 2026)](https://www.nature.com/articles/s41586-026-10265-5). The opportunities below are specific **extensions to investigate**, not claims that no AI scientist has performed useful research.

## Three concrete research opportunities / 三个具体科学缺口

### [SCI-01 · Choosing the frontier / 怎样选择真正值得攻克的科学未知？](https://github.com/flyoung588/recursive-productive-capacity/issues/11)

**What is already known:** Co-Scientist generates and refines hypotheses **given a research goal**; The AI Scientist explores computational research workflows.

**The gap:** Before hypothesis generation, can AI **choose a valuable, uncertain and testable question** from multiple competing frontier candidates—rather than pursue a question a human picked or one that merely sounds novel?

**First experiment:** In one bounded scientific domain, compare a domain expert's frontier ranking, a novelty-only heuristic, an LLM selector and an approach accounting for importance, uncertainty, cost and a feasible evaluation oracle. Use independent subsequent tests—not literary plausibility—to judge the quality of the chosen frontier. **[Explore #11](https://github.com/flyoung588/recursive-productive-capacity/issues/11)**.

*Potential collaborators:* domain scientists, scientific method, active learning, experiment design.

### [SCI-02 · Prospective validation / 独立留出与现实检验下的新颖性是否成立？](https://github.com/flyoung588/recursive-productive-capacity/issues/12)

**What is already known:** Co-Scientist's authors discuss incomplete/contradictory published evidence, scarce negative results and preliminary validation. The AI Scientist reports wrong implementations and other scientific-quality limitations.

**The gap:** Can a proposed scientific claim survive **blind, independent evaluation** when its evidence is incomplete and some observations directly contradict the initial idea?

**First experiment:** Select a safe public scientific setting with a legitimate development set and an independently withheld evaluation, declare the prediction in advance, compare to a strong simple model, then have an outside reviewer assess prediction, traceability and uncertainty. A historical holdout is **not** a newly performed physical experiment. **[Explore #12](https://github.com/flyoung588/recursive-productive-capacity/issues/12)**.

*Potential collaborators:* reproducible science, domain expertise, experimental statistics, independent reviewers.

### [SCI-03 · Failure changes the research plan / 失败反馈能否真正改变机器的下一轮科研动作？](https://github.com/flyoung588/recursive-productive-capacity/issues/13)

**What is already known:** AI Scientist systems can run search-and-experiment loops, but published work documents errors and limitations. Generating another list of hypotheses alone does not show that the next action used a real negative observation.

**The gap:** After a **genuine observed failure**, can an AI search policy select a demonstrably more informative next experiment than one that ignores the feedback or a strong conventional adaptive method?

**First experiment:** In a bounded scientific world with independent observations and a finite budget, compare **feedback-enabled**, **feedback-blind**, and **strong adaptive-search** procedures. Track the actual change in action, informativeness, cost and scientific progress. **[Explore #13](https://github.com/flyoung588/recursive-productive-capacity/issues/13)**.

*Potential collaborators:* AI for science, domain experiment owners, active learning, prospective evaluation.

## Research can generate the organization it needs

A scientific question may first require computation, then an expert's independent critique, a dataset or a physical test. **Rather than presupposing a fixed lab, we want to see whether research capability can form around the question itself**, while real scientific evidence changes both the question and the collaboration.

Existing autonomous research systems may contribute methods or evaluation material when appropriately shared; Co-Do does not need to claim ownership of those projects for this to work.

**[Discuss the scientific project](https://github.com/flyoung588/recursive-productive-capacity/issues/4) · [Browse all nine research questions](../research/OPEN_QUESTIONS.md) · [Email](mailto:flyoung588@gmail.com?subject=Co-Do%20%E2%80%94%20autonomous%20science) · [About Co-Do](../README.md)**
