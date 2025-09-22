#!/usr/bin/env python3


import os
from dotenv import load_dotenv
import logging
from typing import Any, Sequence

import arxiv
from server_parthers.server1.bibtex_gen import BibtexGenerator

load_dotenv()
    
DOWNLOAD_DIR = os.getenv("DOWNLOAD_ROOT")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arxiv-mcp-server")

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("arxiv-mcp-server")

def format_paper_info(paper) -> str:
    """Format paper information for display."""
    authors = ", ".join([author.name for author in paper.authors])
    categories = ", ".join(paper.categories)
    
    # Format dates
    published = paper.published.strftime("%Y-%m-%d") if paper.published else "Unknown"
    updated = paper.updated.strftime("%Y-%m-%d") if paper.updated else "Unknown"
    
    return f"""**{paper.title}**

**Authors:** {authors}

**ArXiv ID:** {paper.entry_id.split('/')[-1]}

**Categories:** {categories}

**Published:** {published}
**Updated:** {updated}

**PDF URL:** {paper.pdf_url}
**ArXiv URL:** {paper.entry_id}

**DOI:** {paper.doi}

**Abstract:**
{paper.summary}"""

# **BibTeX:** {paper.bibtex if paper.bibtex else 'Unknown'}"""

SORT_BY = {
    'relevance': arxiv.SortCriterion.Relevance,
    'date': arxiv.SortCriterion.SubmittedDate
}
SORT_ORDER = {
    'ascending': arxiv.SortOrder.Ascending,
    'descending': arxiv.SortOrder.Descending
}

@mcp.tool()
async def search_arxiv(query:str, sort_by:str, sort_order:str) -> str:
    """Search papers in arxiv

    Args:
        query: Search query (can include terms, authors, categories like 'cat:cs.AI')
        sort_by: 'relevance', 'date'
        sort_order: 'ascending', 'descending
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=5,
        sort_by=SORT_BY.get(sort_by, arxiv.SortCriterion.Relevance),
        sort_order=SORT_ORDER.get(sort_order, arxiv.SortOrder.Descending)
    )
    results = []
    paper_count = 0
    for paper in client.results(search):
        results.append(format_paper_info(paper))
        paper_count += 1
        if paper_count >= 5:
            break
    return ('\n' + '-'*80 + '\n').join(results)

@mcp.tool()
async def download_paper_arxiv(id:str, filename:str) -> str:
    """Downloads papers as PDF from arxiv

    Args:
        id: arxiv id (e.g. '1701.08184v1')
        filename: name to assign to the pdf file
    """
    client = arxiv.Client()
    search = arxiv.Search(
        id_list=[id]
    )
    try:
        paper = next(client.results(search))
        print(paper.title)
        paper.download_pdf(dirpath=DOWNLOAD_DIR, filename=filename)
        return f'PDF {filename} downloaded successfully at directory: {dir}'
    except Exception as e:
        return f'Error while downloading with id: {id}, directory: {dir}\nException: {e}'
    
@mcp.tool() 
async def get_download_root() -> str:
    """Returns the root for arxiv downloads
    """
    return DOWNLOAD_DIR
    

@mcp.tool()
async def generate_bibtex(doi:str=None, title:str=None, authors:str=None, year:str=None) -> str:
    """Generate bibtex for a paper. If possible get the DOI (highest priority) before calling this function. 
    In order to be called it must have at least one of the arguments

    Args:
        doi: (otional) identificator of the paper
        title: (optional) title of the paper
        authors: (optional) name of the authors
        year: (optional) year of publication
    """
    generator = BibtexGenerator()
    bibtex = generator.generate_bibtex(doi, None, title, authors, year)
    if bibtex:
        return bibtex
    return 'Could not generate the bibtex citation'

if __name__ == "__main__":
    print("Ejemplo")
    # Initialize and run the server
    mcp.run(transport='stdio')
