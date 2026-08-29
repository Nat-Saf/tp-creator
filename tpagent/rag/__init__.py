"""tpagent/rag -- retrieval profiles (SOFTWARE.md 6.8).

index.py: offline chunk + embed + upsert (one index per embedding profile).
retrieve.py: online query embed + top-k, asserting the index's recorded
embedding model. The Pinecone SDK is imported only inside this package;
every embedding call goes through the LLMClient (and thus the recorder).
"""
