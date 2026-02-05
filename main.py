from dotenv import load_dotenv
import os

def main():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        print("✅ Environment variable loaded successfully")
    else:
        print("❌ OPENAI_API_KEY not found")

if __name__ == "__main__":
    main()
