from fpdf import FPDF

def make_pdf(yml_content, py_content, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=8)

    pdf.cell(0, 10, "Notion Update Notification System", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 9)
    pdf.cell(0, 8, "1. GitHub Actions Workflow (notion-check.yml)", ln=True)
    pdf.set_font("Courier", size=8)
    pdf.multi_cell(0, 4, yml_content)
    pdf.ln(3)

    pdf.set_font("Courier", "B", 9)
    pdf.cell(0, 8, "2. Python Script (check_notion.py)", ln=True)
    pdf.set_font("Courier", size=8)
    pdf.multi_cell(0, 4, py_content)

    pdf.output(output_path)

# ファイル読み込み
with open("notion-check.yml") as f:
    yml = f.read()

with open("check_notion.py") as f:
    py = f.read()

make_pdf(yml, py, "Notion_Update_Notification_System.pdf")
