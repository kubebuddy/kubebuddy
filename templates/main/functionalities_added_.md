# Functionalities added/changed
  
## 1. Integrated Ollama as an AI Provider
  
Ollama, a **local AI provider**, has been integrated alongside **OpenAI** and **Gemini**.  
Since it does **not require an API key**, users can simply select _Ollama_ and their preferred model in **Settings**.  
Once selected, it is saved in the configuration, and you can start chatting with **Buddy AI** immediately.  
Buddy AI will respond to prompts just like with other providers.
  
---
  
## 2. Added `/change` and `/switch` Commands
  
Introduced two new commands:
  
- **/change** – Switch the current AI provider or model.
- **/switch** – Quickly toggle between previously used providers.
  
These commands allow seamless switching while chatting with **Buddy AI**.
  
---
  
## 3. API Key Configuration for OpenAI and Gemini
  
The **API Key** for both **OpenAI** and **Gemini** is now configured **only in Settings**.  
Buddy AI will **no longer ask for API keys** during the chat session.
  
---
  
## 4. Provider Configuration Check
  
If the user tries to start chatting with **Buddy AI** without configuring any **AI provider** or any **model** in settings  
Buddy AI will prompt the user to **configure them first** in the settings before proceeding.
  