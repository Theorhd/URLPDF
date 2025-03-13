from PDFGenerator.PDFGenerator import PDFGenerator

if __name__ == "__main__":
    pdf = PDFGenerator(output_dir="output")
    urls = pdf.all_urls("https://docs.crewai.com", 1000, False)
    pdf.generate_pdfs_from_urls(urls, False, False)
