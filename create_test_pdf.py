from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf(filename="test.pdf"):
    # Create a new PDF with Reportlab
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter  # Get the size of the page
    
    # Add some content
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 100, "Test PDF Document")
    c.line(100, 95, 300, 95)
    
    c.setFont("Helvetica", 10)
    c.drawString(100, height - 150, "This is a test PDF document for verifying the upload functionality.")
    c.drawString(100, height - 170, "It contains sample text to test the PDF processing pipeline.")
    
    # Save the PDF
    c.save()
    print(f"Created test PDF: {filename}")

if __name__ == "__main__":
    create_test_pdf()
