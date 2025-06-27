"""
ChatBGP - Intelligent BGP Analysis System

A comprehensive system for analyzing BGP routing data using LLM-powered
natural language queries and heuristic analysis.
"""

__version__ = "1.0.0"
__author__ = "Tomer van Houts"

from .router import ChatBGPRouter
from .models.config import ChatBGPConfig

__all__ = ['ChatBGPRouter', 'ChatBGPConfig'] 