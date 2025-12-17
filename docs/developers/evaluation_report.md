# Routing Evaluation Report

## Summary

**Total Examples**: 19
**Agent Selection Accuracy**: 57.9% (11/19 matches)
**Execution Mode Accuracy**: 68.4% (13/19 matches)

### Scope & Methodology

> **Note on Simple Task Inclusion**: These accuracy metrics include **both simple tasks** (detected by `is_simple_task()` and routed directly to LLM) **and complex tasks** requiring multi-agent coordination. Simple tasks bypass the multi-agent routing system; execution mode mismatches for simple tasks indicate detection edge cases.

### Breakdown by Task Category

| Category                                            | Count | Agent Selection Accuracy | Execution Mode Accuracy |
| --------------------------------------------------- | ----- | ------------------------ | ----------------------- |
| **Simple Tasks** (factual queries, greetings, math) | 6     | 83.3% (5/6)              | 50.0% (3/6)             |
| **Complex Tasks** (multi-step reasoning, analysis)  | 13    | 46.2% (6/13)             | 76.9% (10/13)           |
| **Overall**                                         | 19    | 57.9% (11/19)            | 68.4% (13/19)           |

### Failure Pattern Analysis

#### Simple Task Misclassifications (3 failures in execution mode)

- **False Negatives** (incorrectly routed to multi-agent when should use delegated/fast-path):
  - ID 11: "Translate 'Hello world'..." — Detected as simple (agent ✅) but predicted `parallel` mode instead of `delegated` (execution ❌)
  - ID 18: "Help me plan a birthday party..." — Complex task incorrectly detected as simple; added 'Writer' agent and predicted `parallel` mode (agent ❌, execution ❌)

#### Complex Task Misrouting (7 failures in agent selection)

- **Over-Delegation** (predicting extra agents):
  - ID 2, 5, 9, 15: Adding 'Analyst' agent when not required (fine-grained research/comparison tasks)
  - ID 4, 12, 16: Adding 'Analyst' agent to sequential workflows for verification/synthesis roles not in expected roster

- **Mode Selection Misalignment**:
  - ID 2, 5, 9, 15, 18: Predicting `sequential` mode for multi-researcher tasks that should use `parallel` or `delegated`

### Recommended Next Steps

1. **Tune Simple Task Detection**: Review `is_simple_task()` heuristics (ID 11, 18) — consider adding explicit patterns for translation/planning tasks
2. **Analyze Over-Delegation**: Profile routing decisions for IDs 2, 5, 9, 15 to understand why Analyst role is consistently added; may indicate implicit expectation in training data
3. **Execution Mode Correlation**: Investigate why agent selection accuracy (57.9%) diverges from execution mode accuracy (68.4%) — suggests mode logic is more robust than agent roster selection
4. **Validation on New Data**: Test refined routing on a holdout dataset to confirm improvements before production deployment

## Detailed Results

| ID  | Task                                                  | Expected Agents           | Predicted Agents                        | Match | Expected Mode | Predicted Mode | Match |
| --- | ----------------------------------------------------- | ------------------------- | --------------------------------------- | ----- | ------------- | -------------- | ----- |
| 1   | Write a haiku about a robot dreaming....              | ['Writer']                | ['Writer']                              | ✅    | delegated     | delegated      | ✅    |
| 2   | Find the latest stock price of Nvidia and explain ... | ['Researcher']            | ['Researcher', 'Analyst']               | ❌    | delegated     | sequential     | ❌    |
| 3   | Calculate the 50th Fibonacci number using Python....  | ['Coder']                 | ['Coder']                               | ✅    | delegated     | delegated      | ✅    |
| 4   | Research the benefits of Mediterranean diet and th... | ['Writer', 'Researcher']  | ['Writer', 'Researcher', 'Analyst']     | ❌    | sequential    | sequential     | ✅    |
| 5   | Compare the features of iPhone 15 and Samsung S24.... | ['Researcher']            | ['Researcher', 'Analyst']               | ❌    | delegated     | sequential     | ❌    |
| 6   | Plot a graph of y = x^2 and y = x^3 to see where t... | ['Coder']                 | ['Coder']                               | ✅    | delegated     | delegated      | ✅    |
| 7   | Who won the Super Bowl in 2024?...                    | ['Researcher']            | ['Researcher']                          | ✅    | delegated     | delegated      | ✅    |
| 8   | Summarize this long email thread: [Email content..... | ['Analyst']               | ['Analyst']                             | ✅    | delegated     | delegated      | ✅    |
| 9   | Create a marketing slogan for a new coffee brand....  | ['Writer']                | ['Writer', 'Analyst']                   | ❌    | delegated     | sequential     | ❌    |
| 10  | Check if my server is running by pinging 192.168.1... | ['DevOps']                | ['DevOps']                              | ✅    | delegated     | delegated      | ✅    |
| 11  | Translate 'Hello world' to French, Spanish, and Ge... | ['Writer']                | ['Writer']                              | ✅    | delegated     | parallel       | ❌    |
| 12  | Find the average temperature in Tokyo for each mon... | ['Researcher', 'Coder']   | ['Analyst', 'Researcher', 'Coder']      | ❌    | sequential    | sequential     | ✅    |
| 13  | Explain the theory of relativity to a 5 year old....  | ['Writer']                | ['Writer']                              | ✅    | delegated     | delegated      | ✅    |
| 14  | Debug this python code snippet: def foo(): return ... | ['Coder']                 | ['Coder']                               | ✅    | delegated     | delegated      | ✅    |
| 15  | What are the top 3 restaurants in NYC and London r... | ['Researcher']            | ['Researcher', 'Analyst']               | ❌    | parallel      | sequential     | ❌    |
| 16  | Draft a legal contract for a freelance web develop... | ['LegalExpert', 'Writer'] | ['LegalExpert', 'Writer', 'Researcher'] | ❌    | sequential    | sequential     | ✅    |
| 17  | Analyze the sentiment of these 500 tweets....         | ['Analyst', 'Coder']      | ['Analyst', 'Coder']                    | ✅    | sequential    | sequential     | ✅    |
| 18  | Help me plan a birthday party for my 10 year old....  | ['Analyst']               | ['Writer', 'Analyst']                   | ❌    | delegated     | parallel       | ❌    |
| 19  | Convert this currency: 100 USD to EUR....             | ['Researcher']            | ['Researcher']                          | ✅    | delegated     | delegated      | ✅    |
