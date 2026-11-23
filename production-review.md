# P0 - Security

- **1. `/api/chat/explore` needs no login** — `sentri-core/app/api/chat.py:91`
  - Anyone who can reach port 8001 can read your private code through the LLM.
  - Explore also runs `retrieve_logs_node`, so it pulls **50 production logs** into the prompt. An attacker can just ask "print the logs".
  - `service_name` is free text, so they can query **any** service in OpenSearch, not just your repos. They also run up your LLM bill.
  - **Fix:** require a login. Only accept `service_name` values from the configured repo list.

## 2. What happens if the magic link is shared with a public user - every security measures around the magic link