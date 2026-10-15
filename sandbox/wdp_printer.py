"""
WDP Printer Control – czyszczenie dysz
Payload i format MIME odtworzony 1:1 z pcap oryginalnej komunikacji WSDAPI.
"""

import argparse, sys, time, uuid, socket
import xml.etree.ElementTree as ET

DEFAULT_HOST  = "192.168.50.20"
DEFAULT_PORT  = 80
WDP_PATH      = "/WDP/PRINT"
POLL_INTERVAL = 5
POLL_TIMEOUT  = 120

# Exact 66-byte EJL payload z pcap
EJL_CLEAN = (
    b'\x00\x00\x00\x1b\x01'
    b'@EJL 1284.4\n'
    b'@EJL     \n'
    b'\x1b@\x1b@'
    b'\x1b(R\x08\x00\x00'
    b'REMOTE1'
    b'TI\x08\x00\x00\x07\xea\x04\x19\x10\x02\x1f'
    b'CH\x02\x00\x00\x00'
    b'\x1b\x00\x00\x00'
)

def http_post_chunked(host, port, path, headers, body):
    """Raw socket POST z Transfer-Encoding: chunked (wymagane przez drukarkę)."""
    chunk = f'{len(body):x}\r\n'.encode() + body + b'\r\n' + b'0\r\n\r\n'
    req  = f'POST {path} HTTP/1.1\r\n'
    req += f'Host: {host}\r\n'
    for k, v in headers.items():
        req += f'{k}: {v}\r\n'
    req += 'Transfer-Encoding: chunked\r\n\r\n'
    with socket.create_connection((host, port), timeout=30) as s:
        s.sendall(req.encode() + chunk)
        resp = b''
        s.settimeout(10)
        try:
            while True:
                d = s.recv(4096)
                if not d: break
                resp += d
        except socket.timeout:
            pass
    return resp.decode('utf-8', errors='replace')

def http_post_soap(host, port, body_str):
    """Prosty SOAP POST z Content-Length."""
    b = body_str.encode('utf-8')
    req  = f'POST {WDP_PATH} HTTP/1.1\r\n'
    req += f'Host: {host}\r\n'
    req += 'Cache-Control: no-cache\r\nConnection: Keep-Alive\r\nPragma: no-cache\r\n'
    req += 'Content-Type: application/soap+xml\r\nUser-Agent: WSDAPI\r\n'
    req += f'Content-Length: {len(b)}\r\n\r\n'
    with socket.create_connection((host, port), timeout=10) as s:
        s.sendall(req.encode() + b)
        resp = b''
        s.settimeout(5)
        try:
            while True:
                d = s.recv(4096)
                if not d: break
                resp += d
        except socket.timeout:
            pass
    return resp.decode('utf-8', errors='replace')

def mid(): return f'urn:uuid:{uuid.uuid4()}'
def url(host, port): return f'http://{host}:{port}{WDP_PATH}'

def parse_soap(text, tag):
    try:
        # Pomiń nagłówki HTTP — XML jest po \r\n\r\n
        hdr_end = text.find('\r\n\r\n')
        xml_text = text[hdr_end + 4:] if hdr_end != -1 else text
        # Odpowiedź drukarki jest chunked — pomiń rozmiar pierwszego chunku
        xml_text = xml_text.strip()
        if xml_text and not xml_text.startswith('<'):
            xml_text = xml_text[xml_text.find('\r\n') + 2:].strip()
        root = ET.fromstring(xml_text)
        for e in root.iter():
            if e.tag.split('}')[-1] == tag:
                return (e.text or '').strip()
    except:
        pass
    return None

def get_status(host, port):
    u = url(host, port)
    body = (f'<?xml version="1.0" encoding="utf-8"?>'
        f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
        f' xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
        f' xmlns:pri="http://schemas.microsoft.com/windows/2006/08/wdp/print">'
        f'<soap:Header><wsa:To>{u}</wsa:To>'
        f'<wsa:Action>http://schemas.microsoft.com/windows/2006/08/wdp/print/GetPrinterElements</wsa:Action>'
        f'<wsa:MessageID>{mid()}</wsa:MessageID>'
        f'<wsa:ReplyTo><wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>'
        f'<wsa:From><wsa:Address>{mid()}</wsa:Address></wsa:From>'
        f'</soap:Header><soap:Body>'
        f'<pri:GetPrinterElementsRequest><pri:RequestedElements>'
        f'<pri:Name>pri:PrinterStatus</pri:Name>'
        f'</pri:RequestedElements></pri:GetPrinterElementsRequest>'
        f'</soap:Body></soap:Envelope>')
    r = http_post_soap(host, port, body)
    return {'state': parse_soap(r,'PrinterState') or 'Unknown',
            'queue': parse_soap(r,'QueuedJobCount') or '0',
            'time':  parse_soap(r,'PrinterCurrentTime') or ''}

def create_job(host, port, name, user='ha-script'):
    u = url(host, port)
    body = (f'<?xml version="1.0" encoding="utf-8"?>'
        f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
        f' xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
        f' xmlns:pri="http://schemas.microsoft.com/windows/2006/08/wdp/print">'
        f'<soap:Header><wsa:To>{u}</wsa:To>'
        f'<wsa:Action>http://schemas.microsoft.com/windows/2006/08/wdp/print/CreatePrintJob</wsa:Action>'
        f'<wsa:MessageID>{mid()}</wsa:MessageID>'
        f'<wsa:ReplyTo><wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>'
        f'<wsa:From><wsa:Address>{mid()}</wsa:Address></wsa:From>'
        f'</soap:Header><soap:Body>'
        f'<pri:CreatePrintJobRequest><pri:PrintTicket><pri:JobDescription>'
        f'<pri:JobName>{name}</pri:JobName>'
        f'<pri:JobOriginatingUserName>{user}</pri:JobOriginatingUserName>'
        f'</pri:JobDescription></pri:PrintTicket></pri:CreatePrintJobRequest>'
        f'</soap:Body></soap:Envelope>')
    r = http_post_soap(host, port, body)
    job_id = parse_soap(r, 'JobId')
    if not job_id: raise RuntimeError(f'Brak JobId:\n{r[:300]}')
    return int(job_id)

def send_doc(host, port, job_id, payload):
    u = url(host, port)
    boundary = f'{uuid.uuid4()}-{uuid.uuid4()}'
    crlf = b'\r\n'

    soap = (f'<?xml version="1.0" encoding="utf-8"?>'
        f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
        f' xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
        f' xmlns:pri="http://schemas.microsoft.com/windows/2006/08/wdp/print"'
        f' xmlns:xop="http://www.w3.org/2004/08/xop/include">'
        f'<soap:Header><wsa:To>{u}</wsa:To>'
        f'<wsa:Action>http://schemas.microsoft.com/windows/2006/08/wdp/print/SendDocument</wsa:Action>'
        f'<wsa:MessageID>{mid()}</wsa:MessageID>'
        f'<wsa:ReplyTo><wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>'
        f'<wsa:From><wsa:Address>{mid()}</wsa:Address></wsa:From>'
        f'</soap:Header><soap:Body>'
        f'<pri:SendDocumentRequest>'
        f'<pri:JobId>{job_id}</pri:JobId>'
        f'<pri:DocumentDescription>'
        f'<pri:DocumentId>1</pri:DocumentId>'
        f'<pri:Compression>None</pri:Compression>'
        f'<pri:Format>unknown</pri:Format>'
        f'</pri:DocumentDescription>'
        f'<pri:LastDocument>true</pri:LastDocument>'
        f'<pri:DocumentData><xop:Include href="cid:0@body"></xop:Include></pri:DocumentData>'
        f'</pri:SendDocumentRequest>'
        f'</soap:Body></soap:Envelope>').encode('utf-8')

    # MIME body — struktura identyczna jak w pcap
    body  = b'--' + boundary.encode() + crlf
    body += b'Content-Type: application/xop+xml;charset=UTF-8;type="application/soap+xml"' + crlf
    body += b'Content-Transfer-Encoding: binary' + crlf
    body += b'Content-ID: <soap@soap>' + crlf
    body += crlf
    body += soap + crlf
    body += b'--' + boundary.encode() + crlf
    body += b'Content-Type: application/octet-stream' + crlf
    body += b'Content-Transfer-Encoding: binary' + crlf
    body += b'Content-ID:<0@body>' + crlf          # bez spacji po : jak w oryginale
    body += crlf
    body += payload + crlf
    body += b'--' + boundary.encode() + b'--' + crlf

    headers = {
        'Cache-Control':       'no-cache',
        'Connection':          'Keep-Alive',
        'Pragma':              'no-cache',
        'Content-Type':        (f'Multipart/Related;boundary={boundary}'
                                f';type="application/xop+xml"'
                                f';start="<soap@soap>"'
                                f';start-info="application/soap+xml"'),
        'User-Agent':          'WSDAPI',
        'MIME-Version':        '1.0',
        'Content-Description': 'WSDAPI MIME multipart',
    }
    return http_post_chunked(host, port, WDP_PATH, headers, body)

def wait_idle(host, port, label=''):
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            st = get_status(host, port)
            print(f'  [{label}] {st["state"]}, kolejka: {st["queue"]}')
            if st['state'] == 'Idle': return True
        except Exception as e:
            print(f'  [{label}] Błąd: {e}')
        time.sleep(POLL_INTERVAL)
    print(f'  TIMEOUT po {POLL_TIMEOUT}s')
    return False

def run_clean(host, port):
    print(f'\n=== Czyszczenie dysz → {host}:{port} ===')
    print('1. Sprawdzam status (wybudzam jeśli sleep)...')
    st = get_status_with_wakeup(host, port)
    print(f'   Stan: {st["state"]}, kolejka: {st["queue"]}')
    if st['state'] != 'Idle':
        print('   BŁĄD: drukarka nie jest Idle'); return False

    print('2. CreatePrintJob...')
    job_id = create_job(host, port, 'HeadCleaning')
    print(f'   JobId: {job_id}')

    print('3. SendDocument (EJL)...')
    resp = send_doc(host, port, job_id, EJL_CLEAN)
    if 'SendDocumentResponse' in resp:
        print('   OK')
    else:
        print(f'   Odpowiedź: {resp[:300]}')

    print('4. Czekam na Idle...')
    ok = wait_idle(host, port, 'clean')
    if ok: print('   Gotowe — czyszczenie zakończone.')
    return ok

def get_status_with_wakeup(host, port, retries=8, delay=3):
    """Ponawia GetPrinterElements — samo połączenie TCP budzi drukarkę ze sleep."""
    for i in range(retries):
        try:
            st = get_status(host, port)
            if st['state'] in ('Idle', 'Processing'):
                return st
            print(f'  Wybudzam drukarkę... ({i+1}/{retries})')
        except Exception as e:
            print(f'  Próba {i+1}: {e}')
        time.sleep(delay)
    raise RuntimeError('Drukarka nie odpowiedziała po wybudzeniu')

def run_status(host, port):
    print(f'\n=== Status drukarki {host}:{port} ===')
    st = get_status_with_wakeup(host, port)
    print(f'  Stan:    {st["state"]}')
    print(f'  Kolejka: {st["queue"]}')
    print(f'  Czas drukarki: {st["time"]}')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host',   default=DEFAULT_HOST)
    p.add_argument('--port',   type=int, default=DEFAULT_PORT)
    p.add_argument('--action', choices=['clean','status'], required=True)
    a = p.parse_args()
    try:
        if a.action == 'status': run_status(a.host, a.port)
        elif a.action == 'clean':
            ok = run_clean(a.host, a.port)
            sys.exit(0 if ok else 1)
    except ConnectionRefusedError:
        print(f'BŁĄD: brak połączenia z {a.host}:{a.port}'); sys.exit(2)
    except Exception as e:
        print(f'BŁĄD: {e}'); raise

if __name__ == '__main__':
    main()