from flask import Flask, render_template, request, redirect
import sqlite3
import webbrowser
import threading
import os
import shutil
from datetime import datetime
from dotenv import load_dotenv  # ← NOVA DEPENDÊNCIA

# Carrega variáveis de ambiente do .env se existir
load_dotenv()

# Configurações de banco de dados
USE_SUPABASE = os.getenv('USE_SUPABASE', 'false').lower() == 'true'
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Verifica se as credenciais do Supabase estão definidas quando necessário
if USE_SUPABASE and (not SUPABASE_URL or not SUPABASE_KEY):
    raise EnvironmentError("SUPABASE_URL e SUPABASE_KEY são obrigatórios quando USE_SUPABASE=true")

def fazer_backup():
    if os.path.exists('dados_empresa.db'):
        if not os.path.exists('backups'):
            os.makedirs('backups')
        agora = datetime.now().strftime('%Y-%m-%d_%H-%M')
        destino = f'backups/backup_{agora}.db'
        shutil.copy('dados_empresa.db', destino)
        print(f'Backup criado: {destino}')

def conectar():
    if USE_SUPABASE:
        import psycopg2
        import urllib.parse
        conn = psycopg2.connect(
            host=urllib.parse.urlparse(SUPABASE_URL).hostname,
            port=5432,
            database=urllib.parse.urlparse(SUPABASE_URL).path[1:],
            user='postgres',
            password=SUPABASE_KEY,
            sslmode='require'
        )
        return conn
    else:
        return sqlite3.connect('dados_empresa.db')

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()

    if USE_SUPABASE:
        # Tabelas para PostgreSQL (Supabase)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf_cnpj TEXT NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordens_servico (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                data_servico TEXT,
                hora_servico TEXT,
                local_servico TEXT,
                comprimento REAL,
                altura REAL,
                materiais TEXT,
                status TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_ordem (
                id SERIAL PRIMARY KEY,
                ordem_id INTEGER REFERENCES ordens_servico(id),
                tipo TEXT,
                altura REAL,
                comprimento REAL,
                material TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estoque (
                id SERIAL PRIMARY KEY,
                nome_produto TEXT NOT NULL,
                tipo TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                status TEXT NOT NULL,
                cliente_id INTEGER REFERENCES clientes(id),
                data_entrada TEXT,
                data_saida TEXT,
                observacoes TEXT
            )
        """)
    else:
        # Tabelas para SQLite (local)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf_cnpj TEXT NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordens_servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                data_servico TEXT,
                hora_servico TEXT,
                local_servico TEXT,
                comprimento REAL,
                altura REAL,
                materiais TEXT,
                status TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_ordem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ordem_id INTEGER,
                tipo TEXT,
                altura REAL,
                comprimento REAL,
                material TEXT,
                FOREIGN KEY (ordem_id) REFERENCES ordens_servico(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_produto TEXT NOT NULL,
                tipo TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                status TEXT NOT NULL,
                cliente_id INTEGER,
                data_entrada TEXT,
                data_saida TEXT,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Banco de dados verificado/criado.")

def salvar_item_ordem(ordem_id, tipo, altura, comprimento, material):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
        VALUES (?, ?, ?, ?, ?)
    """, (ordem_id, tipo, altura, comprimento, material))
    conn.commit()
    cursor.close()
    conn.close()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro_cliente', methods=['GET', 'POST'])
def cadastro_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        cpf_cnpj = request.form['cpf_cnpj']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        conn = conectar()
        cursor = conn.cursor()
        if USE_SUPABASE:
            cursor.execute("""
                INSERT INTO clientes (nome, cpf_cnpj, endereco, telefone, email)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (nome, cpf_cnpj, endereco, telefone, email))
            cliente_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO clientes (nome, cpf_cnpj, endereco, telefone, email)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, cpf_cnpj, endereco, telefone, email))
            cliente_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/clientes')
    return render_template('cadastro_cliente.html')

@app.route('/clientes', methods=['GET', 'POST'])
def listar_clientes():
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        filtro = request.form['filtro']
        if USE_SUPABASE:
            cursor.execute("""
                SELECT * FROM clientes
                WHERE nome ILIKE %s OR cpf_cnpj ILIKE %s OR email ILIKE %s
            """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
        else:
            cursor.execute("""
                SELECT * FROM clientes
                WHERE nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ?
            """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
    else:
        cursor.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('listar_clientes.html', clientes=clientes)

@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        cpf_cnpj = request.form['cpf_cnpj']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']
        if USE_SUPABASE:
            cursor.execute("""
                UPDATE clientes
                SET nome=%s, cpf_cnpj=%s, endereco=%s, telefone=%s, email=%s
                WHERE id=%s
            """, (nome, cpf_cnpj, endereco, telefone, email, id))
        else:
            cursor.execute("""
                UPDATE clientes
                SET nome=?, cpf_cnpj=?, endereco=?, telefone=?, email=?
                WHERE id=?
            """, (nome, cpf_cnpj, endereco, telefone, email, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/clientes')
    if USE_SUPABASE:
        cursor.execute("SELECT * FROM clientes WHERE id = %s", (id,))
    else:
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (id,))
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
    else:
        cursor.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/clientes')

@app.route('/cadastro_os', methods=['GET', 'POST'])
def cadastro_os():
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
    else:
        cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    if request.method == 'POST':
        cliente_id = request.form['cliente']
        local_servico = request.form['local']
        data_servico = request.form['data']
        hora_servico = request.form['hora']
        materiais = request.form.get('observacoes')
        status = request.form['status']

        if USE_SUPABASE:
            cursor.execute("""
                INSERT INTO ordens_servico (
                    cliente_id, local_servico, data_servico, hora_servico, materiais, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (cliente_id, local_servico, data_servico, hora_servico, materiais, status))
            ordem_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO ordens_servico (
                    cliente_id, local_servico, data_servico, hora_servico, materiais, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (cliente_id, local_servico, data_servico, hora_servico, materiais, status))
            ordem_id = cursor.lastrowid

        tipos = request.form.getlist('tipo[]')
        alturas = request.form.getlist('altura[]')
        comprimentos = request.form.getlist('comprimento[]')
        materiais_item = request.form.getlist('material[]')

        for i in range(len(tipos)):
            salvar_item_ordem(ordem_id, tipos[i], alturas[i], comprimentos[i], materiais_item[i])

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/ordens_servico')
    return render_template('cadastro_os.html', clientes=clientes)

@app.route('/ordens_servico', methods=['GET', 'POST'])
def listar_ordens():
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        filtro = request.form['filtro']
        if USE_SUPABASE:
            cursor.execute("""
                SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                       os.comprimento, os.altura, os.materiais, os.status
                FROM ordens_servico os
                JOIN clientes c ON os.cliente_id = c.id
                WHERE c.nome ILIKE %s OR os.status ILIKE %s
                ORDER BY os.data_servico DESC
            """, (f'%{filtro}%', f'%{filtro}%'))
        else:
            cursor.execute("""
                SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                       os.comprimento, os.altura, os.materiais, os.status
                FROM ordens_servico os
                JOIN clientes c ON os.cliente_id = c.id
                WHERE c.nome LIKE ? OR os.status LIKE ?
                ORDER BY os.data_servico DESC
            """, (f'%{filtro}%', f'%{filtro}%'))
    else:
        if USE_SUPABASE:
            cursor.execute("""
                SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                       os.comprimento, os.altura, os.materiais, os.status
                FROM ordens_servico os
                JOIN clientes c ON os.cliente_id = c.id
                ORDER BY os.data_servico DESC
            """)
        else:
            cursor.execute("""
                SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                       os.comprimento, os.altura, os.materiais, os.status
                FROM ordens_servico os
                JOIN clientes c ON os.cliente_id = c.id
                ORDER BY os.data_servico DESC
            """)
    ordens = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('listar_ordens.html', ordens=ordens)

@app.route('/editar_os/<int:id>', methods=['GET', 'POST'])
def editar_os(id):
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        data_servico = request.form['data_servico']
        hora_servico = request.form['hora_servico']
        local_servico = request.form['local_servico']
        materiais = request.form['materiais']
        status = request.form['status']

        if USE_SUPABASE:
            cursor.execute("""
                UPDATE ordens_servico
                SET cliente_id=%s, data_servico=%s, hora_servico=%s, local_servico=%s, materiais=%s, status=%s
                WHERE id=%s
            """, (cliente_id, data_servico, hora_servico, local_servico, materiais, status, id))
        else:
            cursor.execute("""
                UPDATE ordens_servico
                SET cliente_id=?, data_servico=?, hora_servico=?, local_servico=?, materiais=?, status=?
                WHERE id=?
            """, (cliente_id, data_servico, hora_servico, local_servico, materiais, status, id))

        item_ids = request.form.getlist('item_id[]')
        tipos = request.form.getlist('tipo[]')
        alturas = request.form.getlist('altura[]')
        comprimentos = request.form.getlist('comprimento[]')
        materiais_item = request.form.getlist('material[]')

        if USE_SUPABASE:
            cursor.execute("SELECT id FROM itens_ordem WHERE ordem_id = %s", (id,))
        else:
            cursor.execute("SELECT id FROM itens_ordem WHERE ordem_id = ?", (id,))
        itens_existentes = set(row[0] for row in cursor.fetchall())
        item_ids_form = set(int(i) for i in item_ids if i)
        itens_removidos = itens_existentes - item_ids_form

        for item_id in itens_removidos:
            if USE_SUPABASE:
                cursor.execute("DELETE FROM itens_ordem WHERE id = %s", (item_id,))
            else:
                cursor.execute("DELETE FROM itens_ordem WHERE id = ?", (item_id,))

        for item_id, tipo, altura, comprimento, material in zip(item_ids, tipos, alturas, comprimentos, materiais_item):
            if item_id and int(item_id) in itens_existentes:
                if USE_SUPABASE:
                    cursor.execute("""
                        UPDATE itens_ordem
                        SET tipo=%s, altura=%s, comprimento=%s, material=%s
                        WHERE id=%s
                    """, (tipo, altura, comprimento, material, item_id))
                else:
                    cursor.execute("""
                        UPDATE itens_ordem
                        SET tipo=?, altura=?, comprimento=?, material=?
                        WHERE id=?
                    """, (tipo, altura, comprimento, material, item_id))
            else:
                if USE_SUPABASE:
                    cursor.execute("""
                        INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, tipo, altura, comprimento, material))
                else:
                    cursor.execute("""
                        INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
                        VALUES (?, ?, ?, ?, ?)
                    """, (id, tipo, altura, comprimento, material))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/ordens_servico')

    if USE_SUPABASE:
        cursor.execute("SELECT * FROM ordens_servico WHERE id = %s", (id,))
        cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
        cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = %s ORDER BY id", (id,))
    else:
        cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
        cursor.execute("SELECT id, nome FROM clientes")
        cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = ? ORDER BY id", (id,))
    ordem = cursor.fetchone()
    clientes = cursor.fetchall()
    itens = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('editar_os.html', ordem=ordem, clientes=clientes, itens=itens)

@app.route('/excluir_os/<int:id>')
def excluir_os(id):
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("DELETE FROM ordens_servico WHERE id = %s", (id,))
    else:
        cursor.execute("DELETE FROM ordens_servico WHERE id = ?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/ordens_servico')

@app.route('/ficha_os/<int:id>')
def ficha_os(id):
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("SELECT * FROM ordens_servico WHERE id = %s", (id,))
        cursor.execute("SELECT nome FROM clientes WHERE id = %s", (id,))
        cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = %s ORDER BY id", (id,))
    else:
        cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
        cursor.execute("SELECT nome FROM clientes WHERE id = ?", (id,))
        cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = ? ORDER BY id", (id,))
    ordem = cursor.fetchone()
    cliente = cursor.fetchone()[0]
    itens = cursor.fetchall()

    estimativas = []
    recomendacoes = []
    for item in itens:
        tipo = item[2]
        altura = float(item[3])
        comprimento = float(item[4])
        area = altura * comprimento

        if tipo in ['Cortina', 'Persiana'] and max(altura, comprimento) > 4:
            recomendacoes.append(f"{tipo} com {max(altura, comprimento):.2f}m: recomenda-se uso de escada ou andaime.")
        if tipo == 'Cortina':
            suportes = max(2, round(comprimento / 1.5))
            estimativas.append(f"{area:.2f} m² de tecido | {suportes} suportes")
        elif tipo == 'Persiana':
            estimativas.append(f"{area:.2f} m² de tecido")
        else:
            estimativas.append("—")

    cursor.close()
    conn.close()
    return render_template('ficha_os.html', ordem=ordem, cliente=cliente, itens=itens, estimativas=estimativas, recomendacoes=recomendacoes)

@app.route('/cadastro_estoque', methods=['GET', 'POST'])
def cadastro_estoque():
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
    else:
        cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    if request.method == 'POST':
        nome_produto = request.form['nome_produto']
        tipo = request.form['tipo']
        quantidade = request.form['quantidade']
        status = request.form['status']
        cliente_id = request.form.get('cliente_id') or None
        data_entrada = request.form['data_entrada']
        observacoes = request.form['observacoes']
        if USE_SUPABASE:
            cursor.execute("""
                INSERT INTO estoque (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes))
        else:
            cursor.execute("""
                INSERT INTO estoque (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/estoque')
    return render_template('cadastro_estoque.html', clientes=clientes)

@app.route('/estoque', methods=['GET', 'POST'])
def listar_estoque():
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        filtro = request.form['filtro']
        if USE_SUPABASE:
            cursor.execute("""
                SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                       c.nome, e.data_entrada, e.data_saida, e.observacoes
                FROM estoque e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                WHERE e.nome_produto ILIKE %s OR e.tipo ILIKE %s OR e.status ILIKE %s OR c.nome ILIKE %s
                ORDER BY e.data_entrada DESC
            """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
        else:
            cursor.execute("""
                SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                       c.nome, e.data_entrada, e.data_saida, e.observacoes
                FROM estoque e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                WHERE e.nome_produto LIKE ? OR e.tipo LIKE ? OR e.status LIKE ? OR c.nome LIKE ?
                ORDER BY e.data_entrada DESC
            """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
    else:
        if USE_SUPABASE:
            cursor.execute("""
                SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                       c.nome, e.data_entrada, e.data_saida, e.observacoes
                FROM estoque e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                ORDER BY e.data_entrada DESC
            """)
        else:
            cursor.execute("""
                SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                       c.nome, e.data_entrada, e.data_saida, e.observacoes
                FROM estoque e
                LEFT JOIN clientes c ON e.cliente_id = c.id
                ORDER BY e.data_entrada DESC
            """)
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('listar_estoque.html', produtos=produtos)

@app.route('/editar_estoque/<int:id>', methods=['GET', 'POST'])
def editar_estoque(id):
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        nome_produto = request.form['nome_produto']
        tipo = request.form['tipo']
        quantidade = request.form['quantidade']
        status = request.form['status']
        cliente_id = request.form.get('cliente_id') or None
        data_entrada = request.form['data_entrada']
        data_saida = request.form['data_saida']
        observacoes = request.form['observacoes']
        if USE_SUPABASE:
            cursor.execute("""
                UPDATE estoque
                SET nome_produto=%s, tipo=%s, quantidade=%s, status=%s, cliente_id=%s, data_entrada=%s, data_saida=%s, observacoes=%s
                WHERE id=%s
            """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, data_saida, observacoes, id))
        else:
            cursor.execute("""
                UPDATE estoque
                SET nome_produto=?, tipo=?, quantidade=?, status=?, cliente_id=?, data_entrada=?, data_saida=?, observacoes=?
                WHERE id=?
            """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, data_saida, observacoes, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/estoque')
    if USE_SUPABASE:
        cursor.execute("SELECT * FROM estoque WHERE id = %s", (id,))
        cursor.execute("SELECT id, nome FROM clientes ORDER BY nome")
    else:
        cursor.execute("SELECT * FROM estoque WHERE id = ?", (id,))
        cursor.execute("SELECT id, nome FROM clientes")
    produto = cursor.fetchone()
    clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('editar_estoque.html', produto=produto, clientes=clientes)

@app.route('/excluir_estoque/<int:id>')
def excluir_estoque(id):
    conn = conectar()
    cursor = conn.cursor()
    if USE_SUPABASE:
        cursor.execute("DELETE FROM estoque WHERE id = %s", (id,))
    else:
        cursor.execute("DELETE FROM estoque WHERE id = ?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/estoque')

def abrir_navegador():
    webbrowser.open_new("http://localhost:5000")

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    fazer_backup()
    inicializar_banco()
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.5, abrir_navegador).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
