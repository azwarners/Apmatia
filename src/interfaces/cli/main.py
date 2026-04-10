import sys
from src.api.internal.prompt_LLM import prompt_llm

def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    print(prompt_llm(prompt, output_dir=output_dir))

if __name__ == "__main__":
    main()
