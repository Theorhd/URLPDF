import re
import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from fpdf import FPDF
from ollama import chat
from ollama import ChatResponse
from tqdm import tqdm

class PDFGenerator:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.openaiapi_key = os.getenv("OPENAI")
        self.ollama_model = os.getenv("OLLAMA_MODEL")

    def sanitize_filename(self, filename):
        """Nettoie le nom de fichier en supprimant les caractères interdits."""
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def get_filename_from_url(self, url):
        """
        Génère un nom de fichier à partir d'une URL.
        """
        parsed = urlparse(url)
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) > 1:
            domain = "_".join(domain_parts[:-1])
        else:
            domain = parsed.netloc

        path_parts = [part for part in parsed.path.split('/') if part]
        if path_parts:
            filename_base = domain + "_" + "_".join(path_parts)
        else:
            filename_base = domain

        filename_base = self.sanitize_filename(filename_base)
        return filename_base

    def get_content_from_url(self, url):
        """Extrait le texte brut d'une URL en utilisant BeautifulSoup."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            print(f"Erreur lors de la récupération du contenu de l'URL {url} : {e}")
            return ""

    def create_pdf_from_content(self, content, filename):
        """
        Crée un PDF à partir du contenu.
        Le texte est converti en latin-1 en ignorant les erreurs d'encodage
        pour éviter les problèmes avec FPDF.
        """
        content = content.encode('latin-1', errors='ignore').decode('latin-1')
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        
        output_path = os.path.join(self.output_dir, filename)
        try:
            pdf.output(output_path)
            print(f"PDF sauvegardé dans : {output_path}")
        except Exception as e:
            print(f"Erreur lors de la création du PDF {output_path} : {e}")

    def clean_text_with_gpt(self, text):
        """Nettoie le texte en utilisant GPT-4o-mini."""
        from openai import OpenAI
        client = OpenAI(api_key=self.openaiapi_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant qui nettoie le texte récuéperer depuis un site web. Tu dois supprimé les problèmes lors du scrapping, supprime les listes de la bar de navigations."},
                {"role": "user", "content": text}
            ]   
        )
        return response.choices[0].message.content
    
    def clean_with_ollama(self, text):
        """Nettoie le texte en utilisant Ollama."""
        response: ChatResponse = chat(model=self.ollama_model, messages=[
            {"role": "system", "content": "Tu es un assistant qui nettoie le texte récuéperer depuis un site web. Tu dois supprimé les problèmes lors du scrapping, supprime les listes de la bar de navigations. N'ajoute aucun contenu."},
            {"role": "user", "content": text}
            ]) 
        return response['message']['content']
    
    def all_urls(self, base_url: str, limit: int = 10, createListOfUrls: bool = False):
        """Récupère toutes les urls à partir d'une url de base qui commencent par base_url"""
        urls = []
        try:
            response = requests.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/'):
                    parsed_base = urlparse(base_url)
                    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
                    full_url = base_domain + href
                elif not href.startswith(('http://', 'https://')):
                    if base_url.endswith('/'):
                        full_url = base_url + href
                    else:
                        full_url = base_url + '/' + href
                else:
                    full_url = href
                if full_url.startswith(base_url):
                    if full_url not in urls:
                        urls.append(full_url)
                        if len(urls) >= limit:
                            break
            if createListOfUrls:
                with open('urls.txt', 'w') as f:
                    for url in urls:
                        f.write(f"{url}\n")
            return urls
        except Exception as e:
            print(f"Erreur lors de la récupération des URLs à partir de {base_url}: {e}")
            return urls

    def load_urls_from_file(self, filename):
        """Charge une liste d'URLs à partir d'un fichier texte."""
        urls = []
        with open(filename, 'r') as f:
            urls = f.readlines()
        return [url.strip() for url in urls]

    def generate_pdfs_from_urls(self, url_list, cleanWithGPT: bool = False, cleanWithOllama: bool = False):
        """Génère des PDFs à partir d'une liste d'URLs."""
        if not url_list:
            print("La liste des URLs est vide.")
            return
        
        for url in tqdm(url_list, desc="Génération des PDFs", unit="URL"):
            # Création du nom de fichier à partir de l'URL
            filename_base = self.get_filename_from_url(url)
            filename = f"{filename_base}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            # Si le fichier existe déjà, on le saute
            if os.path.exists(output_path):
                print(f"Le fichier {output_path} existe déjà. Saut de l'URL {url}.")
                continue

            print(f"Traitement de l'URL : {url}")
            content = self.get_content_from_url(url)
            if content and cleanWithGPT:
                content = self.clean_text_with_gpt(content)
            elif content and cleanWithOllama:
                content = self.clean_with_ollama(content)
            if content:
                self.create_pdf_from_content(content, filename)
            else:
                print(f"Aucun contenu trouvé pour l'URL {url}")
