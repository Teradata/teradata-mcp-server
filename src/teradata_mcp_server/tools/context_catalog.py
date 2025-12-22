"""
This module manages the context catalog used to support progressive disclosure of tools, documentation and instructions in the MCP server.
It allows:
 - dynamic registration and retrieval of tools.
 - execution of tools by name with arguments.
 - searching for tools based on keywords.
 - searching for documentation snippets based on keywords.
"""

ContextCatalog = None  # Placeholder for the actual ContextCatalog implementation

class Tool:
    """
    Represents a tool with its name, documentation and function.
    """    
    def __init__(self, name, func):
        self.name = name
        self.func = func


class ContextCatalog:
    def __init__(self):
        self.tools = {} # Collection of registered tools
        self.docs = {}  # Collection of documentation snippets

    def register_tool(self, tool_func):
        """
        Register a tool function in the context catalog.
        tool_func: The function to register as a tool. 
        Its name and signature are extracted for search and documentation.
        """
        tool_name = tool_func.__name__
        tool_doc = tool_func.__doc__ or "No description available."
        
    def get_tool(self, tool_name):
        return self.tools.get(tool_name)

    def search_tools(self, keyword):
        return [name for name in self.tools if keyword.lower() in name.lower()]

    def register_doc(self, doc_name, doc_content):
        """
            Register a documentation snippet in the context catalog.
            doc_name: The name/key for the documentation snippet.
            doc_content: The content of the documentation snippet.
        """
        self.docs[doc_name] = doc_content

    def get_doc(self, doc_name):
        return self.docs.get(doc_name)

    def search_docs(self, keyword):
        return [name for name in self.docs if keyword.lower() in name.lower()]
