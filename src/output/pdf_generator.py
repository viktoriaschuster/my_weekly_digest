# This file contains functions to generate a PDF from the summarized entries.

from fpdf import FPDF

class PDFGenerator:
    def __init__(self, title, summaries):
        self.title = title
        self.summaries = summaries
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)

    def add_title(self):
        self.pdf.set_font("Arial", 'B', 16)
        self.pdf.cell(0, 10, self.title, ln=True, align='C')
        self.pdf.ln(10)

    def add_summary(self, summary):
        self.pdf.set_font("Arial", size=12)
        self.pdf.multi_cell(0, 10, summary)
        self.pdf.ln(5)

    def generate_pdf(self, output_path):
        self.add_title()
        for summary in self.summaries:
            self.add_summary(summary)
        self.pdf.output(output_path)

def create_pdf(title, summaries, output_path):
    pdf_generator = PDFGenerator(title, summaries)
    pdf_generator.generate_pdf(output_path)