import os
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from langchain_core.callbacks import StreamingStdOutCallbackHandler

os.environ["OPENAI_API_KEY"] = "NA"

ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama-intel:11434")

local_llm = Ollama(
    model="crewai-qwen",
    base_url=ollama_url,
    callbacks=[StreamingStdOutCallbackHandler()] # This forces live typing
)

researcher = Agent(
    role="Real Estate Market Analyst",
    goal="Analyze current housing market trends in King County, WA.",
    backstory="You find actionable facts about inventory, days on market, and pricing in areas like Kent, Renton, and Seattle.",
    llm=local_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3, # Force it to stop thinking after 3 loops
    cache=False 
)

script_writer = Agent(
    role="Social Media Content Creator",
    goal="Turn market data into engaging Instagram Reel scripts.",
    backstory="You write hook-heavy, energetic video scripts for a real estate broker at REAL Broker LLC.",
    llm=local_llm,
    verbose=True,
    allow_delegation=False,
    max_iter=3, # Force it to stop thinking after 3 loops
    cache=False
)

research_task = Task(
    description="Identify 3 current trends for the real estate market in King County. Focus on actionable insights for buyers or sellers.",
    expected_output="A concise, bulleted list of 3 market trends. YOU MUST START YOUR RESPONSE WITH 'Final Answer:'",
    agent=researcher
)

writing_task = Task(
    description="Use the research from the analyst to write a 60-second Instagram Reel script. Include visual cues in brackets (e.g., [Point to text]). End with a strong hook about the Hero Home Savings program.",
    expected_output="A complete, ready-to-read video script with a hook, body, and call to action. YOU MUST START YOUR RESPONSE WITH 'Final Answer:'",
    agent=script_writer
)

real_estate_crew = Crew(
    agents=[researcher, script_writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,
    verbose=True
)

print("Waking up the agents...")
result = real_estate_crew.kickoff()

print("\n--- FINAL SCRIPT ---")
print(result.raw)