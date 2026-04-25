from agent.agent_executor import run_agent

question = "What information exists about employees?"

response = run_agent(question)

print("\n✅ AGENT RESPONSE:\n")
print(response)