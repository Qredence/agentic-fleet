# Routing Evaluation Report

**Total Examples**: 19
**Agent Selection Accuracy**: 57.9%
**Execution Mode Accuracy**: 68.4%

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
