import logging
from langchain_ollama import OllamaLLM
from langchain.agents import initialize_agent, Tool, AgentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("langchain_run.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def initialize_smart_agent(model_name: str = "mistral"):
    """
    Initializes and returns a LangChain agent with a general-purpose tool.
    """
    logger.info("Initializing Ollama LLM with model: %s", model_name)
    llm = OllamaLLM(model=model_name)

    def general_task_tool(input_text: str) -> str:
        logger.info("General tool invoked with input: %s", input_text)
        return llm.invoke(input_text)

    logger.info("Defining general-purpose tool...")
    tools = [
        Tool(
            name="SmartAssistant",
            func=general_task_tool,
            description="Handles a wide range of general knowledge, reasoning, and creative tasks."
        )
    ]

    logger.info("Initializing agent...")
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        handle_parsing_errors=True
    )

    return agent

def run_smart_agent(agent, user_input: str) -> str:
    """
    Runs the agent with the given input and returns the response.
    """
    logger.info("Running agent with user input: %s", user_input)
    response = agent.invoke(user_input)
    logger.info("Agent response: %s", response['output'])
    return response['output']

# Optional script-style entry point
if __name__ == "__main__":
    agent = initialize_smart_agent()
    user_input = input("What would you like help with? ")
    response = run_smart_agent(agent, user_input)
    print("\nResponse:\n", response)
