# Truffle

A slack bot to find domain experts in an organization.

## System Overview

### MainApp
- FastAPI
- Route `/slack/events` -> this is a Slack event handler (slack app for my workspace) that receives messages through mentions or DMs and trigger the workflow
- Route `/ask` -> (AGENT) endpoint for asking question to the system, this is the start of the workflow
  - the slack event handler posts to `/ask`
  - TOOL(calculate_embeddings) Converts the question into a dense vector for semantic similarity search.
  - (stores the question and its embeddings into vector db)
  - TOOL(query_experts) makes query to vector db to find similar topics/messages
  - TOOL(query_experts) processes the result from vector db to rank users
  - TOOL(summarize_results) summarize the query result into a nice message
  - post answer to slack (TOOL or maybe AGENT)

### SlackExperticeTracker (FastAPI)
- Pulls slack messages from public channels (via slack api)
- Cleans and chunks messages
- Sends message batches to LLM to infer user -> topic mappings
- Calculates embeddings of topics/messages
- Saves embeddings plus metadata (user, date, ...) to vector database

### MCP-Server
- calculate_embeddings
- query_experts
- summarize_results
- (maybe) post_to_slack

### VectorDB
- qdrant
- just running
