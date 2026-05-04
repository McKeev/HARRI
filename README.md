# H.A.R.R.I - Head Assistant for Routing and Intelligence

This project aims to construct my own Telegram assistant.
This assistant will be able to perform various tasks, such as answering questions, providing information, and assisting with daily activities.
Here are some of the features I have in mind for H.A.R.R.I:

- Personalised assistant: H.A.R.R.I should memorize some of my engagements (such as current project, my location, etc..)
- Calendar management: H.A.R.R.I can help me schedule appointments, set reminders, and manage my google calendar.
- Task management: H.A.R.R.I can assist me in creating to-do lists (google tasks), setting deadlines, and tracking my progress on various tasks (github access).
- Financial markets: I have a project, [fin_db](https://github.com/McKeev/fin_db) that serves as my personal financial database which contains all my financial data. 
  H.A.R.R.I can access this database to monitor stocks, indices and my personal portfolio, providing me with real-time updates and insights.
- News and information: H.A.R.R.I can fetch the latest news, weather updates, and other relevant information based on my preferences.

## Architecture & Design Patterns

H.A.R.R.I is built using a **Supervisor/Router multi-agent architecture** powered by [Pydantic AI](https://pydantic.dev/).

### 1. The Head Agent (H.A.R.R.I)
H.A.R.R.I acts as the central router. Its primary responsibilities are:
- Maintaining the conversational state (Short-term memory) with the user over Telegram.
- Understanding user intent and maintaining context.
- Synthesizing explicit, self-contained tasks to delegate to specialized sub-agents.
- Consolidating results into a natural, conversational response back to the user.

### 2. Sub-Agents (The Workers)
Tasks are delegated to highly specialized, stateless sub-agents (e.g., Finance Agent, Schedule Agent, Task Agent). 
- **Bottom-Up Development:** Sub-agents are built and tested as standalone scripts to ensure domain-specific prompts work reliably before integration.
- **Agent Delegation:** H.A.R.R.I accesses these sub-agents via tool calls (e.g., `@harri.tool async def ask_finance_agent(...)`).
- **Synthesized Prompts:** H.A.R.R.I *never* passes raw conversation history to a sub-agent. Instead, it resolves pronouns and context (e.g., translating "How did it do?" to "Get the YTD performance of Apple") to save tokens, reduce latency, and prevent sub-agent hallucination.

### 3. Memory Management
- **Short-Term Memory (Conversation History):** Managed entirely by H.A.R.R.I passing `message_history` in its run execution loop.
- **Long-Term Memory (Facts/Preferences):** Managed through a database (e.g., SQLite/JSON) via two methods:
  - *Passive Memory:* Injecting core facts (user name, location, current projects) into H.A.R.R.I's system prompt dynamically using `RunContext` dependencies.
  - *Active Memory:* Providing H.A.R.R.I with specific tools (e.g., `save_fact`, `search_memory`) to let it dynamically write and read user preferences.

## Data Management

Data is stored in a SQL database (SQLite for simplicity).
The main table is `users` which is associated with the `User` class.
```python
class User(BaseModel):
    id: int
    telegram_id: int
    name: str = "User"
    approval_status: bool = False
    admin_status: bool = False
```

For authentication, there is also a oauth_credentials table that stores the credentials for the various APIs that H.A.R.R.I will use to perform its tasks.
The tokens are encrypted using the `cryptography` library to ensure security.
Use the following command to view the database:
```bash
harlequin path/to/database.db
```
