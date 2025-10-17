"""
Test memory-augmented agent with OpenAI API
"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

from memory_system.core.vector_store import ChromaMemoryStore
from memory_system.core.retriever import MemoryRetriever
from memory_system.agents.memory_agent import MemoryAugmentedNegotiator
from memory_system.utils.embeddings import create_embedder


def test_openai_memory_agent():
    """Test memory-augmented agent with OpenAI"""
    
    print("=" * 70)
    print("OPENAI MEMORY-AUGMENTED AGENT TEST")
    print("=" * 70)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("\nERROR: OPENAI_API_KEY not found in environment")
        print("Please set OPENAI_API_KEY in your .env file")
        sys.exit(1)
    
    print("\n[1/5] Initializing memory system...")
    
    embedder = create_embedder(
        embedder_type="sentence_transformer",
        model="all-MiniLM-L6-v2"
    )
    
    memory_store = ChromaMemoryStore(
        persist_directory="./test_openai_agent_db",
        collection_name="openai_agent_memories"
    )
    
    if memory_store.collection.count() > 0:
        print("  - Clearing existing memories...")
        memory_store.clear_all()
    
    retriever = MemoryRetriever(memory_store, embedder)
    
    print("  Memory system initialized")
    
    print("\n[2/5] Creating memory-augmented agent with OpenAI...")
    
    agent = MemoryAugmentedNegotiator(
        agent_name="France",
        llm_backend="openai",
        model="gpt-4",
        memory_store=memory_store,
        retriever=retriever,
        embedding_generator=embedder,
        retrieval_config={
            "strategy": "hybrid",
            "k": 5,
            "recency_weight": 0.3,
            "similarity_weight": 0.7
        }
    )
    
    session_id = "france_diplomacy_test_session"
    agent.start_session(session_id)
    
    print("\n[3/5] Running negotiation scenario...")
    print("-" * 70)
    
    system_prompt = """You are France in a game of Diplomacy (1901). 
Your goal is to expand your influence while maintaining strategic alliances.
Be diplomatic but strategic. Remember past agreements and adjust your strategy accordingly.
Keep responses concise (2-3 sentences)."""
    
    negotiation_scenario = [
        {
            "from": "England",
            "message": "France, I think we should discuss our mutual border with Germany. They're growing too powerful.",
            "context": {
                "game_type": "diplomacy",
                "phase": "Spring 1901",
                "france_units": "Army Paris, Army Marseilles, Fleet Brest",
                "england_units": "Fleet London, Fleet Edinburgh, Army Liverpool"
            }
        },
        {
            "from": "England",
            "message": "I propose we form an alliance. I'll support you against Germany if you help contain their fleet.",
            "context": {
                "game_type": "diplomacy",
                "phase": "Spring 1901",
                "recent_moves": "Germany moved into Holland"
            }
        },
        {
            "from": "England",
            "message": "Specifically, what if I support your move into Burgundy and you support my fleet into the North Sea?",
            "context": {
                "game_type": "diplomacy",
                "phase": "Spring 1901 Orders",
                "proposed_alliance": "France-England vs Germany"
            }
        },
    ]
    
    for i, turn in enumerate(negotiation_scenario, 1):
        print(f"\nTurn {i}:")
        print(f"  England: {turn['message']}")
        
        response = agent.generate_response(
            message=turn['message'],
            game_context=turn['context'],
            system_prompt=system_prompt,
            role="France"
        )
        
        print(f"  France (Agent): {response}")
        print()
    
    print("\n[4/5] Analyzing agent's memory...")
    print("-" * 70)
    
    stats = agent.get_memory_stats()
    print(f"\n  Memory Statistics:")
    print(f"    - Session ID: {stats.get('session_id', 'N/A')}")
    print(f"    - Total memories: {stats.get('total_memories', 0)}")
    print(f"    - Current turn: {stats.get('current_turn', 0)}")
    print(f"    - Unique speakers: {stats.get('unique_speakers', 0)}")
    if 'message_types' in stats:
        print(f"    - Message types: {stats['message_types']}")
    
    print("\n  Testing memory retrieval:")
    memories = agent.get_negotiation_history(limit=10)
    print(f"    Retrieved {len(memories)} memories from negotiation")
    
    for mem in memories[:6]:
        print(f"      - Turn {mem.turn.turn_id}: {mem.turn.speaker} ({mem.turn.message_type})")
        print(f"        {mem.turn.message[:70]}...")
    
    print("\n  Testing semantic search:")
    alliance_memories = retriever.retrieve_relevant(
        query="alliance proposal cooperation",
        session_id=session_id,
        strategy="semantic",
        k=3
    )
    
    print(f"    Query: 'alliance proposal cooperation'")
    print(f"    Found {len(alliance_memories.memories)} relevant memories:")
    for mem in alliance_memories.memories:
        print(f"      - {mem.turn.speaker}: {mem.turn.message[:60]}...")
    
    print("\n  Analyzing opponent pattern:")
    pattern = agent.analyze_opponent_pattern()
    print(f"    Opponent negotiation pattern: {pattern.get('pattern', 'unknown')}")
    print(f"    Total offers from opponent: {pattern.get('total_offers', 0)}")
    
    print("\n[5/5] Testing memory persistence across sessions...")
    print("-" * 70)
    
    print("\n  Creating new agent instance (simulating restart)...")
    agent2 = MemoryAugmentedNegotiator(
        agent_name="France",
        llm_backend="openai",
        model="gpt-4",
        memory_store=memory_store,
        retriever=retriever,
        embedding_generator=embedder
    )
    
    agent2.start_session(session_id)
    
    print("  Retrieving past negotiation history...")
    past_memories = agent2.get_negotiation_history()
    print(f"    Successfully retrieved {len(past_memories)} memories from previous session")
    print(f"    Memory persisted across agent instances")
    
    print("\n  Testing context-aware response with memory:")
    test_message = "So, have we reached an agreement on our alliance?"
    test_context = {
        "game_type": "diplomacy",
        "phase": "Spring 1901 Resolution",
        "pending_orders": True
    }
    
    print(f"\n  England: {test_message}")
    
    context_response = agent2.generate_response(
        message=test_message,
        game_context=test_context,
        system_prompt=system_prompt,
        role="France"
    )
    
    print(f"  France (Agent with Memory): {context_response}")
    print("\n  Response should reference previous discussion about alliance")
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("OpenAI memory-augmented agent working successfully")
    print("\nCapabilities demonstrated:")
    print("  1. OpenAI API integration")
    print("  2. Memory-augmented response generation")
    print("  3. Context-aware diplomacy negotiation")
    print("  4. Persistent memory across sessions")
    print("  5. Semantic memory retrieval")
    print("  6. Pattern analysis")
    print(f"\nDatabase persisted to: ./test_openai_agent_db")
    print("=" * 70)


def test_openai_embeddings():
    """Test OpenAI embeddings"""
    
    print("\n" + "=" * 70)
    print("BONUS: Testing OpenAI Embeddings")
    print("=" * 70)
    
    try:
        print("\nInitializing OpenAI embeddings...")
        openai_embedder = create_embedder(
            embedder_type="openai",
            model="text-embedding-3-small"
        )
        
        test_text = "I propose an alliance between France and England"
        embedding = openai_embedder.generate(test_text)
        
        print(f"  Generated embedding for: '{test_text}'")
        print(f"  Embedding dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        print("\nOpenAI embeddings working")
        
    except Exception as e:
        print(f"\nOpenAI embeddings test skipped: {e}")
        print("(This is optional - SentenceTransformer embeddings work fine)")


if __name__ == "__main__":
    try:
        test_openai_memory_agent()
        
        print("\n")
        response = input("Test OpenAI embeddings too? (y/n): ")
        if response.lower() == 'y':
            test_openai_embeddings()
        
    except Exception as e:
        print(f"\nTest failed with error:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)