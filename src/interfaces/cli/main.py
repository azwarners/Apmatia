import sys
from src.api.internal.prompt_LLM import prompt_llm

def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    print(prompt_llm(prompt))

if __name__ == "__main__":
    main()
