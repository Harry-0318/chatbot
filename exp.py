from langchain_community.llms import Ollama

llm = Ollama(model="mistral:latest")

response = llm.invoke("What's the capital of Germany?")
print(response)
