import sqlite3
import os
from datetime import datetime

class SqliteService:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_cheques(self, page=1, page_size=10, filters=None):
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        offset = (page - 1) * page_size
        
        query = "SELECT * FROM cheques WHERE 1=1"
        params = []
        
        if filters:
            if filters.get("bkcode"):
                query += " AND bkcode = ?"
                params.append(filters["bkcode"])
            if filters.get("cheque_number"):
                query += " AND cheque_number LIKE ?"
                params.append(f"%{filters['cheque_number']}%")
            if filters.get("payee_name"):
                query += " AND payee_name LIKE ?"
                params.append(f"%{filters['payee_name']}%")
            if filters.get("ssn_last4"):
                # Ensure it matches the end of the SSN
                query += " AND ssn LIKE ?"
                params.append(f"%{filters['ssn_last4']}")
            if filters.get("date"):
                query += " AND date LIKE ?"
                params.append(f"%{filters['date']}%")
        
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        processed_rows = []
        for row in rows:
            d = dict(row)
            ssn = d.get('ssn', '')
            d['ssn_masked'] = "XXXXX" + ssn[-4:] if ssn and len(ssn) >= 4 else ssn
            del d['ssn']
            processed_rows.append(d)
            
        conn.close()
        return processed_rows, total_count

    def get_full_data_by_ids(self, ids):
        if not ids:
            return []
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(ids))
        query = f"SELECT * FROM cheques WHERE id IN ({placeholders})"
        cursor.execute(query, ids)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_signatures(self):
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signatures ORDER BY name ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_signature_by_id(self, sig_id):
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signatures WHERE id = ?", (sig_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def approve_cheque(self, cheque_id, signature_id):
        sig = self.get_signature_by_id(signature_id)
        if not sig:
            return False, "Signature not found"
            
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("SELECT is_approved FROM cheques WHERE id = ?", (cheque_id,))
        row = cursor.fetchone()
        if row and row['is_approved']:
            conn.close()
            return False, "This cheque is already approved and cannot be re-signed."
            
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            UPDATE cheques 
            SET approved_signature_id = ?, 
                approved_by_name = ?, 
                approved_signature_path = ?, 
                is_approved = 1, 
                approved_at = ?
            WHERE id = ?
        """
        cursor.execute(query, (
            sig['id'],
            sig['name'],
            sig['signature_path'],
            now,
            cheque_id
        ))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success, "Approved successfully" if success else "Cheque not found"
