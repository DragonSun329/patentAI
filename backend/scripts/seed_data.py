"""Seed sample patent data for testing."""
import asyncio
import sys
sys.path.insert(0, "..")

from app.core.database import init_db, get_db_context
from app.models.patent import Patent
from app.services.embedding import embedding_service

SAMPLE_PATENTS = [
    {
        "title": "Machine Learning System for Natural Language Processing",
        "abstract": "A system and method for processing natural language using deep learning models. The system comprises a transformer-based neural network that processes input text sequences and generates contextual embeddings for downstream tasks such as classification, summarization, and question answering.",
        "claims": "1. A method for processing natural language comprising: receiving input text; encoding the text using a transformer neural network; generating contextual embeddings; and outputting processed results.",
        "patent_number": "US-2024-001",
        "applicant": "AI Research Corp",
        "classification": "G06F40/20"
    },
    {
        "title": "Distributed Computing System for Large-Scale Data Processing",
        "abstract": "A distributed computing architecture for processing large-scale datasets across multiple computing nodes. The system utilizes a novel load balancing algorithm and fault-tolerant data replication strategy to ensure high availability and performance.",
        "claims": "1. A distributed computing system comprising: multiple computing nodes; a load balancer; a data replication module; wherein the system processes data in parallel across nodes.",
        "patent_number": "US-2024-002",
        "applicant": "Cloud Systems Inc",
        "classification": "G06F9/50"
    },
    {
        "title": "Computer Vision System for Object Detection and Tracking",
        "abstract": "An advanced computer vision system utilizing convolutional neural networks for real-time object detection and tracking in video streams. The system employs a multi-scale feature pyramid network for detecting objects of varying sizes.",
        "claims": "1. A computer vision method comprising: receiving video input; processing frames through a CNN; detecting objects using feature pyramids; tracking detected objects across frames.",
        "patent_number": "US-2024-003",
        "applicant": "Vision AI Labs",
        "classification": "G06V10/82"
    },
    {
        "title": "Blockchain-Based Secure Transaction System",
        "abstract": "A decentralized transaction system leveraging blockchain technology for secure and transparent financial transactions. The system implements a novel consensus mechanism that reduces energy consumption while maintaining security.",
        "claims": "1. A blockchain transaction system comprising: distributed ledger; consensus module; cryptographic verification; wherein transactions are immutably recorded.",
        "patent_number": "US-2024-004",
        "applicant": "FinTech Solutions",
        "classification": "G06Q20/38"
    },
    {
        "title": "Autonomous Vehicle Navigation Using Sensor Fusion",
        "abstract": "A navigation system for autonomous vehicles that fuses data from multiple sensors including LiDAR, cameras, and radar to create a comprehensive environmental model. The system uses deep reinforcement learning for path planning.",
        "claims": "1. An autonomous navigation method comprising: collecting sensor data; fusing multi-modal inputs; generating environmental model; computing optimal path using reinforcement learning.",
        "patent_number": "US-2024-005",
        "applicant": "AutoDrive Technologies",
        "classification": "G05D1/02"
    },
]


async def seed():
    """Seed the database with sample patents."""
    print("Initializing database...")
    await init_db()
    
    async with get_db_context() as session:
        for i, patent_data in enumerate(SAMPLE_PATENTS):
            print(f"Processing patent {i+1}/{len(SAMPLE_PATENTS)}: {patent_data['title'][:50]}...")
            
            # Generate embedding
            embedding = await embedding_service.embed_patent(
                patent_data["title"],
                patent_data["abstract"],
                patent_data.get("claims")
            )
            
            # Create patent
            patent = Patent(
                id=f"sample-{i+1:03d}",
                title=patent_data["title"],
                abstract=patent_data["abstract"],
                claims=patent_data.get("claims"),
                patent_number=patent_data.get("patent_number"),
                applicant=patent_data.get("applicant"),
                classification=patent_data.get("classification"),
                embedding=embedding
            )
            
            session.add(patent)
        
        await session.commit()
        print(f"✅ Seeded {len(SAMPLE_PATENTS)} patents successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
