import requests
import arxiv
from habanero import Crossref
from scholarly import scholarly
import json
import re

class BibtexGenerator:
    def __init__(self):
        self.cr = Crossref()
    
    def generate_bibtex(self, doi=None, arxiv_id=None, title=None, authors=None, year=None):
        """Main method to generate BibTeX from various inputs"""
        if doi:
            return self._from_doi(doi)
        elif arxiv_id:
            return self._from_arxiv(arxiv_id)
        elif title or authors or year:
            return self.search_paper_bibtex(title, authors, year)
        else:
            return "Please provide at least one identifier"
    
    def _from_doi(self, doi):
        try:
            result = self.cr.works(ids=doi)
            print(doi)
            return self._format_crossref_bibtex(result['message'])
        except Exception as e:
            return f'Error: {e}'
    
    def _from_arxiv(self, arxiv_id):
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(search.results())
            if results:
                return self._format_arxiv_bibtex(results[0])
        except Exception as e:
            return f'Error: {e}'
    
    
    def _format_crossref_bibtex(self, crossref_data):
        """Simple function to format Crossref data as BibTeX"""
        work = crossref_data
        entry_type = 'article'  # Default to article
        
        authors = " and ".join([f"{author.get('given', '')} {author.get('family', '')}" 
                            for author in work.get('author', [])])
        journal = work.get('container-title', [''])
        journal = journal[0] if len(journal) > 0 else 'Unknown'
        
        bibtex = f"""@article{{{work.get('DOI', 'unknown').replace('.', '_')},
        author = {{{authors}}},
        title = {{{work.get('title', ['Untitled'])[0]}}},
        journal = {{{journal}}},
        year = {{{work.get('issued', {}).get('date-parts', [[None]])[0][0]}}},
        volume = {{{work.get('volume', '')}}},
        number = {{{work.get('issue', '')}}},
        pages = {{{work.get('page', '')}}},
        doi = {{{work.get('DOI', '')}}}
    }}"""
        return bibtex
    
    def search_paper_bibtex(self, title=None, authors=None, year=None):
        """Search for paper and generate BibTeX"""
        search_query = ""
        if title:
            search_query += f"title: '{title}' "
        if authors:
            search_query += f"author:'{authors}' "
        if year:
            search_query += f"({year})"

        ans = ''
        # search_results = scholarly.search_pubs(search_query, citations=False)
        # for result in search_results:
        #     # Check if it matches our criteria
        #     if (not title or title.lower() in result['bib']['title'].lower()):
        #         bib = result['bib']
        #         search_query = f"title: '{bib['title']}' ({bib['pub_year']}) author: '{', '.join(bib['author'])}'"
        #         ans = self.format_scholarly_as_bibtex(result)
        #         break

        try:
            print(search_query)
            result = self.cr.works(query=search_query, limit=5)['message']['items']
            return ('\n' + '='*80 + '\n').join([ans]+[self._format_crossref_bibtex(res) for res in result])
        except Exception as e:
            return f'Error: {e}'
        
         
        
        # for result in search_results:
        #     # Check if it matches our criteria
        #     if (not title or title.lower() in result['bib']['title'].lower()):
        #         return self.format_scholarly_as_bibtex(result)
        
        # return None

    def format_scholarly_as_bibtex(self, paper):
        """Format scholarly result as BibTeX"""
        bib = paper['bib']
        entry_id = f"{'-'.join('_'.join(a.split()) for a in bib['author']).lower()}{bib['pub_year']}"
        
        bibtex = f"""@article{{{entry_id},
        author = {{{' and '.join(bib['author'])}}},
        title = {{{bib['title']}}},
        journal = {{{bib.get('journal', '')}}},
        year = {{{bib.get('pub_year', '')}}},
        volume = {{{bib.get('volume', '')}}},
        number = {{{bib.get('number', '')}}},
        pages = {{{bib.get('pages', '')}}},
        doi = {{{bib.get('doi', '')}}},
        url = {{{paper.get('pub_url', '')}}}
    }}"""
        
        return bibtex
    
    def _format_arxiv_bibtex(self, paper):
        entry_id = re.sub(r'[^a-zA-Z0-9]', '_', paper.entry_id.split('/')[-1])
    
        bibtex = f"""@article{{{entry_id},
        author = {{{paper.authors[0]}}},
        title = {{{paper.title}}},
        journal = {{arXiv preprint}},
        year = {{{paper.published.year}}},
        eprint = {{{paper.entry_id.split('/')[-1]}}},
        archivePrefix = {{arXiv}},
        primaryClass = {{{paper.primary_category}}},
        url = {{{paper.pdf_url}}}
    }}"""
        
        return bibtex

if __name__ == '__main__':
    generator = BibtexGenerator()
    bibtex = generator.generate_bibtex(doi="https://doi.org/10.1016/j.jmaa.2025.129959")
    print(bibtex)
    bibtex = generator.generate_bibtex(title="Attention is all you need")
    print(bibtex)
    bibtex = generator.generate_bibtex(doi="10.1002/9781394185542")
    print(bibtex)