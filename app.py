"""Loopback-only full-stack teaching prototype. Run: python app.py"""
import argparse
import csv
import io
import json
import secrets
import sqlite3
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from ledger.service import DomainError, Ledger
from ledger.provider import load_local_config, ProviderError
from ledger.domain import validate_record
from ledger.localization import LABELS, MESSAGES, public_payload, chinese_csv

ROOT = Path(__file__).resolve().parent

def create_server(db_path, port=8765):
    ledger = Ledger(db_path)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def wants_chinese(self):
            return self.headers.get('Accept-Language','').lower().startswith('zh') or parse_qs(urlsplit(self.path).query).get('lang')==['zh']

        def reply(self, code, body, content_type='application/json; charset=utf-8'):
            if isinstance(body,(dict,list)) and self.wants_chinese():
                body=public_payload(body)
            data = json.dumps(body, ensure_ascii=False).encode('utf-8') if isinstance(body, (dict,list)) else body
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.host_ok():
                return self.reply(403, {'error':'Unknown host.'})
            path = urlsplit(self.path).path
            if path == '/api/config':
                return self.reply(200, {'token':token,'labels':{**LABELS,**MESSAGES}})
            if path == '/api/state':
                return self.reply(200, ledger.state())
            if path == '/api/export':
                if self.wants_chinese():
                    return self.reply(200,chinese_csv(ledger.transactions()),'text/csv; charset=utf-8')
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['date','description','amount','kind','category','counterparty','note','source_kind','source_category'])
                for r in ledger.transactions():
                    # Prefix spreadsheet formula syntax on export, leaving stored text intact.
                    def safe(text):
                        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
                    writer.writerow([r['date'],safe(r['description']),f"{r['amount_fen']/100:.2f}",r['kind'],r['category'],
                        safe(r['counterparty']),safe(r['note']),safe(r['source_kind']),safe(r['source_category'])])
                return self.reply(200, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8')
            if path == '/sample.csv':
                records=[validate_record(raw) for raw in csv.DictReader(io.StringIO((ROOT/'samples/transactions.csv').read_text(encoding='utf-8')))]
                return self.reply(200,chinese_csv(records,translate_examples=True),'text/csv; charset=utf-8')
            files = {'/':('static/index.html','text/html; charset=utf-8'), '/app.js':('static/app.js','text/javascript; charset=utf-8'),
                     '/styles.css':('static/styles.css','text/css; charset=utf-8'), '/workflows.js':('static/workflows.js','text/javascript; charset=utf-8'),
                     '/adventure.js':('static/adventure.js','text/javascript; charset=utf-8'), '/adventure.css':('static/adventure.css','text/css; charset=utf-8')}
            if path in files:
                file, content_type = files[path]
                return self.reply(200, (ROOT/file).read_bytes(), content_type)
            extra={'/reports.js':('static/reports.js','text/javascript; charset=utf-8'),
                   '/goals.js':('static/goals.js','text/javascript; charset=utf-8'),
                   '/memories.js':('static/memories.js','text/javascript; charset=utf-8'),
                   '/workspace.css':('static/workspace.css','text/css; charset=utf-8'),
                   '/imports.js':('static/imports.js','text/javascript; charset=utf-8'),
                   '/pages.js':('static/pages.js','text/javascript; charset=utf-8'),
                   '/comfort.css':('static/comfort.css','text/css; charset=utf-8'),
                   '/setup-chat.js':('static/setup-chat.js','text/javascript; charset=utf-8'),
                   '/trials.js':('static/trials.js','text/javascript; charset=utf-8'),
                   '/minimal.css':('static/minimal.css','text/css; charset=utf-8'),
                   '/quick-entry.js':('static/quick-entry.js','text/javascript; charset=utf-8'),
                   '/images/comic-flat.png':('static/images/comic-flat.png','image/png')}
            if path in extra:
                file,content_type=extra[path]
                return self.reply(200,(ROOT/file).read_bytes(),content_type)
            return self.reply(404, {'error':'Route not found.'})

        def mutate(self):
            if not self.host_ok():
                return self.reply(403, {'error':'Unknown host.'})
            origin = self.headers.get('Origin')
            allowed = (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')
            if (origin and origin not in allowed) or not secrets.compare_digest(self.headers.get('X-Ledger-Token',''),token):
                return self.reply(403, {'error':'Same-origin session token required. Refresh this page.'})
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.reply(415, {'error':'Use application/json.'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                max_length=7000000 if urlsplit(self.path).path in ('/api/import-file/preview','/api/import-file/confirm') else 2200000
                if not 0 < length <= max_length:
                    return self.reply(413, {'error':'Request must be 1 byte to 2.2 MB.'})
                raw = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(raw, dict):
                    raise DomainError('JSON body must be an object.')
                path = urlsplit(self.path).path
                if self.command == 'PATCH' and path.startswith('/api/transactions/'):
                    result = ledger.edit(int(path.rsplit('/',1)[1]), raw)
                elif self.command == 'PATCH' and path.startswith('/api/memories/'):
                    result = ledger.memory.update(int(path.rsplit('/',1)[1]),raw)
                elif self.command != 'POST':
                    return self.reply(404, {'error':'Route not found.'})
                elif path == '/api/import':
                    result = ledger.import_csv(raw.get('csv'))
                elif path == '/api/import-file/preview':
                    result = ledger.wechat_import.preview(raw)
                elif path == '/api/import-file/confirm':
                    result = ledger.wechat_import.commit(raw)
                elif path == '/api/demo':
                    result = ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'))
                elif path == '/api/memory-demo':
                    phase=raw.get('phase')
                    if phase not in ('seed','followup'):
                        raise DomainError('Choose seed or followup synthetic sample.')
                    result=ledger.import_csv((ROOT/f'samples/memory_{phase}.csv').read_text(encoding='utf-8'))
                elif path == '/api/confirm-purpose':
                    result=ledger.memory.confirm(raw.get('id'),{k:v for k,v in raw.items() if k!='id'})
                elif path == '/api/delete-memory':
                    result=ledger.memory.delete(raw.get('id'))
                elif path == '/api/plans/generate':
                    result=ledger.tools.generate_savings_plans(raw)
                elif path == '/api/plans/save':
                    result=ledger.tools.save_plan(raw)
                elif path == '/api/monthly-review':
                    result=ledger.tools.monthly_review(raw)
                elif path == '/api/reports/generate':
                    result=ledger.reports.generate(raw)
                elif path == '/api/entries/draft':
                    result=ledger.quick_entry.draft(raw)
                elif path == '/api/entries/save':
                    result=ledger.quick_entry.save(raw)
                elif path == '/api/setup/chat':
                    result=ledger.setup_chat.chat(raw)
                elif path == '/api/setup/confirm':
                    result=ledger.setup_chat.commit(raw)
                elif path == '/api/adventure/trial/start':
                    result=ledger.trials.start(raw)
                elif path == '/api/adventure/trial/answer':
                    result=ledger.trials.answer(raw)
                elif path == '/api/adventure/goals':
                    result=ledger.adventure.create_goal(raw)
                elif path == '/api/adventure/entries':
                    result=ledger.adventure.add_entry(raw)
                elif path == '/api/adventure/archive':
                    result=ledger.adventure.archive_goal(raw)
                elif path == '/api/adventure/reflect':
                    result=ledger.adventure.reflect(raw)
                elif path == '/api/adventure/theme':
                    result=ledger.adventure.set_theme(raw)
                elif path == '/api/plan':
                    result = ledger.plan(raw)
                elif path == '/api/budgets':
                    result = ledger.set_budget(raw.get('category'),raw.get('amount'))
                elif path == '/api/ask':
                    result = ledger.ask(raw.get('question'),raw.get('session_id'),use_model=raw.get('use_model',False),locale='zh' if self.wants_chinese() else 'auto')
                elif path == '/api/suggest':
                    if type(raw.get('id')) is not int:
                        raise DomainError('Record ID must be an integer.')
                    result = ledger.suggest(raw['id'])
                else:
                    return self.reply(404, {'error':'Route not found.'})
                self.reply(200, result)
            except (DomainError, ValueError, UnicodeDecodeError) as exc:
                self.reply(400, {'error':str(exc)})
            except sqlite3.Error:
                self.reply(503, {'error':'Database operation failed. No partial transaction saved. Please retry.'})

        do_POST = mutate
        do_PATCH = mutate

    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.ledger = ledger
    return server

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--db',default=str(ROOT/'data/ledger.sqlite'))
    args = parser.parse_args()
    try:
        load_local_config(ROOT)
    except ProviderError as exc:
        print(str(exc),flush=True)
    server = create_server(args.db,args.port)
    print(f'LedgerLens 已启动：http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
