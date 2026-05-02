"""
RAG Engine - Retrieval Augmented Generation from scratch using ChromaDB
"""
import chromadb
from chromadb.config import Settings
import hashlib
import json
import os
import time
from datetime import datetime
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, db_path: str = "./chroma_db"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Load embedding model
        logger.info("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collections
        self.knowledge_col = self._get_or_create("knowledge_base")
        self.user_memory_col = self._get_or_create("user_memory")
        self.interaction_col = self._get_or_create("interactions")
        
        # Seed knowledge base
        self._seed_knowledge_base()
        logger.info("RAG Engine initialized.")

    def _get_or_create(self, name: str):
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )

    def _seed_knowledge_base(self):
        """Seed with default knowledge if empty"""
        if self.knowledge_col.count() > 0:
            return
        
        knowledge = [
            {
                "id": "k001",
                "text": "This AI assistant is powered by advanced RAG technology. It remembers your preferences and personalizes responses based on your interaction history.",
                "category": "system"
            },
            {
                "id": "k002", 
                "text": "You can ask about a wide range of topics including science, technology, history, arts, business, health, and general knowledge.",
                "category": "capabilities"
            },
            {
                "id": "k003",
                "text": "The system tracks user preferences such as communication style, topics of interest, language complexity, and response format preferences.",
                "category": "personalization"
            },
            {
                "id": "k004",
                "text": "Voice input is supported. Click the microphone button and speak your question. The system will transcribe and process your speech.",
                "category": "features"
            },
            {
                "id": "k005",
                "text": "Your conversation history is stored securely and used to provide personalized, context-aware responses across sessions.",
                "category": "privacy"
            },
            {
                "id": "k006",
                "text": "Machine learning involves training algorithms on data to make predictions or decisions without being explicitly programmed for each task.",
                "category": "technology"
            },
            {
                "id": "k007",
                "text": "Natural language processing (NLP) enables computers to understand, interpret, and generate human language in a meaningful way.",
                "category": "technology"
            },
            {
                "id": "k008",
                "text": "Python is a versatile programming language known for its readability and extensive library ecosystem, widely used in AI, web development, and data science.",
                "category": "technology"
            },
            {
                "id": "k009",
                "text": "Retrieval Augmented Generation (RAG) combines information retrieval with language generation to produce more accurate and contextually relevant responses.",
                "category": "technology"
            },
            {
                "id": "k010",
                "text": "ChromaDB is an open-source vector database designed for AI applications, enabling efficient similarity search on embeddings.",
                "category": "technology"
            },
        ]
        
        texts = [k["text"] for k in knowledge]
        embeddings = self.embedder.encode(texts).tolist()
        
        self.knowledge_col.add(
            ids=[k["id"] for k in knowledge],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"category": k["category"]} for k in knowledge]
        )

    def add_knowledge(self, text: str, category: str = "user_added", doc_id: str = None) -> str:
        """Add document to knowledge base"""
        if not doc_id:
            doc_id = f"k_{hashlib.md5(text.encode()).hexdigest()[:8]}_{int(time.time())}"
        
        embedding = self.embedder.encode([text]).tolist()
        self.knowledge_col.add(
            ids=[doc_id],
            documents=[text],
            embeddings=embedding,
            metadatas=[{"category": category, "added_at": datetime.now().isoformat()}]
        )
        return doc_id

    def retrieve_relevant(self, query: str, n_results: int = 5, 
                          collection_name: str = "knowledge_base") -> List[Dict]:
        """Retrieve relevant documents for a query"""
        col = self.knowledge_col if collection_name == "knowledge_base" else self.user_memory_col
        
        query_embedding = self.embedder.encode([query]).tolist()
        
        try:
            results = col.query(
                query_embeddings=query_embedding,
                n_results=min(n_results, col.count()) if col.count() > 0 else 1
            )
            
            docs = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    docs.append({
                        "text": doc,
                        "distance": results["distances"][0][i] if results.get("distances") else 0,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
                    })
            return docs
        except Exception as e:
            logger.warning(f"Retrieval error: {e}")
            return []

    # ADD THESE METHODS INSIDE YOUR EXISTING RAGEngine CLASS

    def store_user_memory(self, username: str, text: str):
        username = username.lower().strip()

        embedding = self.embedder.encode([text]).tolist()

        memory_id = f"mem_{username}_{int(time.time())}"

        self.user_memory_col.add(
            ids=[memory_id],
            documents=[text],
            embeddings=embedding,
            metadatas=[{
                "user": username,
                "type": "memory"
            }]
        )

        print("✅ STORED MEMORY:", text)


    def get_user_memories(self, username: str, query: str, n_results: int = 3):
        username = username.lower().strip()

        query_embedding = self.embedder.encode([query]).tolist()

        results = self.user_memory_col.query(
            query_embeddings=query_embedding,
            n_results=n_results if self.user_memory_col.count() > 0 else 1
        )

        memories = results.get("documents", [[]])[0]

        print("🧠 RAW MEMORIES:", memories)

        # 🔥 Manual filtering (fix for your bug)
        filtered = [m for m in memories if m]

        return filtered

    def log_interaction(self, user_id: str, query: str, response: str, 
                       sentiment: str = "neutral", topics: List[str] = None):
        """Log interaction for analytics"""
        int_id = f"int_{user_id}_{int(time.time() * 1000)}"
        text = f"Query: {query} | Response summary: {response[:100]}"
        embedding = self.embedder.encode([text]).tolist()
        
        self.interaction_col.add(
            ids=[int_id],
            documents=[text],
            embeddings=embedding,
            metadatas=[{
                "user_id": user_id,
                "query": query[:500],
                "response_length": len(response),
                "sentiment": sentiment,
                "topics": json.dumps(topics or []),
                "timestamp": datetime.now().isoformat()
            }]
        )

    def get_user_analytics(self, user_id: str) -> Dict:
        """Get analytics for a specific user"""
        try:
            if self.interaction_col.count() == 0:
                return self._empty_analytics()
            
            results = self.interaction_col.get(where={"user_id": user_id})
            
            if not results["ids"]:
                return self._empty_analytics()
            
            total = len(results["ids"])
            topics_counter = {}
            sentiments = {"positive": 0, "neutral": 0, "negative": 0}
            
            for meta in results["metadatas"]:
                sentiment = meta.get("sentiment", "neutral")
                sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
                
                topics = json.loads(meta.get("topics", "[]"))
                for topic in topics:
                    topics_counter[topic] = topics_counter.get(topic, 0) + 1
            
            top_topics = sorted(topics_counter.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                "total_interactions": total,
                "sentiments": sentiments,
                "top_topics": top_topics,
                "engagement_score": min(100, total * 5)
            }
        except Exception as e:
            logger.warning(f"Analytics error: {e}")
            return self._empty_analytics()

    def get_all_analytics(self) -> Dict:
        """Get global analytics"""
        try:
            if self.interaction_col.count() == 0:
                return self._empty_analytics()
            
            results = self.interaction_col.get()
            users = set()
            topics_counter = {}
            sentiments = {"positive": 0, "neutral": 0, "negative": 0}
            daily_counts = {}
            
            for i, meta in enumerate(results["metadatas"]):
                users.add(meta.get("user_id", "unknown"))
                
                sentiment = meta.get("sentiment", "neutral")
                sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
                
                topics = json.loads(meta.get("topics", "[]"))
                for topic in topics:
                    topics_counter[topic] = topics_counter.get(topic, 0) + 1
                
                ts = meta.get("timestamp", "")
                if ts:
                    day = ts[:10]
                    daily_counts[day] = daily_counts.get(day, 0) + 1
            
            top_topics = sorted(topics_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            sorted_daily = sorted(daily_counts.items())[-14:]  # last 14 days
            
            return {
                "total_interactions": len(results["ids"]),
                "unique_users": len(users),
                "sentiments": sentiments,
                "top_topics": top_topics,
                "daily_counts": sorted_daily,
                "knowledge_docs": self.knowledge_col.count()
            }
        except Exception as e:
            logger.warning(f"All analytics error: {e}")
            return self._empty_analytics()

    def _empty_analytics(self) -> Dict:
        return {
            "total_interactions": 0,
            "unique_users": 0,
            "sentiments": {"positive": 0, "neutral": 0, "negative": 0},
            "top_topics": [],
            "daily_counts": [],
            "knowledge_docs": 0
        }