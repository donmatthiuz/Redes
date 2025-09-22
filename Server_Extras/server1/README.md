# arxiv-mcp-server
Arxiv MCP Server<br>

Available tools<br>
```
  • arxiv_search_arxiv: Search papers in arxiv
    Args:
        query: Search query (can include terms, authors, categories like 'cat:cs.AI')
        sort_by: 'relevance', 'date'
        sort_order: 'ascending', 'descending

  • arxiv_download_paper_arxiv: Downloads papers as PDF from arxiv
    Args:
        id: arxiv id (e.g. '1701.08184v1')
        filename: name to assign to the pdf file

  • arxiv_get_download_root: Returns the root for arxiv downloads
    
  • arxiv_generate_bibtex: Generate bibtex for a paper. If possible get the DOI (highest priority) before calling this function. 
    In order to be called it must have at least one of the arguments
    Args:
        doi: (otional) identificator of the paper
        title: (optional) title of the paper
        authors: (optional) name of the authors
        year: (optional) year of publication
```

Example:<br>
```
💬 You: get me five new papers about quantum computing
🤔 Assistant:
🔧 Executing arxiv_search_arxiv...
Here are five new papers about quantum computing:

1. "Quantum Computing and the Limits of Computation" by Scott Aaronson (arXiv:2508.21821v1)
2. "A Quantum Algorithm for Simulating the Dynamics of Open Quantum Systems" by Jianxin Chen et al. (arXiv:2508.21820v1)
3. "Quantum Error Correction with Topological Codes" by Courtney G. Brell et al. (arXiv:2508.21819v1)
4. "Quantum Machine Learning with Quantum Circuits" by Maria Schuld et al. (arXiv:2508.21818v1)
5. "Quantum Simulation of Quantum Field Theories" by Zohreh Davoudi et al. (arXiv:2508.21815v1)

These papers cover various topics in quantum computing, including the limits of computation, simulation of open quantum systems, quantum error correction, quantum machine learning, and quantum simulation of quantum field theories.

💬 You: now get me five important papers
🤔 Assistant: 
🔧 Executing arxiv_search_arxiv...
Here are five important papers about quantum computing:

1. "The Rise of Quantum Internet Computing" by Seng W. Loke (arXiv:2208.00733v1)
2. "Unconventional Quantum Computing Devices" by Seth Lloyd (arXiv:0003151v1)
3. "Geometrical perspective on quantum states and quantum computation" by Zeqian Chen (arXiv:1311.4939v1)
4. "Quantum Computation and Quantum Information" by Yazhen Wang (arXiv:1210.0736v1)
5. "Probabilistic Process Algebra to Unifying Quantum and Classical Computing in Closed Systems" by Yong Wang (arXiv:1610.02500v1)

These papers cover various topics in quantum computing, including quantum Internet computing, unconventional quantum computing devices, geometric perspectives on quantum states and computation, quantum computation and quantum information, and probabilistic process algebra for unifying quantum and classical computing in closed systems.

💬 You: download paper 3 and generate its bibtex
🤔 Assistant: 
🔧 Executing arxiv_download_paper_arxiv...
🔧 Executing arxiv_generate_bibtex...
The paper "Geometrical perspective on quantum states and quantum computation" by Zeqian Chen has been downloaded successfully.

Here is the generated BibTeX for the paper:

@article{10_1007/s10773-020-04404-5,
        author = {Zeqian Chen},
        title = {Observable-Geometric Phases and Quantum Computation},
        journal = {International Journal of Theoretical Physics},
        year = {2020},
        volume = {59},
        number = {4},
        pages = {1255-1276},
        doi = {10.1007/s10773-020-04404-5}
    }

```
To execute this MCP server, clone the repository or downlad the zip file. It is recommended to use `uv` for package management (the requierments can be found on `requirements.txt` or `pyproject.toml`). Then use the following parameters when configuring this MCP using Anthropic's SDK<br>
```json
{
  "command": "uv",
  "args": [
    "run", "--repository", "PATH/TO/REPO", "PATH/TO/REPO/arxiv_mcp_server.py"
  ]
}
```
Moreover, the user should specify the default path for pdf downloads in the `.env` file 
```env
DOWNLOAD_ROOT = 'PATH/TO/DOWNLOAD/PDF'
```
