from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color, black, white, HexColor
from reportlab.lib.utils import ImageReader
import os
import io
import requests
from PIL import Image, ImageOps

# Register MICR Font
FONT_PATH = os.path.join('assets', 'fonts', 'E13B.ttf')
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('MICR', FONT_PATH))
else:
    print(f"WARNING: MICR font not found at {FONT_PATH}")

# Define colors (Theme changed to BLACK per user request)
CH_THEME_COLOR = black 

class ChequeGenerator:
    def __init__(self, output_dir="outputs"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.width, self.height = letter
        
        # Reference backgrounds (if they exist)
        self.top_bg = os.path.join("assets", "templates", "top_bg_clean.png")
        self.cheque_bg = os.path.join("assets", "templates", "cheque_bg_clean.png")

    def generate(self, data):
        # Ensure cheque number is padded to 8 digits
        raw_no = str(data.get('cheque_number', '')).strip()
        padded_no = raw_no.zfill(8)
        data['padded_cheque_number'] = padded_no
        
        filename = f"cheque_{padded_no}.pdf"
        return self.generate_variant(data, filename)

    def generate_variant(self, data, filename):
        full_path = os.path.join(self.output_dir, filename)
        c = canvas.Canvas(full_path, pagesize=letter)
        self._draw_full_cheque(c, data)
        c.save()
        return full_path

    def _draw_full_cheque(self, c, data):
        """Draws the entire page with refined layout based on latest reference image."""
        d = data
        padded_no = d.get('padded_cheque_number', str(d.get('cheque_number', '')).zfill(8))
        
        # =========================
        # 🔝 BACKGROUND TEMPLATES
        # =========================
        try:
            if os.path.exists(self.top_bg):
                c.drawImage(ImageReader(self.top_bg), 0, 4.2 * inch, width=8.5 * inch, height=6.8 * inch)
            
            if os.path.exists(self.cheque_bg):
                c.drawImage(ImageReader(self.cheque_bg), 0.2 * inch, 0.5 * inch, width=8.1 * inch, height=3.2 * inch)
            else:
                # Custom bars (Changed to BLACK theme)
                c.setFillColor(CH_THEME_COLOR)
                c.rect(0.2 * inch, 3.4 * inch, 8.1 * inch, 0.28 * inch, fill=1, stroke=0)
                c.rect(0.2 * inch, 0.45 * inch, 8.1 * inch, 0.12 * inch, fill=1, stroke=0)
                c.setFillColor(black)
        except Exception as e:
            print(f"BGs could not be loaded: {e}")

        c.setFont("Courier", 10)
        
        # FROM Section
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, 10.3 * inch, "FROM:")
        c.setFont("Helvetica", 10)
        
        emp_name = str(d.get("employer_name", "")).split('\n')[0].upper()
        c.drawString(1.5 * inch, 10.3 * inch, emp_name)
        
        y_emp = 10.15 * inch
        # Secondary employer plan info
        emp_lines = str(d.get("employer_name", "")).split('\n')
        if len(emp_lines) > 1:
            for line in emp_lines[1:]:
                if line.strip():
                    c.drawString(1.5 * inch, y_emp, line.upper())
                    y_emp -= 0.15 * inch
        
        # Employer Address
        c.drawString(1.5 * inch, y_emp, str(d.get('employer_street', '')).upper())
        y_emp -= 0.15 * inch
        c.drawString(1.5 * inch, y_emp, str(d.get('employer_city_state_zip', '')).upper())

        # TO Section
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, 9.1 * inch, "TO:")
        
        # Barcode placeholder above payee (Maintained as commented out)
        # c.setFont("Courier", 10)
        # c.drawString(1.5 * inch, 9.25 * inch, "||.||..|||..||..|||..||..|||..||..|||..|||..||..||") 
        
        c.setFont("Courier", 10)
        c.drawString(1.5 * inch, 9.1 * inch, str(d.get("payee_name", "")).upper())
        y_to = 8.95 * inch
        for line in str(d.get("payee_address", "")).split('\n'):
            if line.strip():
                c.drawString(1.5 * inch, y_to, line.upper())
                y_to -= 0.15 * inch

        # RIGHT SIDE Block (Date, Check No, Bkcode, SSN)
        ref_x = 7.8 * inch
        c.setFont("Courier", 10)
        c.drawRightString(ref_x, 9.1 * inch, str(d.get("date", "")))
        c.drawRightString(ref_x, 8.95 * inch, f"CHECK NO.: {padded_no}")
        c.drawRightString(ref_x, 8.8 * inch, str(d.get("bkcode", "")))
        
        ssn_raw = d.get('ssn', '')
        masked_ssn = f"XXX-XX-{ssn_raw[-4:]}" if len(ssn_raw) >= 4 else ssn_raw
        c.drawRightString(ref_x, 8.65 * inch, masked_ssn)

        # NAME ADDRESS BLOCK (Maintained Courier 8 font)
        c.setFont("Courier", 8)
        c.drawString(1.0 * inch, 8.3 * inch, "NAME")
        c.drawString(1.0 * inch, 8.15 * inch, "ADDRESS")
        
        c.setFont("Courier", 10)
        c.drawString(2.3 * inch, 8.3 * inch, str(d.get("payee_name", "")).upper())
        addr_flat = str(d.get("payee_address", "")).replace('\n', ', ').upper()
        c.drawString(2.3 * inch, 8.15 * inch, addr_flat)

        # SUMMARY COLUMNS (Maintained Balanced spacing and Courier 10 font)
        y_sum_h = 7.1 * inch
        c.setFont("Courier", 10)
        pos_cols = [1.5 * inch, 3.5 * inch, 5.5 * inch, 7.5 * inch]
        c.drawCentredString(pos_cols[0], y_sum_h, "PENSION")
        c.drawCentredString(pos_cols[1], y_sum_h, "FED W/H")
        c.drawCentredString(pos_cols[2], y_sum_h, "S/T W/H")
        c.drawCentredString(pos_cols[3], y_sum_h, "CHECK AMT")
        
        y_sum_v = y_sum_h - 0.35 * inch
        c.setFont("Courier", 10)
        val_amt = f"{float(d.get('amount', 0)):,.2f}"
        c.drawCentredString(pos_cols[0], y_sum_v, val_amt)
        c.drawCentredString(pos_cols[1], y_sum_v, ".00")
        c.drawCentredString(pos_cols[2], y_sum_v, ".00")
        c.drawCentredString(pos_cols[3], y_sum_v, val_amt)

        # NOTICE TEXT (Maintained size and alignment adjustments)
        c.setFont("Courier", 10.5)
        notice_text = [
            "IN THE EVENT YOU DO NOT RECEIVE YOUR CHECK ON THE FIRST OF THE MONTH,",
            "DO NOT CONTACT THE FUND ADMINISTRATION OFFICE UNTIL AFTER THE TENTH",
            "(10TH) OF THE MONTH, SINCE NO STOP-PAYMENT ORDERS MAY BE PLACED ON",
            "LOST CHECKS UNTIL AFTER THE (10TH) TENTH OF THE MONTH IN WHICH THEY ARE",
            "ISSUED."
        ]
        y_notice = 6.0 * inch
        for line in notice_text:
            c.drawString(1.25 * inch, y_notice, line)
            y_notice -= 0.18 * inch

        
        
        # Employer Info (Top Left)
        c.setFont("Helvetica-Bold", 8)
        emp_lines = str(d.get("employer_name", "")).split('\n')
        c.drawString(0.5 * inch, 3.15 * inch, emp_lines[0].upper())
        if len(emp_lines) > 1:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(0.5 * inch, 3.0 * inch, emp_lines[1].upper())

        # Date & SSN Table
        table_x, table_y = 0.5 * inch, 2.45 * inch
        table_w, table_h = 3.2 * inch, 0.45 * inch
        col1_w = 1.4 * inch
        header_h = 0.15 * inch

        c.setLineWidth(0.8)
        c.rect(table_x, table_y, table_w, table_h)
        c.line(table_x, table_y + table_h - header_h, table_x + table_w, table_y + table_h - header_h)
        c.line(table_x + col1_w, table_y, table_x + col1_w, table_y + table_h)
        
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(table_x + col1_w / 2, table_y + table_h - 0.12 * inch, "DATE")
        c.drawCentredString(table_x + col1_w + (table_w - col1_w) / 2, table_y + table_h - 0.12 * inch, "SOCIAL SECURITY NUMBER")

        c.setFont("Courier-Bold", 10)
        date_str = str(d.get('date', '')).replace(' ', '')
        c.drawCentredString(table_x + col1_w / 2, table_y + 0.1 * inch, date_str)
        c.drawCentredString(table_x + col1_w + (table_w - col1_w) / 2, table_y + 0.1 * inch, masked_ssn)

        # Bank Info
        c.setFont("Helvetica", 7)
        bank_lines = str(d.get('bank_info', '')).split('\n')
        y_bank = 2.2 * inch
        for line in bank_lines:
            c.drawString(0.6 * inch, y_bank, line.upper())
            y_bank -= 0.12 * inch

        # Cheque Number (Top Right - Maintained Helvetica 18 font)
        c.setFont("Helvetica-Bold", 15)
        c.drawRightString(7.65 * inch, 3.18 * inch, padded_no)
        
        # BKROUT / Fraction (RESTORED and UPDATED from DB - Real data, no hard fallback)
        c.setFont("Helvetica", 6)
        bkrout = str(d.get('bank_routing_fraction', '')).strip()
        if not bkrout:
            # bkrout = "19-1/910" # Safety only
            pass
        c.drawRightString(5.7 * inch, 3.05 * inch, bkrout)

        # Amount Words (Preserving user manual adjustment y=1.65)
        c.setFont("Courier", 11)
        c.drawCentredString(4.25 * inch, 1.75 * inch, str(d.get('amount_words', '')))

        # --- Payee (PAY TO THE ORDER OF + DOTS) ---
        labels = ["PAY TO", "THE ORDER", "OF"]
        label_center_x = 0.8 * inch
        bullet_x = 1.25 * inch
        text_x = 1.5 * inch
        y_payee = 1.33 * inch
        
        payee_lines = [str(d.get('payee_name', '')).upper()]
        p_addr = str(d.get('payee_address', ''))
        if p_addr:
            payee_lines.extend([line.upper() for line in p_addr.split('\n') if line.strip()])

        for i in range(max(4, len(payee_lines))):
            if i < len(labels):
                c.setFont("Times-Bold", 6)
                c.drawCentredString(label_center_x, y_payee, labels[i])
            y_payee -= 0.18 * inch
        
        y_payee = 1.40 * inch
        for i in range(max(4, len(payee_lines))):
            if i < 4: # Always draw 4 dots
                c.circle(bullet_x, y_payee + 0.05 * inch, 1.2, fill=1, stroke=0)
            y_payee -= 0.18 * inch

        y_payee = 1.45 * inch
        for i in range(max(4, len(payee_lines))):
            if i < len(payee_lines):
                c.setFont("Courier", 11)
                c.drawString(text_x, y_payee, payee_lines[i])
            y_payee -= 0.18 * inch

        # --- Amount Box (Preserving user manual adjustment x=7.3, y=3.0) ---
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(7.2 * inch, 3.0 * inch, "PAY THIS AMOUNT")
        
        box_w, box_h = 1.5 * inch, 0.45 * inch
        box_x = 6.45 * inch
        box_y = 2.45 * inch
        c.setLineWidth(1)
        c.rect(box_x, box_y, box_w, box_h)
        
        c.setFont("Courier-Bold", 12)
        c.drawCentredString(box_x + box_w/2, box_y + 0.15 * inch, f"${val_amt}*")
        
        # VOID AFTER {void_days} DAYS (Dynamic from DB)
        c.setFont("Helvetica-Bold", 7)
        v_days = d.get('void_days', 90)
        c.drawCentredString(box_x + box_w/2, box_y - 0.15 * inch, f"VOID AFTER {v_days} DAYS")

        # Signature rendering
        sig_path = d.get('signature_path', '')
        if sig_path:
            self._draw_signature(c, sig_path, 0.85 * inch)

        # --- MICR Line (Bottom Center) ---
        if pdfmetrics.getRegisteredFontNames().count('MICR'):
            c.setFont("MICR", 14)
            r_no = str(d.get('routing_number', '')).strip()
            acct = str(d.get('micr_account_tail', '')).strip().rstrip('/').replace('-', 'D')
            micr_line = f"C{padded_no}C A{r_no}A {acct}C"
            c.drawCentredString(4.25 * inch, 0.3 * inch, micr_line)

    def _draw_signature(self, c, sig_path, y_pos):
        try:
            if sig_path.startswith(('http://', 'https://')):
                response = requests.get(sig_path, timeout=10)
                img_raw = Image.open(io.BytesIO(response.content))
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                abs_path = os.path.join(project_root, sig_path)
                path_to_use = abs_path if os.path.exists(abs_path) else sig_path
                img_raw = Image.open(path_to_use)
            
            final_sig_data = self._process_signature_image(img_raw)
            if final_sig_data:
                c.drawImage(final_sig_data, 5.5 * inch, y_pos, width=2.6 * inch, height=0.75 * inch, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"ERROR: Signature rendering failed: {e}")

    def _process_signature_image(self, img_raw):
        try:
            img_raw = img_raw.convert('RGBA')
            gray = img_raw.convert('L')
            alpha_mask = gray.point(lambda x: 0 if x > 220 else 255)
            img_raw.putalpha(alpha_mask)
            bbox = alpha_mask.getbbox()
            if bbox:
                trim = 20
                img_cropped = img_raw.crop((max(0, bbox[0] + trim), max(0, bbox[1] + trim), min(img_raw.width, bbox[2] - trim), min(img_raw.height, bbox[3] - trim)))
            else:
                img_cropped = img_raw
            if img_cropped.width > 1000:
                img_cropped = img_cropped.resize((1000, int(img_cropped.height * (1000 / img_cropped.width))), Image.LANCZOS)
            img_byte_arr = io.BytesIO()
            img_cropped.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return ImageReader(img_byte_arr)
        except Exception as e:
            print(f"ERROR: Image processing failed: {e}")
            return ImageReader(img_raw)

if __name__ == "__main__":
    gen = ChequeGenerator()
    test_data = {
        "employer_name": "PLASTERERS LOCAL NO. 1\nPENSION PLAN",
        "employer_street": "525 VINE STREET, SUITE 2325",
        "employer_city_state_zip": "CINCINNATI, OH 45202",
        "date": "03/21/25",
        "ssn": "XXX-XX-4093",
        "cheque_number": "128365",
        "bkcode": "PL1",
        "bank_info": "US BANK\n425 LUDLOW AVE\nCINCINNATI, OH",
        "payee_name": "MARGARET HALL",
        "payee_address": "718 GREENTREE RD\nLAWRENCBURG IN 47025",
        "amount": 1.00,
        "amount_words": "*** One Dollars And 00/100***",
        "routing_number": "019001319",
        "micr_account_tail": "102778400",
        "bank_routing_fraction": "19-1/910",
        "void_days": 120,
        "signature_path": "assets/signatures/white-sig.jpg"
    }
    gen.generate(test_data)
