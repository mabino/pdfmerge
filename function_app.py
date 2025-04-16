import logging
import azure.functions as func
import json
import base64
from pypdf import PdfWriter, PdfReader
import io
from azure.functions import FunctionApp

app = FunctionApp()

def decode_pdf(base64_str: str):
    try:
        return io.BytesIO(base64.b64decode(base64_str))
    except Exception as e:
        logging.warning(f"Failed to decode PDF: {e}")
        return None

def merge_pdfs(base64_pdfs: list[str]) -> str:
    writer = PdfWriter()
    valid_pdfs = 0

    for b64 in base64_pdfs:
        stream = decode_pdf(b64)
        if stream:
            try:
                reader = PdfReader(stream)
                for page in reader.pages:
                    writer.add_page(page)
                valid_pdfs += 1
            except Exception as e:
                logging.warning(f"Failed to read or merge PDF: {e}")

    if valid_pdfs < 2:
        raise ValueError(f"Only {valid_pdfs} valid PDFs. Need at least 2.")

    output = io.BytesIO()
    writer.write(output)
    return base64.b64encode(output.getvalue()).decode()

@app.function_name(name="mergePdfs")
@app.route(route="merge", methods=["POST"])
def merge_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        pdf_list = data.get('pdf_contents_base64')

        if not pdf_list or len(pdf_list) < 2:
            return func.HttpResponse(
                "Expecting 'pdf_contents_base64' array with at least 2 Base64 PDFs.",
                status_code=400
            )

        merged_pdf = merge_pdfs(pdf_list)
        return func.HttpResponse(
            json.dumps({'merged_pdf_base64': merged_pdf}),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as ve:
        return func.HttpResponse(str(ve), status_code=400)
    except Exception as e:
        logging.error(f"Unhandled error: {e}")
        return func.HttpResponse(
            f"Internal server error: {str(e)}",
            status_code=500
        )
