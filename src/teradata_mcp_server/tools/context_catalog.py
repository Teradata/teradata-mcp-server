"""
This module manages the context catalog used to support progressive disclosure of tools, documentation and instructions in the MCP server.
It allows:
 - dynamic registration and retrieval of tools.
 - execution of tools by name with arguments.
 - searching for tools based on keywords.
 - searching for documentation snippets based on keywords.
"""

import inspect
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Set, Tuple, Any, Optional


@dataclass
class ParamInfo:
    """Information about a tool parameter."""
    type: type
    required: bool
    default: Any
    description: str


@dataclass
class ToolMetadata:
    """Rich metadata about a tool function."""
    name: str                           # e.g., "base_readQuery"
    display_name: str                   # e.g., "Read Query"
    func: Callable                      # The actual handle_ function
    description: str                    # Extracted from docstring
    parameters: Dict[str, ParamInfo]    # Name -> ParamInfo
    signature: inspect.Signature        # For validation
    category: str                       # e.g., "base", "fs", "dba"
    keywords: Set[str]                  # Indexed for search
    full_doc: str                       # Complete docstring


class ContextCatalog:
    """Central registry for progressive tool disclosure."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}  # tool_name -> ToolMetadata
        self._tools_lower: Dict[str, str] = {}  # lowercase_name -> actual_name (for exact match lookup)
        self._keyword_index: Dict[str, Set[str]] = {}  # keyword -> set of tool_names
        self._category_index: Dict[str, Set[str]] = {}  # category -> set of tool_names
        self.docs: Dict[str, str] = {}  # Collection of documentation snippets

    def register_tool(self, tool_func: Callable, category: str = None):
        """
        Register a tool function in the context catalog.

        Args:
            tool_func: The function to register as a tool.
            category: Optional category override (auto-detected from name if not provided)
        """
        metadata = self._extract_metadata(tool_func, category)

        # Store in main registry
        self._tools[metadata.name] = metadata

        # Store lowercase mapping for fast exact match lookup
        self._tools_lower[metadata.name.lower()] = metadata.name

        # Index by category
        if metadata.category not in self._category_index:
            self._category_index[metadata.category] = set()
        self._category_index[metadata.category].add(metadata.name)

        # Index by keywords
        for keyword in metadata.keywords:
            if keyword not in self._keyword_index:
                self._keyword_index[keyword] = set()
            self._keyword_index[keyword].add(metadata.name)

    def get_tool(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        Retrieve tool metadata by exact name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            ToolMetadata if found, None otherwise
        """
        return self._tools.get(tool_name)

    def get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """
        Retrieve the actual tool function by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            The tool function if found, None otherwise
        """
        metadata = self.get_tool(tool_name)
        return metadata.func if metadata else None

    def search_tools(self, query: str = "", limit: int = 10) -> Dict[str, Any]:
        """
        Search for tools by name or keywords, or list all tools.

        Three modes:
        1. Empty query: List all tool names (no details)
        2. Exact tool name match: Return full documentation with parameters
        3. Keywords: Return short summaries of matching tools

        Args:
            query: Tool name or keywords to search for (empty = list all)
            limit: Maximum number of results for approximate matches

        Returns:
            Dictionary with search results based on mode
        """
        # Mode 1: List all tools (empty query)
        if not query or not query.strip():
            return {
                "match_type": "list_all",
                "total_count": len(self._tools),
                "tools": sorted(self._tools.keys())
            }

        query_stripped = query.strip()
        query_lower = query_stripped.lower()

        # Mode 2: Exact match (O(1) dictionary lookup)
        if query_lower in self._tools_lower:
            actual_name = self._tools_lower[query_lower]
            exact_match = self._tools[actual_name]

            return {
                "match_type": "exact",
                "tool": {
                    "name": exact_match.name,
                    "category": exact_match.category,
                    "description": exact_match.description,
                    "full_documentation": exact_match.full_doc,
                    "parameters": {
                        name: {
                            "type": param.type.__name__ if hasattr(param.type, '__name__') else str(param.type),
                            "required": param.required,
                            "default": str(param.default) if param.default is not None else None,
                            "description": param.description
                        }
                        for name, param in exact_match.parameters.items()
                    }
                }
            }

        # Mode 3: Approximate match (keyword search)
        query_keywords = set(query_lower.split())
        scored_results = []

        for tool_name, metadata in self._tools.items():
            score = 0

            # Partial name match
            if query_lower in metadata.name.lower():
                score += 100

            # Category match
            if query_lower == metadata.category.lower():
                score += 75
            elif query_lower in metadata.category.lower():
                score += 50

            # Keyword matches
            matching_keywords = query_keywords & metadata.keywords
            score += len(matching_keywords) * 10

            # Description contains query
            if query_lower in metadata.description.lower():
                score += 20

            # Parameter name matches
            for param_name in metadata.parameters.keys():
                if query_lower in param_name.lower():
                    score += 15

            if score > 0:
                scored_results.append((score, metadata))

        # Sort by score and limit
        scored_results.sort(reverse=True, key=lambda x: x[0])
        top_results = scored_results[:limit]

        return {
            "match_type": "approximate",
            "results_count": len(top_results),
            "tools": [
                {
                    "name": meta.name,
                    "category": meta.category,
                    "summary": self._extract_short_summary(meta.full_doc),
                    "score": score
                }
                for score, meta in top_results
            ]
        }

    def _extract_short_summary(self, docstring: str) -> str:
        """
        Extract the first meaningful (non-blank) line from a docstring.

        Args:
            docstring: The full docstring

        Returns:
            The first non-blank line, or "No description available" if none found
        """
        if not docstring:
            return "No description available"

        lines = docstring.split('\n')
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and common section headers
            if stripped and not stripped.lower().endswith(':'):
                return stripped

        return "No description available"

    def validate_arguments(self, tool_name: str, **kwargs) -> Tuple[bool, str]:
        """
        Validate arguments against tool signature.

        Args:
            tool_name: Name of the tool to validate arguments for
            **kwargs: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        metadata = self.get_tool(tool_name)
        if not metadata:
            return False, f"Tool '{tool_name}' not found"

        # Check for missing required parameters
        missing = []
        for param_name, param_info in metadata.parameters.items():
            if param_info.required and param_name not in kwargs:
                missing.append(param_name)

        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"

        # Check for unexpected parameters
        unexpected = []
        for param_name in kwargs:
            if param_name not in metadata.parameters:
                unexpected.append(param_name)

        if unexpected:
            return False, f"Unexpected parameters: {', '.join(unexpected)}"

        return True, ""

    def get_categories(self) -> List[str]:
        """
        Get list of all tool categories.

        Returns:
            List of category names
        """
        return sorted(self._category_index.keys())

    def list_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        List all tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tools in the category
        """
        tool_names = self._category_index.get(category, set())
        return [
            {
                "name": self._tools[name].name,
                "description": self._tools[name].description,
                "parameters": {
                    pname: {
                        "type": pinfo.type.__name__ if hasattr(pinfo.type, '__name__') else str(pinfo.type),
                        "required": pinfo.required
                    }
                    for pname, pinfo in self._tools[name].parameters.items()
                }
            }
            for name in sorted(tool_names)
        ]

    def _extract_metadata(self, func: Callable, category: str = None) -> ToolMetadata:
        """
        Extract rich metadata from a handle_ function.

        Args:
            func: The tool function to extract metadata from
            category: Optional category override

        Returns:
            ToolMetadata object
        """
        # Name extraction
        raw_name = func.__name__
        if raw_name.startswith("handle_"):
            tool_name = raw_name[7:]  # Remove 'handle_' prefix
        else:
            tool_name = raw_name

        # Auto-detect category from name if not provided
        if category is None:
            category = tool_name.split('_')[0] if '_' in tool_name else 'misc'

        # Description from docstring
        full_doc = inspect.getdoc(func) or "No description available"
        description = full_doc.split('\n')[0].strip()  # First line as summary

        # Parameter extraction
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            # Skip internal params
            if param_name in {'conn', 'tool_name', 'fs_config', 'args', 'kwargs'}:
                continue

            # Handle *args and **kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            has_default = param.default != inspect.Parameter.empty
            default_val = param.default if has_default else None

            # Extract description from docstring (parse Arguments section)
            param_desc = self._extract_param_description(full_doc, param_name)

            parameters[param_name] = ParamInfo(
                type=param_type,
                required=not has_default,
                default=default_val,
                description=param_desc
            )

        # Build keyword index
        keywords = set()
        keywords.add(tool_name.lower())
        keywords.update(tool_name.lower().split('_'))

        # Add words from description (filter common words)
        stopwords = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                     'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                     'to', 'was', 'will', 'with', 'via', 'this', 'or', 'if'}
        desc_words = re.findall(r'\b\w+\b', description.lower())
        keywords.update(w for w in desc_words if len(w) > 2 and w not in stopwords)

        # Add parameter names
        keywords.update(param_name.lower() for param_name in parameters.keys())
        keywords.discard('')  # Remove empty strings

        return ToolMetadata(
            name=tool_name,
            display_name=tool_name.replace('_', ' ').title(),
            func=func,
            description=description,
            parameters=parameters,
            signature=sig,
            category=category,
            keywords=keywords,
            full_doc=full_doc
        )

    def _extract_param_description(self, docstring: str, param_name: str) -> str:
        """
        Extract parameter description from docstring.

        Args:
            docstring: The full docstring
            param_name: The parameter name to find

        Returns:
            Description string or empty string if not found
        """
        # Look for "Arguments:" section
        lines = docstring.split('\n')
        in_args_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect Arguments section
            if stripped.lower() in ('arguments:', 'args:', 'parameters:', 'params:'):
                in_args_section = True
                continue

            # Exit arguments section on next section header or blank line
            if in_args_section and stripped and stripped.endswith(':') and stripped != f"{param_name}:":
                break

            # Look for parameter line
            if in_args_section:
                # Match patterns like: "param_name - description" or "param_name: description"
                match = re.match(rf'\s*{re.escape(param_name)}\s*[-:]\s*(.+)', line)
                if match:
                    return match.group(1).strip()

        return ""

    # Documentation methods (for future extension)

    def register_doc(self, doc_name: str, doc_content: str):
        """
        Register a documentation snippet in the context catalog.

        Args:
            doc_name: The name/key for the documentation snippet
            doc_content: The content of the documentation snippet
        """
        self.docs[doc_name] = doc_content

    def get_doc(self, doc_name: str) -> Optional[str]:
        """
        Retrieve a documentation snippet by name.

        Args:
            doc_name: Name of the documentation snippet

        Returns:
            Documentation content if found, None otherwise
        """
        return self.docs.get(doc_name)

    def search_docs(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search for documentation snippets matching keywords.

        Args:
            query: Keywords to search for
            limit: Maximum number of results to return

        Returns:
            List of matching documentation snippets
        """
        query_lower = query.lower()
        results = []

        for name, content in self.docs.items():
            score = 0

            if query_lower in name.lower():
                score += 100

            if query_lower in content.lower():
                score += 50

            if score > 0:
                results.append((score, name, content))

        results.sort(reverse=True, key=lambda x: x[0])

        return [
            {"name": name, "content": content[:500] + "..." if len(content) > 500 else content}
            for score, name, content in results[:limit]
        ]
