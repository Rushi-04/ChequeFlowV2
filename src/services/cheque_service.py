import os
import sys

# Add the parent directory of 'services' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cheque_generator import ChequeGenerator

class ChequeService:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.generator = ChequeGenerator(output_dir=output_dir)

    def get_or_generate_path(self, data, signature_id=None, signature_path=None):
        # Update data with manual signature if provided
        work_data = data.copy()
        if signature_path:
            work_data['signature_path'] = signature_path
        
        # Determine filename (include signature_id if it's a preview/specific one)
        cheque_no = str(data.get('cheque_number', 'unknown')).strip()
        if signature_id:
            filename = f"cheque_{cheque_no}_sig_{signature_id}.pdf"
        else:
            filename = f"cheque_{cheque_no}.pdf"
            
        full_path = os.path.join(self.output_dir, filename)
        
        # For this system, we always regenerate to ensure fresh data
        return self.generator.generate_variant(work_data, filename)
