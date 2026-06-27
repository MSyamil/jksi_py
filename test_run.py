import os
import traceback
from test_agent import TestAgent
from config import Config

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

print("Config.GEMINI_API_KEY:", Config.GEMINI_API_KEY[:10] + "..." if Config.GEMINI_API_KEY else "None")
print("Config.DEFAULT_PROVIDER:", Config.DEFAULT_PROVIDER)
print("Config.DEFAULT_MODEL:", Config.DEFAULT_MODEL)

agent = TestAgent()
goal = "Login dengan standard_user, cari ransel (backpack), tambahkan ke keranjang, dan lakukan checkout sampai selesai."

print("\nRunning Autonomous Test...")
try:
    result = agent.run_autonomous_test(goal=goal)
    print("\nTest Result:")
    print("Success:", result["success"])
    print("Message:", result["message"])
    print("Steps Executed:", len(result["steps"]))
except Exception as e:
    print("\nCrash Error:")
    traceback.print_exc()
