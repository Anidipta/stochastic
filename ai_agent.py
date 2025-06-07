import google.generativeai as genai
import arxiv
from arxiv import Client, Search, SortCriterion
import streamlit as st
import json
import logging
from typing import List, Dict, Any, Optional
import re
from document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseAIAgent:
    """Enterprise-ready AI agent with document Q&A and ArXiv integration."""
    
    def __init__(self, api_key: str):
        """
        Initialize the AI agent with Gemini API.
        
        Args:
            api_key (str): Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.doc_processor = DocumentProcessor()
        self.arxiv_client = Client()
        self.conversation_history = []
        
    def query_documents(self, query: str, documents: Dict[str, Dict[str, Any]], 
                       query_type: str = "general") -> str:
        """
        Query processed documents using Gemini AI.
        
        Args:
            query (str): User query
            documents (Dict): Processed document data
            query_type (str): Type of query (general, summary, extraction)
            
        Returns:
            str: AI-generated response
        """
        try:
            # Prepare context from documents
            context = self._prepare_document_context(documents, query)
            
            # Create specialized prompt based on query type
            prompt = self._create_prompt(query, context, query_type)
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            # Store in conversation history
            self._add_to_history(query, response.text)
            
            logger.info(f"Successfully processed query: {query[:50]}...")
            return response.text
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    def search_arxiv_papers(self, description: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search ArXiv papers based on user description.
        
        Args:
            description (str): User's description of the paper they're looking for
            max_results (int): Maximum number of results to return
            
        Returns:
            List of paper information dictionaries
        """
        try:
            # Extract search terms from description using AI
            search_query = self._extract_search_terms(description)
            
            # Search ArXiv
            search = Search(
                query=search_query,
                max_results=max_results,
                sort_by=SortCriterion.Relevance
            )
            
            results = []
            for paper in self.arxiv_client.results(search):
                paper_info = {
                    'title': paper.title,
                    'authors': [author.name for author in paper.authors],
                    'summary': paper.summary,
                    'published': paper.published.strftime('%Y-%m-%d'),
                    'arxiv_id': paper.entry_id.split('/')[-1],
                    'pdf_url': paper.pdf_url,
                    'categories': paper.categories
                }
                results.append(paper_info)
            
            logger.info(f"Found {len(results)} papers for query: {description}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching ArXiv: {e}")
            return []
    
    def download_arxiv_paper(self, arxiv_id: str, download_path: str = "./downloads") -> Optional[str]:
        """
        Download a paper from ArXiv by ID.
        
        Args:
            arxiv_id (str): ArXiv paper ID
            download_path (str): Directory to save the downloaded paper
            
        Returns:
            Optional[str]: Path to downloaded file or None if failed
        """
        try:
        
            # Detect local Downloads folder based on OS
            downloads_folder = str(Path.home() / "Downloads")

            # Temp folder for arxiv to save in
            temp_dir = os.path.join(os.getcwd(), "temp_arxiv_download")
            os.makedirs(temp_dir, exist_ok=True)

            # Search and download
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(arxiv.Client().results(search))
            filename = f"{paper.title}.pdf"
            temp_pdf_path = paper.download_pdf(dirpath=temp_dir, filename=filename)

            # Move to local Downloads folder
            final_path = os.path.join(downloads_folder, filename)
            shutil.move(temp_pdf_path, final_path)

            # Cleanup temp folder
            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"✅ Paper downloaded to your Downloads folder:\n{final_path}")
            return final_path

        except Exception as e:
            print(f"❌ Failed to download paper: {e}")
            return None
    
    def _prepare_document_context(self, documents: Dict[str, Dict[str, Any]], query: str) -> str:
        """
        Prepare context from documents for AI processing.
        
        Args:
            documents (Dict): Processed document data
            query (str): User query
            
        Returns:
            str: Formatted context string
        """
        context = "Available Documents:\n\n"
        
        for doc_name, doc_data in documents.items():
            context += f"Document: {doc_name}\n"
            context += f"Pages: {doc_data.get('total_pages', 'Unknown')}\n"
            
            # Add structured content
            if doc_data.get('structured_content'):
                for section, content in doc_data['structured_content'].items():
                    if content and len(content.strip()) > 0:
                        context += f"\n{section}:\n{content[:1000]}...\n"
            
            # Add some raw text if structured content is limited
            if doc_data.get('text_content'):
                context += f"\nFull Text Sample:\n{doc_data['text_content'][:2000]}...\n"
            
            # Add table information
            if doc_data.get('tables'):
                context += f"\nTables Found: {len(doc_data['tables'])} tables\n"
            
            context += "\n" + "="*50 + "\n\n"
        
        return context
    
    def _create_prompt(self, query: str, context: str, query_type: str) -> str:
        """
        Create specialized prompts based on query type.
        
        Args:
            query (str): User query
            context (str): Document context
            query_type (str): Type of query
            
        Returns:
            str: Formatted prompt
        """
        base_prompt = f"""You are an enterprise AI assistant specialized in document analysis and research. 
        
Context from processed documents:
{context}

User Query: {query}

"""
        
        if query_type == "summary":
            return base_prompt + """
Please provide a comprehensive summary focusing on:
1. Key methodologies used
2. Main findings and results
3. Conclusions and implications
4. Any performance metrics or evaluation results

Format your response clearly with appropriate headings."""
        
        elif query_type == "extraction":
            return base_prompt + """
Please extract specific information requested by the user. Focus on:
1. Exact values, metrics, and numbers mentioned
2. Specific findings or results
3. Direct quotes when relevant
4. Table data or statistical information

Be precise and cite the specific document/section when possible."""
        
        else:  # general query
            return base_prompt + """
Please provide a helpful and accurate response based on the available documents. 
Consider the context and provide relevant information from the documents.
If the information is not available in the provided documents, please state so clearly."""
    
    def _extract_search_terms(self, description: str) -> str:
        """
        Extract relevant search terms from user description using AI.
        
        Args:
            description (str): User's description
            
        Returns:
            str: Optimized search query for ArXiv
        """
        try:
            prompt = f"""
            Extract the most relevant search terms from this description for searching academic papers on ArXiv:
            
            "{description}"
            
            Return only the key terms separated by spaces, optimized for academic paper search.
            Focus on technical terms, methodologies, and specific topics.
            """
            
            response = self.model.generate_content(prompt)
            search_terms = response.text.strip()
            
            # Clean up the response
            search_terms = re.sub(r'[^\w\s]', '', search_terms)
            return search_terms
            
        except Exception as e:
            logger.error(f"Error extracting search terms: {e}")
            # Fallback: return original description
            return description
    
    def _add_to_history(self, query: str, response: str):
        """Add query and response to conversation history."""
        self.conversation_history.append({
            'query': query,
            'response': response
            
        })
        
        # Keep only last 10 conversations to manage memory
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

def initialize_agent() -> Optional[EnterpriseAIAgent]:
    """
    Initialize the AI agent with API key from Streamlit secrets.
    
    Returns:
        Optional[EnterpriseAIAgent]: Initialized agent or None if failed
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        agent = EnterpriseAIAgent(api_key)
        return agent
    except Exception as e:
        st.error(f"Failed to initialize AI agent: {e}")
        st.info("Please ensure GEMINI_API_KEY is set in Streamlit secrets.")
        return None