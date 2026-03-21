import sqlite3
import pyodbc
import os
from num2words import num2words
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db2_connection():
    host = os.getenv('DB2_HOST')
    port = os.getenv('DB2_PORT')
    database = os.getenv('DB2_DATABASE')
    user = os.getenv('DB2_USER')
    password = os.getenv('DB2_PASSWORD')

    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};"
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
    )
    return pyodbc.connect(connection_string, autocommit=True)

def format_amount_words(amount_val):
    try:
        amt_float = float(amount_val)
        dollars = int(amt_float)
        cents = int(round((amt_float - dollars) * 100))
        words = num2words(dollars, lang='en').title()
        words = words.replace(',', '').replace('-', ' ').replace(' And ', ' ')
        return f"*** {words} Dollars And {cents:02d}/100***"
    except Exception:
        return "*** Zero Dollars And 00/100***"

def clean_name(name):
    if not name: return ""
    return str(name).replace('*', ' ').strip()

def format_date_plasters(y, m, d):
    # m/dd/yy - remove leading zero from month
    y_str = str(y).strip()
    if len(y_str) == 4: y_str = y_str[2:] # Get last 2 digits
    m_str = str(int(m)) # remove leading zero
    d_str = str(d).strip().zfill(2)
    return f"{m_str}/{d_str}/{y_str}"

def format_date_j84(datupd):
    # DATUPD: 41201 -> 4/12/01 ? 
    # Let's assume MMDDYY or similar. 
    # If 41201, it might be 4/12/01.
    s = str(datupd).strip()
    if len(s) == 5:
        m = s[0]
        d = s[1:3]
        y = s[3:]
        return f"{m}/{d}/{y}"
    elif len(s) == 6:
        m = s[0:2]
        d = s[2:4]
        y = s[4:]
        return f"{int(m)}/{d}/{y}"
    return s

def sync(selection):
    # Database is in the project root (one level up from 'src')
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "cheques.db")
    
    print(f"Connecting to DB2 for {selection}...")
    try:
        conn_db2 = get_db2_connection()
        cursor_db2 = conn_db2.cursor()
    except Exception as e:
        print(f"Failed to connect to DB2: {e}")
        return

    conn_local = sqlite3.connect(db_path)
    cursor_local = conn_local.cursor()

    try:
        if selection == 'Plasters':
            main_table = "pl1df.pckmstwp"
            bkcode = "PL1"
            print(f"Fetching records from {main_table}...")
            cursor_db2.execute(f"SELECT * FROM {main_table} FETCH FIRST 20 ROWS ONLY")
        elif selection == 'J84':
            main_table = "filelib.chkhst"
            bkcode = "J84P"
            print(f"Fetching records from {main_table}...")
            cursor_db2.execute(f"SELECT * FROM {main_table} FETCH FIRST 20 ROWS ONLY")
        else:
            print(f"Unknown selection: {selection}")
            return

        columns_main = [col[0].upper() for col in cursor_db2.description]
        rows_main = cursor_db2.fetchall()

        for row in rows_main:
            data_main = dict(zip(columns_main, row))
            
            # Fetch enriched data from ameriben.bankfile
            cursor_db2.execute("SELECT * FROM ameriben.bankfile WHERE BKCODE = ?", (bkcode,))
            columns_bank = [col[0].upper() for col in cursor_db2.description]
            bank_row = cursor_db2.fetchone()
            data_bank = dict(zip(columns_bank, bank_row)) if bank_row else {}

            # Mapping Logic
            if selection == 'Plasters':
                cheque_number = str(data_main.get('PWCKNM', '')).strip()
                date_str = format_date_plasters(data_main.get('PWCKDY'), data_main.get('PWCKDM'), data_main.get('PWCKDD'))
                ssn = str(data_main.get('PWSSN', '')).strip()
                payee_name = clean_name(data_main.get('PWNAME', ''))
                
                addr_parts = [str(data_main.get(f, '')).strip() for f in ['PWADD1', 'PWADD2', 'PWADD3']]
                payee_address = "\n".join([p for p in addr_parts if p])
                
                amount = float(data_main.get('PWCKAM', 0.0))
                claim_number = str(data_main.get('PWMEM#', '')).strip()
                status = str(data_main.get('PWCKTY', 'RG')).strip()
                payment_mode = str(data_main.get('PWPYTY', 'NR')).strip()
            
            else: # J84
                cheque_number = str(data_main.get('CHECK#', '')).strip()
                date_str = format_date_j84(data_main.get('DATUPD', ''))
                ssn = str(data_main.get('SSNO', '')).strip()
                payee_name = str(data_main.get('SUPNAM', '')).strip()
                
                addr_parts = [
                    str(data_main.get('ADDR1', '')).strip(),
                    str(data_main.get('ADDR2', '')).strip(),
                    f"{str(data_main.get('CITY', '')).strip()}, {str(data_main.get('ST', '')).strip()} {str(data_main.get('ZIP', '')).strip()}".strip()
                ]
                payee_address = "\n".join([p for p in addr_parts if p and p != ","])
                
                amount = float(data_main.get('CKAMT', 0.0))
                claim_number = str(data_main.get('XTRA10', '')).strip()
                status = str(data_main.get('RECTYP', '')).strip()
                payment_mode = "" # Not clearly mapped in sample

            amount_words = format_amount_words(amount)

            # Bank Info Enrichment
            emp_name = str(data_bank.get('BKNAME', '')).strip()
            emp_name2 = str(data_bank.get('BKNAM2', '')).strip()
            employer_name = f"{emp_name}\n{emp_name2}" if emp_name2 else emp_name
            
            employer_street = str(data_bank.get('BKADR1', '')).strip()
            city_state_zip = f"{str(data_bank.get('BKADR2', '')).strip()} {str(data_bank.get('BKADR3', '')).strip()}".strip()
            
            bank_name = str(data_bank.get('BKBNAM', '')).strip()
            bank_addr = f"{str(data_bank.get('BKBAD1', '')).strip()}\n{str(data_bank.get('BKBAD2', '')).strip()}\n{str(data_bank.get('BKBAD3', '')).strip()}".strip()
            bank_info = f"{bank_name}\n{bank_addr}".strip()

            routing_number = str(data_bank.get('BKTRAN', '')).strip()
            bank_routing_fraction = str(data_bank.get('BKROUT', '')).strip()
            micr_account_tail = str(data_bank.get('BKACCT', '')).strip()
            void_days = int(data_bank.get('BKVOID', 90))

            # Pad cheque number to 8 digits
            padded_cheque_number = cheque_number.zfill(8)

            # UPSERT into local SQLite
            cursor_local.execute('''
            INSERT OR REPLACE INTO cheques (
                cheque_number, date, ssn, payee_name, payee_address, amount, amount_words,
                claim_number, status, payment_mode, bkcode,
                employer_name, employer_street, employer_city_state_zip,
                bank_info, routing_number, micr_account_tail, bank_routing_fraction, void_days,
                signature_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                padded_cheque_number, date_str, ssn, payee_name, payee_address, amount, amount_words,
                claim_number, status, payment_mode, bkcode,
                employer_name, employer_street, city_state_zip,
                bank_info, routing_number, micr_account_tail, bank_routing_fraction, void_days,
                ""
            ))

        conn_local.commit()
        print(f"Synchronization for {selection} complete.")

    except Exception as e:
        print(f"Error during synchronization: {e}")
    finally:
        cursor_db2.close()
        conn_db2.close()
        conn_local.close()

if __name__ == "__main__":
    # For testing, you can call sync('Plasters') or sync('J84')
    import sys
    if len(sys.argv) > 1:
        sync(sys.argv[1])
    else:
        print("Please provide selection: Plasters or J84")