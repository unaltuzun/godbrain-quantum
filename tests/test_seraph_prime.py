import asyncio
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Setup logging to see thoughts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seraph.test")

from seraph.seraph_jarvis import SeraphJarvis

async def test_seraph_prime():
    print("Initializing Seraph-Prime...")
    seraph = SeraphJarvis()
    
    # Check if mind is accessible
    print(f"Mind Core: {seraph.mind}")
    
    # Complex Reasoning Test
    test_query = "Sistemin şu anki durumunu analiz et ve eğer bir risk görüyorsan (equity düşüşü vb.) beni uyar. Ayrıca kendi zihinsel süreçlerini yansıt (reflect)."
    
    print(f"\nSending Query: {test_query}")
    print("-" * 50)
    
    try:
        response = await seraph.chat(test_query)
        print("\n[SERAPH RESPONSE]:")
        print(response)
        print("-" * 50)
        
        # Check if history is updated
        print(f"Conversation History Length: {len(seraph._conversation_history)}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_seraph_prime())
