# Team routing prompt — OneTyler Cloud Living

The live `system_prompt` on the team. Because `routing_rules` is `null`, this text **is**
the router: it is the only thing deciding which sub-agent answers a question.

Team id: `e92bd437-cb84-4e18-88e6-757370b39c90`

## Current

```text
For all questions related to Identity, use the "Tyler Identity Implementation Assistant" agent
For all questions related to Ops Center, use the "Ops Center" agent
For all questions related to Support Access Center, use the "Support Access Center" agent
For all other questions, use the "General Blueprint Docs" agent
```
