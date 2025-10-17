"""
Embedding generation utilities for memory system
"""
from typing import List, Union
from abc import ABC, abstractmethod
import os


class EmbeddingGenerator(ABC):
    """Abstract base class for embedding generators"""
    
    @abstractmethod
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text
        
        Args:
            text: Single string or list of strings
            
        Returns:
            Single embedding or list of embeddings
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimension of embeddings"""
        pass


class SentenceTransformerEmbedding(EmbeddingGenerator):
    """
    Local embedding generator using sentence-transformers
    Free, runs locally, good quality
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize sentence-transformer model
        
        Args:
            model_name: HuggingFace model name
                - "all-MiniLM-L6-v2": Fast, 384 dim (recommended for testing)
                - "all-mpnet-base-v2": Better quality, 768 dim
                - "multi-qa-mpnet-base-dot-v1": Optimized for Q&A
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        print(f"[SentenceTransformer] Loaded model: {model_name} (dim={self.dimension})")
    
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using sentence-transformers"""
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_tensor=False
        )
        
        embeddings_list = embeddings.tolist()
        
        return embeddings_list[0] if is_single else embeddings_list
    
    def get_dimension(self) -> int:
        """Return embedding dimension"""
        return self.dimension


class GeminiEmbedding(EmbeddingGenerator):
    """
    Google Gemini embedding generator
    Requires Gemini API key
    """
    
    def __init__(self, model: str = "models/text-embedding-004", api_key: str = None):
        """
        Initialize Gemini embeddings
        
        Args:
            model: Gemini embedding model name
            api_key: Gemini API key (or set GEMINI_API_KEY env var)
        """
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )
        
        self.model = model
        api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=api_key)
        self.dimension = 768
        
        print(f"[GeminiEmbedding] Using model: {model} (dim={self.dimension})")
    
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using Gemini API"""
        import google.generativeai as genai
        
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        embeddings = []
        for t in texts:
            result = genai.embed_content(
                model=self.model,
                content=t,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        
        return embeddings[0] if is_single else embeddings
    
    def get_dimension(self) -> int:
        """Return embedding dimension"""
        return self.dimension


class OpenAIEmbedding(EmbeddingGenerator):
    """
    OpenAI embedding generator
    Requires API key, costs money, very high quality
    """
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: str = None):
        """
        Initialize OpenAI embeddings
        
        Args:
            model: OpenAI embedding model
                - "text-embedding-3-small": 1536 dim, cheaper
                - "text-embedding-3-large": 3072 dim, better quality
                - "text-embedding-ada-002": Legacy, 1536 dim
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )
        
        self.model = model
        self.client = OpenAI(api_key=api_key)
        
        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        self.dimension = self.dimensions.get(model, 1536)
        
        print(f"[OpenAIEmbedding] Using model: {model} (dim={self.dimension})")
    
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using OpenAI API"""
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        
        embeddings = [item.embedding for item in response.data]
        
        return embeddings[0] if is_single else embeddings
    
    def get_dimension(self) -> int:
        """Return embedding dimension"""
        return self.dimension


class MockEmbedding(EmbeddingGenerator):
    """
    Mock embedding generator for testing
    Returns random vectors - DO NOT USE IN PRODUCTION
    """
    
    def __init__(self, dimension: int = 384):
        """Initialize mock embedder with specified dimension"""
        import numpy as np
        self.dimension = dimension
        self.np = np
        print(f"[MockEmbedding] WARNING: Using mock embeddings (dim={dimension})")
    
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate random embeddings (for testing only)"""
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        embeddings = []
        for _ in texts:
            vec = self.np.random.randn(self.dimension)
            vec = vec / self.np.linalg.norm(vec)
            embeddings.append(vec.tolist())
        
        return embeddings[0] if is_single else embeddings
    
    def get_dimension(self) -> int:
        """Return embedding dimension"""
        return self.dimension


def create_embedder(
    embedder_type: str = "sentence_transformer",
    model: str = None,
    **kwargs
) -> EmbeddingGenerator:
    """
    Factory function to create embedding generator
    
    Args:
        embedder_type: "sentence_transformer", "gemini", "openai", or "mock"
        model: Model name (optional, uses defaults)
        **kwargs: Additional arguments for specific embedders
        
    Returns:
        EmbeddingGenerator instance
    """
    if embedder_type == "sentence_transformer":
        model = model or "all-MiniLM-L6-v2"
        return SentenceTransformerEmbedding(model_name=model)
    
    elif embedder_type == "gemini":
        model = model or "models/text-embedding-004"
        return GeminiEmbedding(model=model, **kwargs)
    
    elif embedder_type == "openai":
        model = model or "text-embedding-3-small"
        return OpenAIEmbedding(model=model, **kwargs)
    
    elif embedder_type == "mock":
        return MockEmbedding(**kwargs)
    
    else:
        raise ValueError(
            f"Unknown embedder_type: {embedder_type}. "
            f"Choose from: sentence_transformer, gemini, openai, mock"
        )