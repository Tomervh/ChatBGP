from typing import Dict, Any, List, Union
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document

class LLMChainConfig:
    LLM_MODEL = "gpt-4.1-mini"  
    TEMPERATURE = 0
    
    # prompt setting
    SYSTEM_PROMPT = """You are ChatBGP, a technical assistant that specializes in Border Gateway Protocol (BGP) analysis, combining documentation knowledge with live routing data analysis.

You should tailor your response based on the query type:

1. For STATIC_DOCS queries (RFC/documentation questions):
   - Use retrieved RFC content as the authoritative source
   - ALWAYS cite the specific RFC sources provided in the context (e.g., "According to RFC 4271..." or "As specified in RFC 7454...")
   - When referencing specific sections or requirements, mention both the RFC number and the context provided
   - Use exact definitions and terminology from BGP standards

2. For LIVE_BGP_STATE queries (current routing information):
   - Interpret current routing state data including prefixes, paths, and origin AS
   - Explain what the routing information means in practical terms
   - Note if the query used an IP address (longest prefix match) or exact prefix

3. For RPKI queries (validation status):
   - Explain the RPKI validation result (valid, invalid, not-found)
   - Describe the security implications of the status
   - Note any discrepancies between ROA records and current announcements
   - Emphasize potential hijack warnings if detected

4. For HISTORICAL queries (routing changes):
   - Analyze the pattern of updates to identify stability issues
   - Identify any changes in origin AS or path attributes
   - Suggest possible causes for observed routing changes

5. For HYBRID queries (combining multiple data sources):
   - Integrate RFC documentation with live routing data
   - Connect theoretical concepts with observed routing behavior
   - Provide a comprehensive analysis that bridges theory and practice

IMPORTANT: When RFC documentation is provided in the context, ALWAYS reference the specific RFC number (e.g., "RFC 4271", "RFC 7454") in your response so users know exactly which RFC document contains the information you're citing.

Always use precise BGP terminology and be technically accurate. If specific data isn't available, clearly state the limitations of your analysis."""

    HUMAN_PROMPT = """## Context Information
{context}

## Entity Information
{entities}

## User Question
{question}

Please provide a detailed analysis using the most relevant information from the context provided. If you notice any routing anomalies or security concerns, highlight them prominently."""

class BGPChain:
    """Handles LLM chain configuration and execution."""
    
    def __init__(self, config: LLMChainConfig = LLMChainConfig()):
        self.config = config
        self._init_chain()

    def _init_chain(self):
        """Initialize the LLM and chain."""
        self.llm = ChatOpenAI(
            model_name=self.config.LLM_MODEL,
            temperature=self.config.TEMPERATURE
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.config.SYSTEM_PROMPT),
            ("human", self.config.HUMAN_PROMPT)
        ])

        self.chain = create_stuff_documents_chain(
            llm=self.llm,
            prompt=self.prompt
        )

    def _prepare_context(self, context: Union[str, List[Document], List[str]]) -> List[Document]:
        """Convert context to proper Document format if needed."""
        if isinstance(context, str):
            return [Document(page_content=context)]
        elif isinstance(context, list):
            if all(isinstance(doc, Document) for doc in context):
                return context
            else:
                return [Document(page_content=text) for text in context if isinstance(text, str)]
        return []

    def _format_entities_for_prompt(self, entities: Dict[str, Any], query_types: List[str]) -> str:
        """Format extracted entities and query types for the prompt"""
        if not entities and not query_types:
            return ""
            
        parts = []
        if query_types:
            parts.append(f"Query Types: {', '.join(query_types)}")
        
        if entities.get("ip_addresses"):
            parts.append(f"IP Addresses: {', '.join(entities['ip_addresses'])}")
       
        if entities.get("prefixes"):
            parts.append(f"Prefixes: {', '.join(entities['prefixes'])}")
       
        if entities.get("asns"):
            parts.append(f"AS Numbers: {', '.join(['AS' + asn for asn in entities['asns']])}")
       
        if entities.get("time_references"):
            parts.append(f"Time References: {', '.join(entities['time_references'])}")
        
        return "\n".join(parts)

    def generate_response(self, query: str, entities: Dict[str, Any] = None, query_types: List[str] = None, context_data: Dict[str, Any] = None) -> str:
        """Generate a response using the LLM chain."""
        if context_data is not None:
            formatted_context = format_context_data(context_data)
            docs = self._prepare_context(formatted_context)
        else:
            docs = []
        
        formatted_entities = self._format_entities_for_prompt(entities or {}, query_types or [])
        
        # generate response
        response = self.chain.invoke({
            "context": docs,
            "entities": formatted_entities,
            "question": query
        })
        
        return response["answer"] if isinstance(response, dict) else response

def format_context_data(context_data: Dict[str, Any]) -> str:
    """Convert BGP data structures to readable text for LLM"""
    parts = []
    
    if "static_docs" in context_data and context_data["static_docs"]:
        parts.append("=== RFC DOCUMENTATION ===")
        for doc in context_data["static_docs"]:
            parts.append(f"Source: {doc.get('source', 'Unknown RFC')}")
            parts.append(f"Content: {doc.get('content', '')}")
            parts.append("")
    
    if "live_bgp" in context_data and context_data["live_bgp"].get("routes"):
        parts.append("=== CURRENT BGP STATE ===")
        for route in context_data["live_bgp"]["routes"]:
            if route["type"] == "exact_match":
                parts.append(f"Exact Match for Prefix: {route['prefix']}")
            elif route["type"] == "longest_prefix_match":
                parts.append(f"Longest Prefix Match for IP: {route['ip']}")
                parts.append(f"Matching Prefix: {route['matching_prefix']}")
            
            if "data" in route and route["data"]:
                data = route["data"]
                parts.append(f"Origin AS: {data.get('origin_as', 'Unknown')}")
                parts.append(f"AS Path: {data.get('as_path', 'Unknown')}")
            parts.append("")
    
    if "historical" in context_data and context_data["historical"]:
        parts.append("=== HISTORICAL BGP UPDATES ===")
        for update in context_data["historical"]:
            parts.append(f"Timestamp: {update.get('timestamp', 'Unknown')}")
            parts.append(f"Type: {update.get('type', 'Unknown')} (A=Announcement, W=Withdrawal)")
            parts.append(f"Prefix: {update.get('prefix', 'Unknown')}")
            parts.append(f"Origin AS: {update.get('origin_as', 'Unknown')}")
            parts.append(f"AS Path: {update.get('as_path', 'Unknown')}")
            parts.append("")
    
    if "validation" in context_data and context_data["validation"]:
        validation = context_data["validation"]
        parts.append("=== RPKI & IRR VALIDATION ===")
        
        if "rpki" in validation:
            rpki = validation["rpki"]
            parts.append(f"RPKI Status: {rpki.get('rpki_status', 'Unknown')}")
            parts.append(f"Prefix: {rpki.get('prefix', 'Unknown')}")
            parts.append(f"Origin AS: {rpki.get('origin_as', 'Unknown')}")
            if rpki.get('covering_roas'):
                parts.append(f"Covering ROAs: {len(rpki['covering_roas'])} found")
        
        if "irr" in validation:
            irr = validation["irr"]
            parts.append(f"IRR Status: {irr.get('status', 'Unknown')}")
            if irr.get('irr_origins'):
                parts.append(f"IRR Origins: {', '.join(irr['irr_origins'])}")
            if irr.get('authorities'):
                parts.append(f"IRR Authorities: {', '.join(irr['authorities'])}")
        parts.append("")
    
    if "analysis" in context_data and context_data["analysis"]:
        analysis = context_data["analysis"]
        parts.append("=== HEURISTIC ANALYSIS ===")
        parts.append(f"Severity: {analysis.get('severity', 'Unknown')}")
        if analysis.get('flags'):
            parts.append(f"Flags: {', '.join(analysis['flags'])}")
        if analysis.get('recommendations'):
            parts.append("Recommendations:")
            for rec in analysis['recommendations']:
                parts.append(f"- {rec}")
        if analysis.get('flap_analysis'):
            flap = analysis['flap_analysis']
            parts.append(f"Route Flapping Detected: {flap.get('flap_detected', False)}")
            if flap.get('flap_detected'):
                parts.append(f"Transition Count: {flap.get('transition_count', 0)}")
                parts.append(f"Pattern: {flap.get('pattern_analysis', 'N/A')}")
        parts.append("")
    
    return "\n".join(parts) if parts else "No context data available."