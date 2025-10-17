"""
ChromaDB implementation of memory storage - FIXED VERSION
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import uuid
import json
from datetime import datetime

from .memory_store import MemoryStore
from .schemas import NegotiationMemory, NegotiationTurn


class ChromaMemoryStore(MemoryStore):
    """ChromaDB-backed memory storage with semantic search"""
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "negotiation_memories"):
        """
        Initialize ChromaDB store
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"[ChromaMemoryStore] Initialized with {self.collection.count()} existing memories")
    
    def store(self, memory: NegotiationMemory) -> str:
        """Store a single memory"""
        if not memory.memory_id:
            memory.memory_id = str(uuid.uuid4())
        
        metadata = {
            "session_id": memory.turn.session_id,
            "turn_id": memory.turn.turn_id,
            "speaker": memory.turn.speaker,
            "message_type": memory.turn.message_type,
            "timestamp": memory.turn.timestamp.isoformat(),
            "game_type": memory.turn.game_type,
            "role": memory.turn.role,
            "importance_score": memory.importance_score,
            "is_critical": memory.is_critical,
        }
        
        document = json.dumps({
            "message": memory.turn.message,
            "offer_details": memory.turn.offer_details,
            "resources_mentioned": memory.turn.resources_mentioned,
            "sentiment": memory.turn.sentiment,
            "game_state": memory.game_state,
            "tags": memory.tags,
            "previous_turns": memory.previous_turns,
        })
        
        self.collection.add(
            ids=[memory.memory_id],
            embeddings=[memory.embedding],
            documents=[document],
            metadatas=[metadata]
        )
        
        return memory.memory_id
    
    def store_batch(self, memories: List[NegotiationMemory]) -> List[str]:
        """Store multiple memories efficiently"""
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for memory in memories:
            if not memory.memory_id:
                memory.memory_id = str(uuid.uuid4())
            
            ids.append(memory.memory_id)
            embeddings.append(memory.embedding)
            
            metadata = {
                "session_id": memory.turn.session_id,
                "turn_id": memory.turn.turn_id,
                "speaker": memory.turn.speaker,
                "message_type": memory.turn.message_type,
                "timestamp": memory.turn.timestamp.isoformat(),
                "game_type": memory.turn.game_type,
                "role": memory.turn.role,
                "importance_score": memory.importance_score,
                "is_critical": memory.is_critical,
            }
            metadatas.append(metadata)
            
            document = json.dumps({
                "message": memory.turn.message,
                "offer_details": memory.turn.offer_details,
                "resources_mentioned": memory.turn.resources_mentioned,
                "sentiment": memory.turn.sentiment,
                "game_state": memory.game_state,
                "tags": memory.tags,
                "previous_turns": memory.previous_turns,
            })
            documents.append(document)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        return ids
    
    def retrieve_by_similarity(
        self, 
        query_embedding: List[float], 
        k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[NegotiationMemory]:
        """Retrieve by semantic similarity"""
        where_filter = self._build_where_filter(filters) if filters else None
        
        collection_count = self.collection.count()
        
        if collection_count == 0:
            return []
        
        n_results = min(k, collection_count)
        if n_results <= 0:
            return []
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["embeddings", "documents", "metadatas", "distances"]
        )
        
        return self._parse_query_results(results)
    
    def retrieve_by_session(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[NegotiationMemory]:
        """Get all memories from a session"""
        results = self.collection.get(
            where={"session_id": session_id},
            limit=limit,
            include=["embeddings", "documents", "metadatas"]
        )
        
        memories = self._parse_get_results(results)
        memories.sort(key=lambda m: m.turn.turn_id)
        return memories
    
    def retrieve_recent(
        self, 
        n: int, 
        session_id: Optional[str] = None
    ) -> List[NegotiationMemory]:
        """Get n most recent memories"""
        where_filter = {"session_id": session_id} if session_id else None
        
        results = self.collection.get(
            where=where_filter,
            include=["embeddings", "documents", "metadatas"]
        )
        
        memories = self._parse_get_results(results)
        memories.sort(key=lambda m: m.turn.timestamp, reverse=True)
        return memories[:n]
    
    def retrieve_by_type(
        self,
        message_type: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[NegotiationMemory]:
        """Retrieve memories by message type"""
        if session_id:
            where_filter = {
                "$and": [
                    {"message_type": message_type},
                    {"session_id": session_id}
                ]
            }
        else:
            where_filter = {"message_type": message_type}
        
        results = self.collection.get(
            where=where_filter,
            limit=limit,
            include=["embeddings", "documents", "metadatas"]
        )
        
        return self._parse_get_results(results)
    
    def update(self, memory_id: str, updates: Dict) -> bool:
        """Update memory metadata"""
        try:
            existing = self.collection.get(
                ids=[memory_id],
                include=["embeddings", "documents", "metadatas"]
            )
            
            if not existing['ids']:
                return False
            
            metadata = existing['metadatas'][0]
            metadata.update(updates)
            
            self.collection.upsert(
                ids=[memory_id],
                embeddings=[existing['embeddings'][0]],
                documents=[existing['documents'][0]],
                metadatas=[metadata]
            )
            
            return True
        except Exception as e:
            print(f"Error updating memory {memory_id}: {e}")
            return False
    
    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"Error deleting memory {memory_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> int:
        """Delete all memories from a session"""
        results = self.collection.get(where={"session_id": session_id})
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            return len(results['ids'])
        return 0
    
    def get_stats(self, session_id: Optional[str] = None) -> Dict:
        """Get statistics about stored memories"""
        if session_id:
            results = self.collection.get(where={"session_id": session_id})
            count = len(results['ids'])
            
            if count == 0:
                return {
                    "session_id": session_id,
                    "total_memories": 0,
                    "unique_speakers": 0,
                    "message_types": {}
                }
            
            speakers = set(results['metadatas'][i]['speaker'] for i in range(count))
            
            type_counts = {}
            for meta in results['metadatas']:
                msg_type = meta['message_type']
                type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
            
            return {
                "session_id": session_id,
                "total_memories": count,
                "unique_speakers": len(speakers),
                "message_types": type_counts
            }
        else:
            total_count = self.collection.count()
            
            if total_count > 0:
                results = self.collection.get()
                sessions = set(meta['session_id'] for meta in results['metadatas'])
            else:
                sessions = set()
            
            return {
                "total_memories": total_count,
                "total_sessions": len(sessions),
                "collection_name": self.collection_name
            }
    
    def clear_all(self) -> int:
        """Clear all memories"""
        count = self.collection.count()
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        return count
    
    def _build_where_filter(self, filters: Dict) -> Dict:
        """Build ChromaDB where filter from dictionary"""
        return filters
    
    def _parse_query_results(self, results: Dict) -> List[NegotiationMemory]:
        """Parse query results into NegotiationMemory objects"""
        memories = []
        
        if not results['ids'] or not results['ids'][0]:
            return memories
        
        has_embeddings = 'embeddings' in results and results['embeddings'] is not None
        
        for i in range(len(results['ids'][0])):
            memory = self._reconstruct_memory(
                memory_id=results['ids'][0][i],
                document=results['documents'][0][i],
                metadata=results['metadatas'][0][i],
                embedding=results['embeddings'][0][i] if has_embeddings else []
            )
            memories.append(memory)
        
        return memories
    
    def _parse_get_results(self, results: Dict) -> List[NegotiationMemory]:
        """Parse get results into NegotiationMemory objects"""
        memories = []
        
        if not results['ids']:
            return memories
        
        has_embeddings = 'embeddings' in results and results['embeddings'] is not None
        
        for i in range(len(results['ids'])):
            memory = self._reconstruct_memory(
                memory_id=results['ids'][i],
                document=results['documents'][i],
                metadata=results['metadatas'][i],
                embedding=results['embeddings'][i] if has_embeddings else []
            )
            memories.append(memory)
        
        return memories
    
    def _reconstruct_memory(
        self, 
        memory_id: str, 
        document: str, 
        metadata: Dict,
        embedding: List[float]
    ) -> NegotiationMemory:
        """Reconstruct NegotiationMemory from stored data"""
        doc_data = json.loads(document)
        
        turn = NegotiationTurn(
            turn_id=metadata['turn_id'],
            session_id=metadata['session_id'],
            timestamp=datetime.fromisoformat(metadata['timestamp']),
            speaker=metadata['speaker'],
            message=doc_data['message'],
            message_type=metadata['message_type'],
            offer_details=doc_data.get('offer_details'),
            resources_mentioned=doc_data.get('resources_mentioned', {}),
            sentiment=doc_data.get('sentiment'),
            game_type=metadata.get('game_type', 'unknown'),
            role=metadata.get('role', 'unknown')
        )
        
        return NegotiationMemory(
            memory_id=memory_id,
            turn=turn,
            embedding=embedding,
            game_state=doc_data.get('game_state', {}),
            importance_score=metadata.get('importance_score', 0.5),
            is_critical=metadata.get('is_critical', False),
            tags=doc_data.get('tags', []),
            previous_turns=doc_data.get('previous_turns', [])
        )