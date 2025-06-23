
# test_openai.py
import openai
import os
from dotenv import load_dotenv


print("Starting OpenAI test...")

# Load environment variables
load_dotenv()
print("Loaded .env file")

# Set API key from environment variable
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def test_openai_connection():
    try:
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "who won the superbowl in 2011'"}
            ],
            max_tokens=50
        )
        
        print("OpenAI connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"OpenAI connection failed: {e}")
        return False

if __name__ == "__main__":
    test_openai_connection()