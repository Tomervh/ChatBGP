from setuptools import setup, find_packages

setup(
    name="chatbgp",
    version="1.0.0",
    description="Intelligent BGP Analysis System using LLM and heuristic analysis",
    long_description=open("README.md").read() if open("README.md") else "",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.2.1",
        "langchain-openai>=0.1.8", 
        "langchain-community>=0.2.1",
        "langchain-text-splitters>=0.2.0",
        "chromadb>=0.5.3",
        "duckdb>=0.10.3",
        "openai>=1.30.3",
        "pytricia>=1.0.2",
        "requests>=2.31.0",
        "numpy>=1.24.3",
        "pandas>=2.0.3",
        "python-dotenv>=1.0.0",
        "pybgpstream>=2.0.0", 
        "py-radix>=0.10.0",    
        "ipaddress>=1.0.23"   
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
) 