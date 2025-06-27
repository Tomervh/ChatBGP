# ChatBGP - Intelligent BGP Analysis System

ChatBGP is a comprehensive system for analyzing BGP routing data using LLM-powered natural language queries and heuristic analysis.

## Features

- **Natural language queries**: Ask questions about BGP in plain English
- **Heuristic analysis**: Automated detection of routing anomalies and potential hijacks
- **Static document knowledge base**: Access to BGP RFCs and technical documentation
- **Live BGP data**: Query current routing state (requires BGP RIB data setup)
- **Historical analysis**: Track routing changes over time
- **RPKI & IRR validation**: Cross-reference routing data with authoritative sources

## Quick Start

### Installation

```bash
git clone 
cd chatbgp_clean
pip install -e .

# Set up environment variables (create .env file with OPENAI_API_KEY)
```

### Basic Usage

```python
from chatbgp import ChatBGPRouter, ChatBGPConfig

# Initialize with default settings
config = ChatBGPConfig(verbose=True)
router = ChatBGPRouter(config)

# Ask a question
result = router.query("What is BGP route flapping?")
print(result)
```

## Architecture

```
chatbgp/
├── router.py              # Main orchestration component
├── extractors/           # Entity extraction (regex & LLM)
├── retrievers/           # Document retrieval
├── analyzers/            # Heuristic analysis modules
├── chains/               # LLM response generation
└── utils/                # BGP data processing & external APIs
```

## Data Requirements

**Note**: This repository contains the core system code. Additional data files are required:

1. **Static documents** (included): BGP RFCs in `data/rfc_documents/`
2. **BGP RIB data** (not included): MRT RIB dumps for live BGP queries
3. **Radix trees** (not included): Built from RIB data for fast prefix lookups
4. **Vectorstore** (not included): Generated from documents for semantic search

See `data/README.md` for setup instructions and data sources.

## Configuration

Key configuration options in `ChatBGPConfig`:

- `entity_extractor`: "llm" or "regex" for entity extraction
- `model_name`: LLM model (default: "gpt-4.1-mini")
- `verbose`: Enable detailed logging

## Query types

1. **Documentation**: Questions about BGP concepts and RFCs
2. **Live BGP state**: Current routing for specific prefixes/IPs (requires data setup)
3. **Historical analysis**: Routing changes over time (requires data setup)
4. **RPKI/IRR validation**: Route authorization verification

## Dependencies

Core dependencies include:
- `langchain` and `openai` for LLM integration
- `pybgpstream` for BGP data processing (requires data setup)
- `chromadb` for document vectorstore
- `duckdb` for historical data storage

See `requirements.txt` for complete list.

## Notes for Thesis/Research Use

- This is a research prototype demonstrating BGP analysis with LLMs
- Full functionality requires additional BGP data sources (RIB dumps, etc.)
- Designed for academic and research purposes
- See evaluation scripts in `tests/evaluation/` for performance testing
