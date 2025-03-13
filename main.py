from PDFGenerator.PDFGenerator import PDFGenerator

if __name__ == "__main__":
    pdf = PDFGenerator(output_dir="output")
    urls = pdf.all_urls("https://mammouth.ai/", 1000, False)
    pdf.generate_pdfs_from_urls(urls, False, False)
